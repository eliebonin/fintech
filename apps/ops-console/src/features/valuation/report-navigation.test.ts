import {afterEach,expect,it,vi} from 'vitest';
import {readReportLocation,reportHash,writeReportLocation} from './report-navigation';

afterEach(()=>vi.unstubAllGlobals());
it('round trips the selected attempt and report without changing query filters',()=>{
 expect(reportHash({attemptId:'run-123',view:'positions'})).toBe('#valuationRun=run-123&report=positions');
 expect(readReportLocation('#valuationRun=run-123&report=positions')).toEqual({attemptId:'run-123',view:'positions'});
 expect(readReportLocation('#valuationRun=run-123')).toEqual({attemptId:'run-123',view:'breakdown'});
 for(const hash of ['', '#unrelated', '#valuationRun=&report=logs','#valuationRun=run&report=unknown','#valuationRun=..%2Fprivate&report=logs'])expect(readReportLocation(hash)).toBeNull();
});
it('changes only the fragment and avoids duplicate browser history entries',()=>{
 const pushState=vi.fn(),replaceState=vi.fn();
 const location={pathname:'/valuation',search:'?view=results',hash:''};
 vi.stubGlobal('window',{location,history:{pushState,replaceState}});
 writeReportLocation({attemptId:'run-123',view:'logs'});
 expect(pushState).toHaveBeenCalledWith(null,'','/valuation?view=results#valuationRun=run-123&report=logs');
 location.hash='#valuationRun=run-123&report=logs';
 writeReportLocation({attemptId:'run-123',view:'logs'});expect(pushState).toHaveBeenCalledTimes(1);
 writeReportLocation({attemptId:'run-123',view:'review'},'replace');
 expect(replaceState).toHaveBeenCalledWith(null,'','/valuation?view=results#valuationRun=run-123&report=review');
 writeReportLocation(null);expect(pushState).toHaveBeenLastCalledWith(null,'','/valuation?view=results');
});
