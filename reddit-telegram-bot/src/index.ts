import cron from 'node-cron';
import { config } from './config';
import { bot } from './telegramBot';
import { scanAll } from './scanner';

async function main() {
  console.log('🤖 Reddit -> Telegram bot başlatılıyor...');

  await bot.launch();
  console.log('✅ Telegram bot polling başladı.');

  console.log('🔎 İlk tarama çalıştırılıyor...');
  await scanAll().catch((err) => console.error('İlk tarama hatası:', err));

  const cronExpression = `*/${config.scanIntervalMinutes} * * * *`;
  cron.schedule(cronExpression, () => {
    console.log(`⏰ Zamanlanmış tarama başlıyor (${new Date().toISOString()})`);
    scanAll().catch((err) => console.error('Tarama hatası:', err));
  });

  console.log(`⏱️  Tarama sıklığı: ${config.scanIntervalMinutes} dakika, minimum yorum: ${config.minComments}`);
}

main().catch((err) => {
  console.error('Bot başlatılamadı:', err);
  process.exit(1);
});

process.once('SIGINT', () => bot.stop('SIGINT'));
process.once('SIGTERM', () => bot.stop('SIGTERM'));
