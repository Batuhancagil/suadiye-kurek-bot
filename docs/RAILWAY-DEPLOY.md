# Railway deploy ve webhook

Bot varsayılan olarak **GitHub Actions** üzerinde çalışır. Railway kullanılıyorsa deploy/hata webhook'ları Cursor izleme otomasyonunu tetikleyebilir.

## Deploy webhook

Payload örneği:

```json
{
  "event": "deploy",
  "service": "suadiye-kurek-bot",
  "status": "success"
}
```

Agent akışı:

1. `pip install -r requirements.txt`
2. `python scripts/automation_health_check.py --mode deploy`
3. Telegram raporunun gittiğini doğrula

## Hata webhook

```json
{
  "event": "error",
  "message": "kısa hata özeti",
  "logs_snippet": "son log satırları"
}
```

Agent akışı:

1. `message` ve `logs_snippet` oku
2. `python scripts/automation_health_check.py --mode smoke --extra "<özet>"`
3. `docs/RAILWAY-DEPLOY.md` ve ilgili `src/` dosyalarını incele
4. Net küçük fix varsa PR; belirsizse yalnızca Telegram + öneri

## Ortam

Railway / Cloud Agent'ta GitHub Actions ile aynı secret'lar:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- (çalışma zamanı botu için) `SUPERSAAS_EMAIL`, `SUPERSAAS_PASSWORD` — izleme scripti bunları **kullanmaz**

## Not

İzleme otomasyonu canlı siteye bağlanmaz; yalnızca birim testleri ve statik kontroller çalıştırır.
