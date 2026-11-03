import {expect,it} from 'vitest';
import {sessionCookieOptions} from './session-cookie';

it('sets Secure on HTTPS for both session creation and clearing, preserving HTTP local testing',()=>{
 for(const age of [14400,0]){
  expect(sessionCookieOptions(new Request('https://example.test/api/session/context'),age)).toMatchObject({secure:true,httpOnly:true,sameSite:'strict',path:'/',maxAge:age});
  expect(sessionCookieOptions(new Request('http://localhost/api/session/context'),age).secure).toBe(false);
 }
});
