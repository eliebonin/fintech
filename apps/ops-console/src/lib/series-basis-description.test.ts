import {it,expect} from 'vitest';
import {describeSeriesBasis} from './series-basis-description';
it('describes reconstructed RAW without calling it split-adjusted or official',()=>{
 const text=describeSeriesBasis(['RAW']);expect(text).toContain('Reconstructed');expect(text).toContain('not an exchange-certified');expect(text).not.toContain('Close is split-adjusted');
});
it('explains split and distribution adjustment separately and does not infer an empty basis',()=>{
 expect(describeSeriesBasis(['SPLIT_ADJUSTED'])).toContain('split-adjusted');expect(describeSeriesBasis(['VENDOR_ADJUSTED'])).toContain('distribution');expect(describeSeriesBasis([])).toContain('Inspect');
});
