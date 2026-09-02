# Reddit → Telegram Bot

Takip ettiğiniz subreddit'lerde en az `MIN_COMMENTS` (varsayılan 10) yorum almış
YENİ başlıkları belirli aralıklarla tarar, başlığı ve öne çıkan yorumları
Türkçeye çevirir, Telegram'daki ilgili sohbete gönderir.

## Nasıl çalışır

- Reddit'in herkese açık `.json` uçları kullanılır (API key gerekmez).
- Çeviri için ücretsiz, key gerektirmeyen Google Translate uç noktası kullanılır.
- Subreddit takibi Telegram komutlarıyla yönetilir, sohbet başına ayrı liste tutulur.
- Bir subreddit ilk eklendiğinde mevcut başlıklar "baseline" olarak işaretlenir,
  spam olmaması için sadece bundan SONRA gelen yeni başlıklar gönderilir.
- Zaten gönderilmiş başlıklar `data/subscriptions.json` içinde tutulur, tekrar gönderilmez.

## Kurulum

```bash
cd reddit-telegram-bot
npm install
cp .env.example .env
```

`.env` dosyasını doldurun:

1. Telegram'da **@BotFather**'a gidip `/newbot` ile bot oluşturun, verdiği tokenı
   `TELEGRAM_BOT_TOKEN` alanına yapıştırın.
2. İsterseniz `MIN_COMMENTS`, `SCAN_INTERVAL_MINUTES`, `MAX_POSTS_PER_SCAN`,
   `TOP_COMMENTS_COUNT` değerlerini değiştirin.
3. `REDDIT_USER_AGENT` alanını kendi kullanıcı adınızla güncellemeniz önerilir
   (Reddit, ortak/boş User-Agent'ları sınırlayabilir).

Çalıştırın:

```bash
npm start
```

## Telegram komutları

| Komut | Açıklama |
|---|---|
| `/start` | Botu tanıtır |
| `/addsub <subreddit>` | Subreddit'i bu sohbete takibe alır (örn. `/addsub AskReddit`) |
| `/removesub <subreddit>` | Takipten çıkarır |
| `/list` | Bu sohbette takip edilen subreddit'leri listeler |
| `/help` | Komut listesi ve ayarları gösterir |

Bota Telegram'dan `r/AskReddit` şeklinde de yazabilirsiniz, `r/` öneki otomatik silinir.

## 7/24 çalıştırma (VPS)

Bot uzun süre ayakta kalması gereken bir polling process'i, bu yüzden bir
VPS/sunucuda arka planda çalıştırılması önerilir:

```bash
npm install -g pm2
cd reddit-telegram-bot
npm install
npm run build
pm2 start dist/index.js --name reddit-telegram-bot
pm2 save
pm2 startup   # sunucu yeniden başlayınca otomatik ayağa kalkması için
```

Loglara bakmak için: `pm2 logs reddit-telegram-bot`

## Notlar / sınırlamalar

- Reddit'in public JSON uçları kimliksiz (anonim) istek olduğu için zaman zaman
  hız sınırına takılabilir; tarama sıklığını çok düşürmeyin (10 dk altı önerilmez).
- Ücretsiz çeviri uç noktası resmi bir API değildir, çok yoğun kullanımda ara
  sıra hata verebilir — bot bu durumda çevrilmemiş orijinal metni gönderir.
- `data/subscriptions.json` dosyası silinirse tüm takip listeleri ve "görüldü"
  kayıtları sıfırlanır (bir sonraki taramada baseline'lar yeniden oluşur).
