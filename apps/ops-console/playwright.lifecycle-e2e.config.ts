import {defineConfig} from '@playwright/test';
import path from 'node:path';
const stateFile=process.env.LIFECYCLE_E2E_STATE_FILE;
if(!stateFile)throw new Error('Run live lifecycle acceptance through scripts/run_lifecycle_panel_acceptance.py');
export default defineConfig({testDir:'./browser-tests',testMatch:'lifecycle-panel.live.ts',workers:1,timeout:120000,expect:{timeout:15000},outputDir:path.join(path.dirname(stateFile),'playwright-output'),
 use:{baseURL:process.env.LIFECYCLE_E2E_BASE_URL,headless:true,trace:'retain-on-failure',launchOptions:process.env.PLAYWRIGHT_CHANNEL?{channel:process.env.PLAYWRIGHT_CHANNEL}:{},viewport:{width:1360,height:950}}});
