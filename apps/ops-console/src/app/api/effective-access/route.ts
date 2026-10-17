import {NextRequest,NextResponse} from 'next/server';
import {accessProxy} from '@/lib/server/access-proxy';
export async function GET(request:NextRequest) {
 try {
  const userId=request.nextUrl.searchParams.get('userId');
  const upstream=await accessProxy('/v1/tenant-workspace/effective-access'+(userId?'?userId='+encodeURIComponent(userId):''));
  return NextResponse.json(await upstream.json(),{status:upstream.status,headers:{'Cache-Control':'no-store'}});
 } catch {
  return NextResponse.json({error:{message:'Current access could not be loaded. Check your selected context and retry.'}},{status:403,headers:{'Cache-Control':'no-store'}});
 }
}
