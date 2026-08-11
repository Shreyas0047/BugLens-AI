import { chromium } from '@playwright/test'

const BASE = 'http://localhost:5173'

async function main() {
  const browser = await chromium.launch()
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } })
  const errors = []
  page.on('console', (msg) => {
    if (msg.type() === 'error') errors.push(msg.text())
  })
  page.on('pageerror', (err) => errors.push(err.message))

  await page.goto(BASE, { waitUntil: 'networkidle' })
  await page.screenshot({ path: '/tmp/opencode/ui-home.png' })

  await page.setInputFiles('input[type="file"]', '/tmp/opencode/sample-app.zip')
  await page.getByRole('button', { name: /Upload & analyze/i }).click()
  await page.waitForSelector('text=Analysis queued', { timeout: 15000 })
  await page.screenshot({ path: '/tmp/opencode/ui-queued.png' })

  await page.waitForTimeout(4000)
  await page.goto(`${BASE}/runs`, { waitUntil: 'networkidle' })
  await page.waitForSelector('text=sample-app', { timeout: 15000 })
  await page.waitForTimeout(2500)
  await page.screenshot({ path: '/tmp/opencode/ui-runs.png' })

  await page.goto(`${BASE}/repositories`, { waitUntil: 'networkidle' })
  await page.waitForSelector('text=Python', { timeout: 15000 })
  await page.screenshot({ path: '/tmp/opencode/ui-repos.png' })

  console.log('CONSOLE_ERRORS:', JSON.stringify(errors))
  await browser.close()
}

main().catch((e) => {
  console.error('FAILED:', e.message)
  process.exit(1)
})
