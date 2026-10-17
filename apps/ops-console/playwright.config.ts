import {defineConfig} from '@playwright/test';
export default defineConfig({testDir:'./browser-tests',testMatch:'*.spec.ts',fullyParallel:false,workers:1,timeout:30000,
 use:{baseURL:'http://127.0.0.1:3118',headless:true,trace:'retain-on-failure',launchOptions:process.env.PLAYWRIGHT_CHANNEL?{channel:process.env.PLAYWRIGHT_CHANNEL}:{},viewport:{width:1280,height:900}},
 webServer:[{command:'pnpm exec vite --config browser-tests/vite.config.ts',url:'http://127.0.0.1:3118',reuseExistingServer:false,timeout:30000},
 {command:'pnpm exec next dev -p 3119',port:3119,reuseExistingServer:false,timeout:60000,env:{NEXT_DIST_DIR:'.next-frontend-acceptance',REFERENCE_API_URL:'http://127.0.0.1:9'}}]});
