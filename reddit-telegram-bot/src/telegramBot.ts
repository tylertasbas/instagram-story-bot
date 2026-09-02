import { Telegraf } from 'telegraf';
import { config } from './config';
import { addSubreddit, listSubreddits, removeSubreddit, markSeen } from './store';
import { fetchNewPosts } from './reddit';
import { chunkMessage } from './format';

export const bot = new Telegraf(config.telegramToken);

export async function sendFormattedMessage(chatId: string | number, text: string): Promise<void> {
  for (const part of chunkMessage(text)) {
    await bot.telegram.sendMessage(chatId, part, {
      parse_mode: 'HTML',
      link_preview_options: { is_disabled: true },
    });
  }
}

bot.start((ctx) =>
  ctx.reply(
    'Merhaba! Bu bot takip ettiğiniz subreddit\'lerde en az ' +
      config.minComments +
      ' yorum alan yeni başlıkları Türkçeye çevirip buraya gönderir.\n\n' +
      'Komutlar:\n' +
      '/addsub <subreddit> - takibe al (örn: /addsub AskReddit)\n' +
      '/removesub <subreddit> - takipten çıkar\n' +
      '/list - takip edilen subreddit\'ler\n' +
      '/help - yardım'
  )
);

bot.help((ctx) =>
  ctx.reply(
    '/addsub <subreddit>\n/removesub <subreddit>\n/list\n\n' +
      `Tarama sıklığı: ${config.scanIntervalMinutes} dakika, minimum yorum: ${config.minComments}`
  )
);

bot.command('addsub', async (ctx) => {
  const arg = ctx.message.text.split(' ').slice(1).join(' ').trim().replace(/^r\//i, '');
  if (!arg) {
    await ctx.reply('Kullanım: /addsub AskReddit');
    return;
  }
  const chatId = String(ctx.chat.id);
  const added = await addSubreddit(chatId, arg);
  if (!added) {
    await ctx.reply(`r/${arg} zaten listede.`);
    return;
  }

  await ctx.reply(`r/${arg} takibe alındı. Mevcut başlıklar taranıyor, bundan sonraki yeni başlıklar gönderilecek...`);

  try {
    const posts = await fetchNewPosts(arg);
    await markSeen(chatId, arg.toLowerCase(), posts.map((p) => p.id));
    const qualifying = posts.filter((p) => p.numComments >= config.minComments).length;
    await ctx.reply(
      `r/${arg} için başlangıç taraması tamamlandı (${qualifying} başlık kriteri karşılıyordu, bunlar baseline olarak işaretlendi). Yeni gelen başlıklar bir sonraki taramada gönderilecek.`
    );
  } catch (err) {
    await ctx.reply(`r/${arg} taranırken hata oluştu: ${(err as Error).message}. Subreddit adını kontrol edin.`);
  }
});

bot.command('removesub', async (ctx) => {
  const arg = ctx.message.text.split(' ').slice(1).join(' ').trim().replace(/^r\//i, '');
  if (!arg) {
    await ctx.reply('Kullanım: /removesub AskReddit');
    return;
  }
  const removed = await removeSubreddit(String(ctx.chat.id), arg);
  await ctx.reply(removed ? `r/${arg} takipten çıkarıldı.` : `r/${arg} listede değildi.`);
});

bot.command('list', async (ctx) => {
  const subs = await listSubreddits(String(ctx.chat.id));
  if (subs.length === 0) {
    await ctx.reply('Henüz takip edilen subreddit yok. /addsub <subreddit> ile ekleyin.');
    return;
  }
  await ctx.reply('Takip edilenler:\n' + subs.map((s) => `- r/${s}`).join('\n'));
});
