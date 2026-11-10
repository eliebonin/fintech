"""Bounded, values-only files. Excel dropdowns never establish authority."""
from io import BytesIO, StringIO
import csv
from datetime import datetime,timezone
from zipfile import ZipFile
from defusedxml.ElementTree import fromstring
from openpyxl import Workbook, load_workbook
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.comments import Comment

MAX_BYTES=512*1024  # Fits the existing 1 MiB request budget after base64.
MAX_ROWS=500
MAX_COLUMNS=1200


class ImportFormatError(ValueError):
    pass


def render_template(descriptor):
    book=Workbook();guide=book.active;guide.title='Instructions'
    for row in [
        ['Trade import — equities / ETFs / funds'],
        [f"Tenant: {descriptor.get('tenantLabel',descriptor['tenantId'])} · Strategy: {descriptor.get('strategyLabel',descriptor['strategyId'])}"],
        ['One strategy per file. Review and explicitly confirm before booking.'],
        ['Enter amounts and identifiers as text, not formulas or numeric Excel cells.'],
        ['Listing UUID identifies the execution venue; currency comes from its approved definition.'],
        ['Use ISO text dates and timezone-bearing execution timestamps.'],
        ['Source trade IDs must be permanent and unique within your source namespace.'],
        ['Maximum 500 rows / 512 KiB. All rows must pass; no silent partial booking.'],
        ['Separate multiple tags/references using | as described below.'],
        [], ['Column','Label','Required','Description'],
    ]:guide.append(row)
    trades=book.create_sheet('Trades');refs=book.create_sheet('Reference lists');meta=book.create_sheet('Template')
    for key in ('tenantId','strategyId','profileVersionId','profileAssignmentRevision','configurationHash'):
        if key in descriptor:meta.append([key,str(descriptor[key])])
    meta.append(['schemaVersion','cash-trades-v1'])
    meta.append(['generatedAt',datetime.now(timezone.utc).isoformat()])
    columns=descriptor['columns']
    if len(columns)>MAX_COLUMNS:raise ImportFormatError('Too many configured input columns.')
    trades.append([col['key'] for col in columns]);trades.freeze_panes='A2'
    ref_index=0
    for index,col in enumerate(columns,1):
        letter=get_column_letter(index);trades.column_dimensions[letter].width=30
        trades.cell(1,index).comment=Comment(col['label']+'\n'+col.get('description',''),'Platform')
        trades.column_dimensions[letter].number_format='@';trades.cell(2,index).number_format='@'
        guide.append([col['key'],col['label'],'Yes' if col.get('required') else 'Optional',col.get('description','')])
        if col.get('choices'):
            ref_index+=1;ref_col=get_column_letter(ref_index);refs[f'{ref_col}1']=col['label']
            for n,value in enumerate(col['choices'],2):
                refs[f'{ref_col}{n}']=str(value);refs[f'{ref_col}{n}'].data_type='s'
            name=f'choices_{index}'
            book.defined_names.add(DefinedName(name,attr_text=f"'Reference lists'!${ref_col}$2:${ref_col}${len(col['choices'])+1}"))
            rule=DataValidation(type='list',formula1=f'={name}',allow_blank=not col.get('required'))
            rule.showErrorMessage=True;rule.error='Select a listed value. The server checks eligibility again.'
            trades.add_data_validation(rule);rule.add(f'{letter}2:{letter}{MAX_ROWS+1}')
    table=Table(displayName='TradeRows',ref=f'A1:{get_column_letter(len(columns))}2')
    table.tableStyleInfo=TableStyleInfo(name='TableStyleMedium2',showRowStripes=True);trades.add_table(table)
    meta.sheet_state='hidden';refs.freeze_panes='A2'
    guide.column_dimensions['A'].width=65;guide.column_dimensions['B'].width=40;guide.column_dimensions['D'].width=100
    for sheet in (guide,meta,refs):
        for row in sheet:
            for cell in row:
                if isinstance(cell.value,str):cell.data_type='s'
    out=BytesIO();book.save(out);return out.getvalue()


def _workbook_rows(data,descriptor):
    try:
        with ZipFile(BytesIO(data)) as archive:
            members=archive.infolist()
            if len(members)>1000 or sum(m.file_size for m in members)>50*1024*1024:
                raise ImportFormatError('Workbook decompression limit exceeded.')
            if len({m.filename for m in members})!=len(members):raise ImportFormatError('Duplicate workbook components.')
            for member in members:
                name=member.filename.lower()
                if any(part in name for part in ('vbaproject','externallinks/','connections.xml','querytables/','embeddings/')):
                    raise ImportFormatError('Macros and external dependencies are not accepted.')
                if name.endswith('.rels'):
                    relationships=fromstring(archive.read(member))
                    if any(element.get('TargetMode')=='External' for element in relationships):
                        raise ImportFormatError('External workbook relationships are not accepted.')
        book=load_workbook(BytesIO(data),read_only=True,data_only=False,keep_links=False)
        try:
            if set(book.sheetnames)-{'Instructions','Trades','Reference lists','Template'}:raise ImportFormatError('Unexpected workbook sheet.')
            if 'Template' not in book or 'Trades' not in book:raise ImportFormatError('Use the downloaded template.')
            meta=dict(book['Template'].iter_rows(values_only=True))
            if any(str(meta.get(k))!=str(descriptor[k]) for k in ('tenantId','strategyId')) or meta.get('schemaVersion')!='cash-trades-v1':
                raise ImportFormatError('Template context differs from this tenant or strategy.')
            for key in ('profileVersionId','profileAssignmentRevision','configurationHash'):
                if key in descriptor and str(meta.get(key))!=str(descriptor[key]):
                    raise ImportFormatError('The strategy trade profile changed. Download a new template and review the fields.')
            sheet=book['Trades'];sheet.reset_dimensions();raw=[]
            for n,row in enumerate(sheet.iter_rows(),1):
                if n>MAX_ROWS+2:raise ImportFormatError('Use at most 500 trade rows.')
                if len(row)>MAX_COLUMNS:raise ImportFormatError('Too many input columns.')
                values=[]
                for cell in row:
                    if cell.data_type=='f':raise ImportFormatError(f'{cell.coordinate}: formula input is not accepted.')
                    if cell.value is not None and not isinstance(cell.value,str):
                        raise ImportFormatError(f'{cell.coordinate}: enter values as text, including ISO dates, to preserve exact precision.')
                    values.append(cell.value or '')
                raw.append(values)
            return raw
        finally:book.close()
    except ImportFormatError:raise
    except Exception as exc:raise ImportFormatError('Invalid workbook; download a fresh template.') from exc


def parse_file(data,filename,descriptor):
    if not data or len(data)>MAX_BYTES:raise ImportFormatError('Use a nonempty file of at most 512 KiB.')
    if filename.lower().endswith('.csv'):
        try:raw=list(csv.reader(StringIO(data.decode('utf-8-sig')),strict=True))
        except (UnicodeError,csv.Error) as exc:raise ImportFormatError('Use valid UTF-8 CSV.') from exc
    elif filename.lower().endswith('.xlsx'):raw=_workbook_rows(data,descriptor)
    else:raise ImportFormatError('Supported formats are .xlsx and UTF-8 .csv only.')
    if not raw:raise ImportFormatError('A header and at least one trade are required.')
    headers=[str(h).strip() for h in raw[0]]
    while headers and not headers[-1]:headers.pop()
    allowed={col['key'] for col in descriptor['columns']}
    if not headers or len(headers)!=len(set(headers)) or any(h not in allowed for h in headers):
        raise ImportFormatError('Duplicate, unknown or missing machine header; use the current template.')
    required={col['key'] for col in descriptor['columns'] if col.get('required')}
    if required-set(headers):raise ImportFormatError('Missing required header: '+', '.join(sorted(required-set(headers))))
    rows=[]
    for n,row in enumerate(raw[1:],2):
        if not any(str(v).strip() for v in row):continue
        if len(rows)>=MAX_ROWS:raise ImportFormatError('Use at most 500 trade rows; split explicitly into separate imports.')
        if any(row[len(headers):]):raise ImportFormatError(f'Row {n}: values without a header.')
        rows.append(dict(row=n,values={h:str(row[i]).strip() if i<len(row) else '' for i,h in enumerate(headers)}))
    if not rows:raise ImportFormatError('The file contains no trades.')
    return rows
