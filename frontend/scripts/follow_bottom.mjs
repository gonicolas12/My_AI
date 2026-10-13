// Le fil suit la réponse : distance au bas pendant une longue réponse, sans défilement manuel
// Usage (depuis frontend/) : node scripts/follow_bottom.mjs URL_AVEC_JETON
import { composer, openDemo, usage, waitReady } from './lib.mjs';

const [, , url] = process.argv;
if (!url) usage('node scripts/follow_bottom.mjs URL_AVEC_JETON');
const { browser, page } = await openDemo(url);
await waitReady(page);
await page.keyboard.press('Control+n');
await page.waitForTimeout(400);
await composer(page).fill('Écris une réponse long format');
await composer(page).press('Enter');
await page.waitForSelector('[aria-busy="true"]');
const samples = [];
for (let i = 0; i < 40; i += 1) {
  await page.waitForTimeout(250);
  samples.push(
    await page.evaluate(() => {
      const s = document.querySelector('[data-testid="virtuoso-scroller"]');
      return s ? Math.round(s.scrollHeight - s.scrollTop - s.clientHeight) : -1;
    }),
  );
}
console.log('distance au bas (px) :', samples.join(' '));
console.log(
  `max ${Math.max(...samples)} — échantillons à plus de 40 px : ${samples.filter((d) => d > 40).length}`,
);
await page.keyboard.press('Escape');
await browser.close();
