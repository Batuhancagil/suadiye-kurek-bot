# Suadiye Kürek Kulübü — Rezervasyon Botu

SuperSaaS ders takviminde hedef slotlar için otomatik rezervasyon:

| Gün | Saat |
|-----|------|
| Salı | 07:00–08:00 |
| Perşembe | 07:00–08:00 |
| Cumartesi | 08:00–09:00 |

Rezervasyonlar ders başlangıcından **tam 4 gün** önce açılır. Bot iki modda çalışır:

- **burst**: Açılıştan 5 dk önce başlar, 15 dk boyunca yoğun dener (Telegram: saldırı başladı + kayıt oldu)
- **poll**: `config.json` içindeki aralıkta periyodik kontrol (iptal / kaçırılan yerler)

## Kurulum (yerel)

```bash
cd suadiye-kurek-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp config.example.json config.json
cp .env.example .env
# .env dosyasını düzenle
```

## Yapılandırma (`config.json`)

```json
{
  "poll_interval_minutes": 30,
  "burst_start_before_minutes": 5,
  "burst_retry_interval_seconds": 8,
  "burst_duration_minutes": 15
}
```

| Alan | Açıklama |
|------|----------|
| `poll_interval_minutes` | Poll modunda kontrol aralığı (dk) |
| `burst_start_before_minutes` | Açılıştan kaç dk önce saldırı (cron ile uyumlu: 5) |
| `burst_retry_interval_seconds` | Burst denemeleri arası (sn) |
| `burst_duration_minutes` | Burst toplam süresi (dk) |

## Yerel çalıştırma

```bash
# Dry-run (Telegram + log, siteye minimum dokunuş burst'ta)
python -m src.main --mode burst --slot tuesday --dry-run

# Burst — tek slot
python -m src.main --mode burst --slot thursday

# Poll — tüm slotlar (aralık config'den)
python -m src.main --mode poll --slot all

# Poll — hemen çalış (aralığı yoksay)
python -m src.main --mode poll --force-poll

# Görünür tarayıcı (selector debug)
HEADLESS=0 python -m src.main --mode poll --slot tuesday --headed
```

### Selector inceleme

```bash
python scripts/inspect_login_page.py
python scripts/inspect_interactive.py   # .env ile login + page.pause()
```

## GitHub Actions

### 1. Repoyu GitHub'a push et

Bu klasörü ayrı bir repo olarak push edebilirsin (`suadiye-kurek-bot`).

### 2. Secrets ekle

Repository → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**:

| Secret | Açıklama |
|--------|----------|
| `SUPERSAAS_EMAIL` | SuperSaaS giriş e-postası |
| `SUPERSAAS_PASSWORD` | SuperSaaS şifresi |
| `TELEGRAM_BOT_TOKEN` | BotFather token |
| `TELEGRAM_CHAT_ID` | Chat id — **birden fazla** için virgülle ayır: `123456789,-1009876543210` |

İsteğe bağlı: `TELEGRAM_CHAT_IDS` (aynı format; `TELEGRAM_CHAT_ID` ile birleştirilir, tekrarlar elenir).

### 3. Telegram bot kurulumu

1. Telegram'da [@BotFather](https://t.me/BotFather) → `/newbot` → token al
2. Bota bir mesaj at
3. Chat ID: `https://api.telegram.org/bot<TOKEN>/getUpdates` içindeki `chat.id`
   veya [@userinfobot](https://t.me/userinfobot)

**Birden fazla kişi / grup:**

```env
TELEGRAM_CHAT_ID=111111111,222222222,-1001234567890
```

GitHub Secret'ta da aynı şekilde tek satırda virgülle yazabilirsin.

### 4. Workflow'lar

| Workflow | Tetik | Açıklama |
|----------|-------|----------|
| `burst.yml` | Cron + manual | Salı/Per/Cmt açılıştan 5 dk önce |
| `poll.yml` | Her 5 dk | `poll_interval_minutes` ile gerçek sıklık |

**Manuel dry-run (GitHub):** Actions → **Burst Rezervasyon** → **Run workflow** → slot seç.

### Cron takvimi (UTC)

| Slot | Açılış (TRT) | Cron (UTC, T-5 dk) |
|------|----------------|---------------------|
| Salı 07:00 | Cuma 07:00 | `55 3 * * 5` |
| Perşembe 07:00 | Pazar 07:00 | `55 3 * * 0` |
| Cumartesi 08:00 | Salı 08:00 | `55 4 * * 2` |

`burst_start_before_minutes` değiştirirsen bu cron satırlarını da güncelle.

## Bildirimler

- **Burst başlangıcı:** `[SALDIRI] ... denemeler başladı`
- **Kayıt:** `[OK] ... rezerve edildi`
- **Hata:** `[ERR] ...` (+ workflow artifact screenshot)

Yer yok / henüz açılmadı / zaten kayıtlı → sessiz (sadece log).

## Güvenlik

- `.env` ve `config.json` (şifre içermiyorsa commit edilebilir) — **asla** şifreleri repoya commit etme
- GitHub Secrets kullan
