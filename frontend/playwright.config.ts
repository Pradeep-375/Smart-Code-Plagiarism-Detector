import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests/e2e',
  use: { baseURL: process.env.E2E_BASE_URL ?? 'http://localhost:5173' },
  webServer: process.env.E2E_BASE_URL ? undefined : { command: 'npm run dev', url: 'http://localhost:5173', reuseExistingServer: true },
  projects: [
    { name: 'mobile', use: { ...devices['Pixel 7'] } },
    { name: 'tablet', use: { ...devices['iPad (gen 7)'] } },
    { name: 'desktop', use: { ...devices['Desktop Chrome'] } },
  ],
})
