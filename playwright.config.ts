import { defineConfig } from '@playwright/test';
export default defineConfig({
 testDir:'browser-tests',fullyParallel:false,workers:1,timeout:45000,
 use:{baseURL:process.env.LPC_LAB_URL||'http://127.0.0.1:8765',viewport:{width:1600,height:1100}},
 reporter:'list'
});
