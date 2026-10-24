"""Workbook behaviour, not Excel's own validation enforcement."""
from io import BytesIO
from datetime import datetime
from zipfile import ZipFile, ZIP_DEFLATED
import pytest
from openpyxl import load_workbook

from data_imports.formats import parse_file, render_template, ImportFormatError


def descriptor():
    return dict(tenantId='tenant-a', strategyId='strategy-a', columns=[
        dict(key='sourceTradeId', label='Source trade ID', required=True),
        dict(key='quantity', label='Quantity', required=True),
        dict(key='side', label='Side', required=True, choices=['BUY', 'SELL']),
        dict(key='property:stable-id', label='Team', choices=['OPS', 'TRADING']),
    ])


def workbook_bytes(edit):
    book = load_workbook(BytesIO(render_template(descriptor())))
    edit(book)
    out = BytesIO(); book.save(out)
    return out.getvalue()


def test_template_has_native_dropdowns_and_text_financial_columns():
    book = load_workbook(BytesIO(render_template(descriptor())))
    assert set(book.sheetnames) == {'Instructions', 'Trades', 'Reference lists', 'Template'}
    assert len(book['Trades'].data_validations.dataValidation) == 2
    assert book['Trades']['B2'].number_format == '@'
    assert book['Trades']['D1'].value == 'property:stable-id'
    meta=dict(book['Template'].iter_rows(values_only=True))
    assert datetime.fromisoformat(meta['generatedAt']).utcoffset() is not None


def test_exact_values_and_ids_survive_csv_and_excel():
    values=['00001', '123456789012345678.123456789012', 'BUY', 'OPS']
    data=workbook_bytes(lambda book: book['Trades'].append(values))
    excel=parse_file(data, 'trades.xlsx', descriptor())
    csv=parse_file(('sourceTradeId,quantity,side,property:stable-id\n'+','.join(values)+'\n').encode(), 'trades.csv', descriptor())
    expected=dict(zip([c['key'] for c in descriptor()['columns']], values))
    assert excel == [dict(row=3, values=expected)]  # append follows the styled blank row
    assert csv == [dict(row=2, values=expected)]


def test_edited_lookup_sheet_does_not_change_parsed_trade_value():
    def edit(book):
        book['Reference lists']['A2']='INVENTED'
        book['Trades'].append(['id', '1', 'INVENTED', 'OPS'])
    assert parse_file(workbook_bytes(edit), 'trades.xlsx', descriptor())[0]['values']['side']=='INVENTED'


@pytest.mark.parametrize('value', ['=1+2', '=HYPERLINK("https://example.com")'])
def test_formula_input_rejected(value):
    with pytest.raises(ImportFormatError, match='formula'):
        parse_file(workbook_bytes(lambda b:b['Trades'].append(['id', value, 'BUY', ''])), 'x.xlsx', descriptor())


def test_numeric_financial_cell_requires_text_instead_of_guessing_lost_precision():
    with pytest.raises(ImportFormatError, match='text'):
        parse_file(workbook_bytes(lambda b:b['Trades'].append(['id', 123.45, 'BUY', ''])), 'x.xlsx', descriptor())


def test_wrong_scope_template_rejected():
    data=render_template(descriptor())
    with pytest.raises(ImportFormatError, match='context'):
        parse_file(data, 'x.xlsx', descriptor() | {'tenantId':'tenant-b'})


def test_duplicate_unknown_header_and_hidden_populated_rows():
    with pytest.raises(ImportFormatError, match='header'):
        parse_file(b'sourceTradeId,sourceTradeId\na,b', 'x.csv', descriptor())
    def edit(book):
        book['Trades'].append(['id','1','BUY',''])
        book['Trades'].row_dimensions[2].hidden=True
    assert len(parse_file(workbook_bytes(edit), 'x.xlsx', descriptor()))==1


def test_full_input_limit_rejects_not_truncates():
    with pytest.raises(ImportFormatError, match='500'):
        parse_file(('sourceTradeId,quantity,side\n'+''.join(f'{i},1,BUY\n' for i in range(501))).encode(), 'x.csv', descriptor())


def test_unexpected_sheet_and_unsupported_extension_rejected():
    def edit(book): book.create_sheet('Other')['A1']='secret extra input'
    with pytest.raises(ImportFormatError, match='sheet'):
        parse_file(workbook_bytes(edit), 'x.xlsx', descriptor())
    with pytest.raises(ImportFormatError, match='format'):
        parse_file(b'fake', 'x.xlsm', descriptor())


def test_external_relationship_rejected_independent_of_quote_style():
    original=render_template(descriptor());out=BytesIO()
    with ZipFile(BytesIO(original)) as source,ZipFile(out,'w',ZIP_DEFLATED) as target:
        for member in source.infolist():target.writestr(member.filename,source.read(member))
        target.writestr('xl/worksheets/_rels/sheet1.xml.rels',
            "<Relationships xmlns='http://schemas.openxmlformats.org/package/2006/relationships'><Relationship Id='external' Type='hyperlink' Target='https://example.com' TargetMode='External'/></Relationships>")
    with pytest.raises(ImportFormatError,match='External'):
        parse_file(out.getvalue(),'x.xlsx',descriptor())
