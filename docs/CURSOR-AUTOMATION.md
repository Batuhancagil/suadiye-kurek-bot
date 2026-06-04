# Cursor izleme otomasyonu

Suadiye Kürek botu için **izleme-only** Cursor Automation. Rezervasyon veya site girişi yapmaz.

## Tetikleyiciler

| Tetik | Zaman / kaynak | Komut |
|-------|----------------|-------|
| Haftalık sağlık | Pazartesi 06:00 UTC (`0 6 * * 1`) | `python scripts/automation_health_check.py --mode weekly` |
| Deploy | Webhook `event=deploy` veya Railway | `--mode deploy` |
| Hata / alert | Webhook `event=error` | `--mode smoke --extra "<özet>"` |

## Kurulum (Cloud Agent)

1. `pip install -r requirements.txt`
2. Ortam değişkenleri:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID` (virgülle çoklu id desteklenir)

## Script

`scripts/automation_health_check.py`:

- **pytest** — `tests/` (Playwright / SuperSaaS yok)
- **Statik** — import, config, slot 4-gün kuralı, burst cron satırları (weekly/deploy)
- **Telegram** — özet rapor (`src.notify.send_telegram`)

Yerel deneme (Telegram atlamak için):

```bash
python scripts/automation_health_check.py --mode weekly --skip-telegram
```

## Kurallar

- ASLA SuperSaaS rezervasyonu yapma
- ASLA Playwright ile gerçek giriş / booking testi çalıştırma
- Büyük refactor yok; bariz küçük fix dışında PR açma

## Çıktı formatı (agent özeti)

Her koşuda: tetikleyici, test sonucu, Telegram durumu, PR açıldı mı.

## İlgili dokümanlar

- [RAILWAY-DEPLOY.md](RAILWAY-DEPLOY.md) — deploy webhook ve Railway
- [CRON-TRT.md](CRON-TRT.md) — burst/poll zamanları
