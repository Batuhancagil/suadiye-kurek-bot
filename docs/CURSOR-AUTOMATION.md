# Cursor İzleme Otomasyonu

Suadiye Kürek botu için haftalık sağlık, deploy ve hata tetikleyicileri.

## Tetikleyiciler

| Tetik | Mod | Komut |
|-------|-----|-------|
| Cron Pazartesi 06:00 UTC | `weekly` | `python scripts/automation_health_check.py --mode weekly` |
| Webhook `event=deploy` | `deploy` | `python scripts/automation_health_check.py --mode deploy` |
| Webhook `event=error` | `smoke` | `python scripts/automation_health_check.py --mode smoke --extra "..."` |

## Kurallar

- **ASLA** SuperSaaS rezervasyonu yapma
- **ASLA** Playwright ile siteye gerçek giriş yapma
- Yalnızca birim testleri, import, config ve workflow dosya kontrolleri

## Ortam değişkenleri

Cloud Agent ortamında:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID` (veya `TELEGRAM_CHAT_IDS`)

Script sonucu Telegram'a `[İZLEME]` etiketiyle gönderilir.

## Kontroller

### weekly / deploy

- Temel dosyalar (`src/`, `config.example.json`, workflow'lar)
- `config` yükleme
- Modül import'ları
- Slot açılış zamanı (4 gün kuralı)
- `pytest tests/`

### smoke

- Temel dosyalar + config + import
- `pytest tests/`
- `--extra` ile webhook özeti rapora eklenir

## Çıkış kodu

- `0` — tüm kontroller geçti
- `1` — en az bir kontrol başarısız
