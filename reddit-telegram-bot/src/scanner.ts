import { config } from './config';
import { fetchNewPosts, fetchTopComments } from './reddit';
import { getAllChats, isSeen, markSeen } from './store';
import { translateText } from './translate';
import { buildPostMessage, FormattedComment } from './format';
import { sendFormattedMessage } from './telegramBot';

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function scanSubredditForChat(chatId: string, subreddit: string): Promise<void> {
  const posts = await fetchNewPosts(subreddit);

  const unseenQualifying = [];
  for (const post of posts) {
    if (post.numComments < config.minComments) continue;
    if (await isSeen(chatId, subreddit, post.id)) continue;
    unseenQualifying.push(post);
  }

  unseenQualifying.sort((a, b) => a.createdUtc - b.createdUtc);
  const toSend = unseenQualifying.slice(-config.maxPostsPerScan);

  for (const post of toSend) {
    try {
      const translatedTitle = await translateText(post.title);
      const rawComments = await fetchTopComments(subreddit, post.id, config.topCommentsCount);

      const comments: FormattedComment[] = [];
      for (const c of rawComments) {
        const translated = await translateText(c.body);
        comments.push({ author: c.author, translated, score: c.score });
        await sleep(250);
      }

      const message = buildPostMessage(post, translatedTitle, comments);
      await sendFormattedMessage(chatId, message);
    } catch (err) {
      console.error(`[${subreddit}] Başlık gönderilemedi (${post.id}):`, (err as Error).message);
    }
  }

  await markSeen(
    chatId,
    subreddit,
    posts.map((p) => p.id)
  );
}

export async function scanAll(): Promise<void> {
  const chats = await getAllChats();
  for (const { chatId, subreddits } of chats) {
    for (const subreddit of subreddits) {
      try {
        await scanSubredditForChat(chatId, subreddit);
      } catch (err) {
        console.error(`[${subreddit}] Tarama hatası:`, (err as Error).message);
      }
      await sleep(1000);
    }
  }
}
