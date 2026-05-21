# Zamanlama — Türkiye saati (TRT, UTC+3)

GitHub Actions **cron her zaman UTC** çalışır. Aşağıdaki saatler **Türkiye saati**dir.

## Poll (30 dakikada bir kontrol)

| Ne | TRT |
|----|-----|
| GitHub tetik (UTC `*/5`) | Her 5 dk (saat farkı yok, sadece UTC kayıt) |
| Gerçek site kontrolü | **30 dakikada bir** (`poll_interval_minutes`) |

**Önerilen (GitHub schedule çalışmıyorsa):** [cron-job.org](https://cron-job.org) → **30 dk**, saat dilimi **Europe/Istanbul** → `schedule-poll.yml` workflow_dispatch.

## Burst (açılıştan 5 dk önce, 15 dk saldırı)

| Ders (TRT) | Rezervasyon açılışı (TRT) | Burst başlar (TRT) |
|------------|---------------------------|---------------------|
| Salı 07:00–08:00 | Cuma 07:00 | **Cuma 06:55** |
| Perşembe 07:00–08:00 | Pazar 07:00 | **Pazar 06:55** |
| Cumartesi 08:00–09:00 | Salı 08:00 | **Salı 07:55** |

GitHub UTC cron (referans):

| Burst | UTC cron |
|-------|----------|
| Salı dersi | `55 3 * * 5` (Cuma 03:55 UTC) |
| Perşembe | `55 3 * * 0` (Pazar 03:55 UTC) |
| Cumartesi | `55 4 * * 2` (Salı 04:55 UTC) |

Dış cron ile burst: cron-job.org’da yukarıdaki **TRT saatlerinde** `schedule-burst.yml` + `slot` parametresi.
