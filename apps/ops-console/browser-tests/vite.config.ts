import {defineConfig} from 'vite';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const root=path.dirname(fileURLToPath(import.meta.url));
export default defineConfig({root,resolve:{alias:{'@':path.resolve(root,'../src'),'next/link':path.resolve(root,'next-link.tsx'),'next/navigation':path.resolve(root,'next-navigation.ts')}},oxc:{jsx:{runtime:'automatic'}},server:{host:'127.0.0.1',port:3118,strictPort:true,fs:{allow:[path.resolve(root,'..')]}}});
