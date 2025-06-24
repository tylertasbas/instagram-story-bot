import puppeteer from 'puppeteer';
import fs from 'fs-extra';
import path from 'path';
import fetch from 'node-fetch';

export async function downloadStoriesFromLocation(locationUrl: string) {
  const browser = await puppeteer.launch({ headless: true, args: ['--no-sandbox'] });
  const page = await browser.newPage();

  console.log("📍 Sayfa açılıyor:", locationUrl);
  await page.goto(locationUrl, { waitUntil: 'networkidle2' });

  // Basit örnek: Sayfadaki hikaye img'lerini al
  const imgUrls = await page.evaluate(() => {
    const images = Array.from(document.querySelectorAll('img'));
    return images.map(img => img.src).filter(src => src.includes('/stories/'));
  });

  const today = new Date().toISOString().split('T')[0];
  const outputDir = path.join(__dirname, `../downloads/${today}`);
  fs.ensureDirSync(outputDir);

  for (let i = 0; i < imgUrls.length; i++) {
    const res = await fetch(imgUrls[i]);
    const buffer = await res.arrayBuffer();
    fs.writeFileSync(`${outputDir}/story_${i}.jpg`, Buffer.from(buffer));
  }

  await browser.close();
  console.log(`✅ Toplam ${imgUrls.length} story indirildi.`);
}

if (require.main === module) {
  const url = 'https://www.instagram.com/explore/locations/212988663/mekan-adi/';
  downloadStoriesFromLocation(url);
}