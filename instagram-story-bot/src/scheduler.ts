// instagram-story-bot/src/scheduler.ts

import cron from 'node-cron';
import { downloadStoriesFromLocation } from './storyBot';

const locationUrl = 'https://www.instagram.com/explore/locations/212988663/mekan-adi/';

cron.schedule('0 10 * * *', async () => {
  console.log('⏰ Günlük Instagram story çekimi başlıyor...');
  await downloadStoriesFromLocation(locationUrl);
});

// instagram-story-bot/.env.example

# Instagram kullanıcı bilgileri (isteğe bağlı)
IG_USERNAME=your_username
IG_PASSWORD=your_password

# Chromium yolu (gerekirse belirtin)
CHROME_EXECUTABLE_PATH=/usr/bin/google-chrome

// instagram-story-bot/package.json

{
  "name": "instagram-story-bot",
  "version": "1.0.0",
  "main": "src/storyBot.ts",
  "type": "module",
  "scripts": {
    "start": "ts-node src/storyBot.ts",
    "schedule": "ts-node src/scheduler.ts"
  },
  "dependencies": {
    "dotenv": "^16.3.1",
    "fs-extra": "^11.1.1",
    "node-fetch": "^3.3.2",
    "puppeteer": "^22.0.0"
  },
  "devDependencies": {
    "@types/node": "^20.11.30",
    "ts-node": "^10.9.2",
    "typescript": "^5.4.5"
  }
}