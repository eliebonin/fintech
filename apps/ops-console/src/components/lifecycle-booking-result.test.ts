import {expect,it,vi} from 'vitest';
import {confirmLifecycleBooking} from './lifecycle-booking-result';
it('keeps a confirmed booking when only history refresh fails',async()=>{
 const booked=vi.fn(),failedRead=vi.fn();const command=vi.fn(async()=>({trade_ids:['one','two']}));
 await confirmLifecycleBooking(command,async()=>{throw new Error('Read failed');},booked,failedRead);
 expect(command).toHaveBeenCalledTimes(1);expect(booked).toHaveBeenCalledWith({trade_ids:['one','two']});expect(failedRead).toHaveBeenCalledTimes(1);
});
it('leaves an uncertain write retryable without announcing success',async()=>{
 const booked=vi.fn(),failedRead=vi.fn(),refresh=vi.fn();
 await expect(confirmLifecycleBooking(async()=>{throw new Error('Response lost');},refresh,booked,failedRead)).rejects.toThrow('Response lost');
 expect(booked).not.toHaveBeenCalled();expect(refresh).not.toHaveBeenCalled();expect(failedRead).not.toHaveBeenCalled();
});
