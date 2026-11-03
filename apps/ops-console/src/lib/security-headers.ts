/** Per-response script protection; inline styles remain necessary for MUI and charts. */
export function securityHeaders(nonce:string, url:URL):Record<string,string> {
 const development=process.env.NODE_ENV==='development';
 const https=url.protocol==='https:';
 const local=['localhost','127.0.0.1','[::1]'].includes(url.hostname);
 const policy=["default-src 'self'",`script-src 'self' 'nonce-${nonce}' 'strict-dynamic'${development?" 'unsafe-eval'":''}`,
  "style-src 'self' 'unsafe-inline'","img-src 'self' data: blob:","font-src 'self'",
  `connect-src 'self'${development?' ws: wss:':''}`,"object-src 'none'","base-uri 'self'",
  "form-action 'self'","frame-ancestors 'self'",...(https&&!local?['upgrade-insecure-requests']:[])].join('; ');
 return {'Content-Security-Policy':policy,'X-Content-Type-Options':'nosniff',
  'X-Frame-Options':'SAMEORIGIN','Referrer-Policy':'strict-origin-when-cross-origin',
  'Permissions-Policy':'camera=(), microphone=(), geolocation=()',
  ...(https&&!local?{'Strict-Transport-Security':'max-age=31536000'}:{})};
}
