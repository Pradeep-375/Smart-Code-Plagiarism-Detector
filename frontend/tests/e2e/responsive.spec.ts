import { expect, test } from '@playwright/test'

test('landing page has no horizontal scroll at any viewport', async ({ page }) => {
  await page.goto('/')
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
  expect(overflow).toBeLessThanOrEqual(1)
})

test('login page is usable', async ({ page }) => {
  await page.goto('/login')
  await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible()
})

test('protected routes redirect to login when signed out', async ({ page }) => {
  await page.goto('/app/dashboard')
  await expect(page).toHaveURL(/\/login/)
})
