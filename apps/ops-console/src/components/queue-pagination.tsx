import {Button,Stack,Typography} from '@mui/material';
import type {ReferenceApiMeta} from '@/lib/reference-api-client';
export function QueuePagination({meta,path}:{meta:ReferenceApiMeta;path:string}) {
  const offset=meta.offset??0,limit=meta.limit??100,total=meta.total??0;
  if(total<=limit&&offset===0)return null;
  return <Stack direction="row" spacing={2} sx={{my:2,alignItems:'center'}} aria-label="Queue pagination">
    <Button disabled={offset===0} href={`${path}?offset=${Math.max(0,offset-limit)}`}>Previous</Button>
    <Typography variant="body2">Queue records {total===0?0:offset+1}–{Math.min(offset+limit,total)} of {total}</Typography>
    <Button disabled={offset+limit>=total||offset+limit>10000} href={`${path}?offset=${offset+limit}`}>Next</Button>
  </Stack>;
}
export function queueOffset(value?:string):number {
  return value&&/^\d+$/.test(value)&&Number(value)<=10000?Number(value):0;
}
