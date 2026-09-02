import { RedditPost } from './types';

function escapeHtml(text: string): string {
  return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

export interface FormattedComment {
  author: string;
  translated: string;
  score: number;
}

export function buildPostMessage(post: RedditPost, translatedTitle: string, comments: FormattedComment[]): string {
  const lines: string[] = [];
  lines.push(`<b>r/${escapeHtml(post.subreddit)}</b>`);
  lines.push(`<b>${escapeHtml(translatedTitle)}</b>`);
  lines.push(`👍 ${post.score} &nbsp;|&nbsp; 💬 ${post.numComments}`);
  lines.push(`🔗 <a href="${escapeHtml(post.permalink)}">Reddit'te aç</a>`);

  if (comments.length > 0) {
    lines.push('');
    lines.push('<b>Öne çıkan yorumlar:</b>');
    comments.forEach((c, i) => {
      lines.push(`${i + 1}. <i>u/${escapeHtml(c.author)}</i> (👍${c.score}): ${escapeHtml(c.translated)}`);
    });
  }

  return lines.join('\n');
}

export function chunkMessage(text: string, maxLen = 4000): string[] {
  if (text.length <= maxLen) return [text];
  const parts: string[] = [];
  let remaining = text;
  while (remaining.length > maxLen) {
    let splitAt = remaining.lastIndexOf('\n', maxLen);
    if (splitAt <= 0) splitAt = maxLen;
    parts.push(remaining.slice(0, splitAt));
    remaining = remaining.slice(splitAt).trimStart();
  }
  if (remaining.length > 0) parts.push(remaining);
  return parts;
}
