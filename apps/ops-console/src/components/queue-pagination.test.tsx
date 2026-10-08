import {describe,expect,it} from 'vitest';
import {renderToStaticMarkup} from 'react-dom/server';
import {QueuePagination,queueOffset} from './queue-pagination';
describe('bounded queue navigation',()=>{
  it('links to previous and next pages and identifies the full queue size',()=>{
    const html=renderToStaticMarkup(<QueuePagination path="/operations" meta={{tenantContext:'tenant',source:'live-reference-api',apiVersion:'v1',correlationId:'id',offset:100,limit:100,total:250}}/>);
    expect(html).toContain('/operations?offset=0');
    expect(html).toContain('/operations?offset=200');
    expect(html).toContain('101–200 of 250');
  });
  it('rejects malformed or unbounded offsets',()=>{
    expect(queueOffset('-1')).toBe(0);expect(queueOffset('10001')).toBe(0);expect(queueOffset('100')).toBe(100);
  });
});
