# Dış cron kurulumu (GitHub Scheduled çalışmıyorsa)

GitHub’da `Scheduled` run görünmüyorsa prod için **cron-job.org** (ücretsiz) kullan. Saat dilimi: **Europe/Istanbul**.

## 1. GitHub Personal Access Token

1. https://github.com/settings/tokens → **Fine-grained tokens**
2. Repository access: **Only** `suadiye-kurek-bot`
3. Permissions: **Actions → Read and write**
4. Token’ı kopyala (bir daha gösterilmez)

## 2. cron-job.org hesabı

https://console.cron-job.org → kayıt / giriş

## 3. Poll — 30 dakikada bir

- **Title:** Suadiye poll
- **URL:**

```
https://api.github.com/repos/Batuhancagil/suadiye-kurek-bot/actions/workflows/schedule-poll.yml/dispatches
```

- **Schedule:** Every 30 minutes
- **Timezone:** Europe/Istanbul
- **Request method:** POST
- **Headers:**
  - `Accept: application/vnd.github+json`
  - `Authorization: Bearer BURAYA_TOKEN`
  - `X-GitHub-Api-Version: 2022-11-28`
- **Body (JSON):**

```json
{"ref":"master"}
```

## 4. Burst — haftalık 3 job

Aynı ayarlar, farklı saat ve body:

| Job | TRT saat | workflow dosyası | Body |
|-----|----------|------------------|------|
| Salı dersi | Cuma 06:55 | `schedule-burst.yml` | `{"ref":"master","inputs":{"slot":"tuesday"}}` |
| Perşembe | Pazar 06:55 | `schedule-burst.yml` | `{"ref":"master","inputs":{"slot":"thursday"}}` |
| Cumartesi | Salı 07:55 | `schedule-burst.yml` | `{"ref":"master","inputs":{"slot":"saturday"}}` |

URL örneği (Salı):

```
https://api.github.com/repos/Batuhancagil/suadiye-kurek-bot/actions/workflows/schedule-burst.yml/dispatches
```

## 5. Doğrulama

- GitHub → **Actions** → **Schedule Poll** → yeni run, `workflow_dispatch` (dış cron da böyle görünür)
- Telegram test mesajı / log

## Not

`workflow_dispatch` ile tetiklenen run’lar listede **Scheduled değil**, **Manually run** veya workflow_dispatch yazar — bu normaldir; önemli olan run’ların gelmesidir.
