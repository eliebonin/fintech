/** A failed follow-up read must never relabel a confirmed write as a rejection. */
export async function confirmLifecycleBooking<T>(command:()=>Promise<T>,refresh:()=>Promise<unknown>,onCommitted:(result:T)=>void,onRefreshFailed:(error:unknown)=>void):Promise<void>{
 const result=await command();
 onCommitted(result);
 try{await refresh();}catch(error){onRefreshFailed(error);}
}
