/** HTTPS derives from the served URL, not NODE_ENV: optimized local runs use HTTP. */
export function sessionCookieOptions(request:Request,maxAge:number) {
 return {httpOnly:true,secure:new URL(request.url).protocol==='https:',sameSite:'strict' as const,path:'/',maxAge};
}
