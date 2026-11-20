# LLM and guest workspace repair — 20 November 2026

## Deployment evidence and root causes

Checkout and latest Vercel production deployment both used commit `6dc21a8d70a3b205f0222aa7923966ab4429755f` when inspected. Project `clinicalai` uses the Services framework. Deployment `dpl_GRPTVTiuXbfjHSwP7S71z2N3QPjh` remained the latest production deployment. Current runtime logs confirmed `GET /api/v1/llm/providers` and `POST /api/v1/workspace` failed during import because `STORAGE_BUCKET`, `STORAGE_ACCESS_KEY_ID`, and `STORAGE_SECRET_ACCESS_KEY` were missing.

S3 readiness was coupled to global settings construction. It now runs before S3 client initialization. Missing storage returns a sanitized 503 for report operations, while provider metadata, workspace bootstrap and other unrelated routes can start. Production still requires S3; no local disk or memory fallback was added. `/api/v1/health` is liveness; `/api/v1/readiness` checks storage configuration and database migration version. Readiness does not certify bucket permissions or perform an upload.

The existing Vercel multi-service configuration was checked against official routing documentation and retained. Backend dependencies already declare boto3 and psycopg. PostgreSQL schema installation remains an explicit deployment operation. Local startup now runs migrations through head instead of stopping as soon as workspace columns exist.

## Implementation

- `backend/app/core/config.py`, `services/report_storage.py`, `api/routes/health.py`, `main.py`: separate storage readiness, safe storage failure, schema readiness and local migration execution.
- `backend/app/ai/providers.py`, new `ai/endpoints.py`: OpenAI Responses, Gemini generateContent, Anthropic Messages, OpenRouter/Groq/Custom Chat Completions; credential discovery, text-model filtering, sanitized errors and bounded tests. Custom requests require HTTPS port 443, reject URL credentials/query/fragment, check every resolved IP, pin connections to a checked public IP while retaining TLS hostname verification, disable proxies and redirects.
- `backend/app/services/llm.py`, `api/routes/llm.py`, `api/workspace.py`, `db/models.py`: encrypted multiple entries, list/edit/test/remove/activate, exact active-provider execution, stable session cookie, endpoint-bound custom ciphertext, compatible model IDs up to 255 characters. Removing/expiring the active entry does not choose another entry. The first saved entry becomes active; later additions require explicit activation.
- `frontend/src/api/{client,llm}.ts`, `pages/LLMSettingsPage.tsx`: six provider choices, endpoint and manual model controls, key-first discovery, fallback/discovered/tested distinctions, saved entries and active display, cancellation of stale responses, bounded workspace-expiry retry. Keys remain in component memory only until saved or changed.
- Tests cover synthetic clinical flows, adapters, discovery, safe failures, SSRF, migration preservation, session restrictions, workspace isolation, browser recovery and discovery races.

## Migration

`backend/alembic/versions/20261120_0001_multiple_llm.py`, after `20261112_0002`, copies the old table into the new schema. Existing workspace IDs become stable configuration IDs. Existing ciphertext, provider, model, session hash and expiry are copied unchanged; existing entries remain active. New rows use UUIDs; a partial unique index allows one active entry per workspace. Custom endpoint binding is added only to newly saved custom entries. Downgrade deliberately refuses a lossy conversion to one entry per workspace; restore a verified backup if rollback is required.

Back up the database, then from `backend` run `python -m alembic -c alembic.ini upgrade head`. Use a trusted environment with the direct Neon URL. Do not run schema creation against production from request handlers.

## Required Vercel operations (not performed)

Set these on the **backend service**, for each intended deployment environment:

| Variable | Required value/purpose |
|---|---|
| `ENVIRONMENT` | `production` |
| `DEBUG` | `false` |
| `DATABASE_URL` | PostgreSQL/Neon connection URL with TLS (`sslmode=require` or stronger); runtime pooled URL is supported |
| `DIRECT_DATABASE_URL` | Direct TLS PostgreSQL/Neon URL for the migration job; optional if DATABASE_URL is suitable for migrations |
| `WORKSPACE_SIGNING_SECRET` | Existing generated secret, at least 32 bytes; retain existing value |
| `LLM_ENCRYPTION_KEY` | Existing valid Fernet key; retain it to preserve saved credentials |
| `FRONTEND_URL` | `https://clinicalai-kappa.vercel.app` |
| `ALLOWED_CORS_ORIGINS` | Optional additional exact HTTPS origins; no wildcard. Production origin must be included through this or FRONTEND_URL |
| `STORAGE_PROVIDER` | `s3` |
| `STORAGE_BUCKET` | Real private report bucket — confirmed missing |
| `STORAGE_ACCESS_KEY_ID` | Real bucket-scoped credential — confirmed missing |
| `STORAGE_SECRET_ACCESS_KEY` | Matching secret — confirmed missing |
| `STORAGE_REGION` | Bucket region (default `us-east-1`; set the correct actual region) |
| `STORAGE_ENDPOINT` | HTTPS service endpoint for S3-compatible storage; omit for standard AWS S3 |

The frontend keeps the same-origin `/api/v1` default; no provider key belongs in VITE variables. Optional `OPENAI_MODELS` and `GEMINI_MODELS` configure fallback suggestions only. Visitors supply provider-specific keys through the settings page.

Configure private bucket permissions for read/write/delete of `reports/` and `pending-reports/`, browser POST CORS for the exact production origin, and lifecycle cleanup for abandoned staged uploads. Keep existing encrypted report storage controls. Verify real bucket policy and permissions with synthetic content after deployment authorization.

After separately authorized migration and deployment: check health, readiness, OpenAPI, all provider metadata, new and returning browser workspace cookies, two-browser isolation, configuration routes, and a synthetic report upload/download/delete. Production cookies must remain Secure, HttpOnly, SameSite=Lax, Path=/ with the `__Host-` prefix and no Domain. Do not rotate the encryption key as a routine configuration fix.

## Verification scope

Automated provider tests use mocks and synthetic credentials/data. No paid live connection or clinical generation was requested. Live account entitlements, custom endpoint TLS networking, bucket permissions and Neon migrations require operational verification. No push, deployment, environment mutation or real patient data was used.

Official contracts consulted: [OpenAI model listing](https://developers.openai.com/api/reference/resources/models/methods/list), [Gemini models](https://ai.google.dev/api/models), [Anthropic API](https://platform.claude.com/docs/en/api/overview), [Anthropic models](https://platform.claude.com/docs/en/api/models/list), [OpenRouter chat](https://openrouter.ai/docs/api/api-reference/chat/send-chat-completion-request), [OpenRouter models](https://openrouter.ai/docs/api/api-reference/models/get-models), [Groq API](https://console.groq.com/docs/api-reference), and [Vercel Services routing](https://vercel.com/docs/services/routing). Model listings are candidates, not a guarantee of generation access; a successful request is required before persistence marks an entry tested.

Anthropic uses API version `2026-10-21` without the removed sampling parameters, following the [current migration guide](https://platform.claude.com/docs/en/api/migration-2026-10-21). Groq uses `max_completion_tokens`; OpenRouter and Custom use the Chat Completions `max_tokens` contract.

For the frontend service set `VITE_DIRECT_REPORT_UPLOADS=true` to enable the existing direct S3 browser upload flow (verified separately with intercepted synthetic requests). Keep `VITE_API_BASE_URL` unset for the existing same-origin `/api/v1` routing.

## Recorded test results

- `python -m pytest tests/backend -o addopts='' -q`: **81 passed, 3 failed, 1 skipped**. The failures are the two production-startup variants (missing local `psycopg`) and S3 policy test (missing local `boto3`). Both packages are already declared in `backend/requirements.txt`. Installation attempts from PyPI stalled or timed out; the stalled download was stopped. These failures are not suppressed.
- Additional fresh-process startup regression: **1 passed**, using a disposable SQLite database with S3 selected and all three storage credentials absent. Verifies health, degraded readiness, OpenAPI, six providers and metadata entries, workspace creation/restoration, and configuration routes. This is local verification, not hosted PostgreSQL verification.
- SQLite migration preservation test passed, including decrypting the pre-migration Fernet ciphertext after migration. PostgreSQL migration integration test skipped because `TEST_POSTGRES_URL` is unavailable; Docker's daemon is not running. No real Neon database was modified.
- `npm run build --prefix frontend`: **passed**, including TypeScript checks and Vite build.
- Playwright suite using installed Microsoft Edge: **23 passed, 1 skipped**. The skipped direct-upload test then passed separately with `VITE_DIRECT_REPORT_UPLOADS=true`. The subsequently added multi-configuration activation/removal browser test also passed separately. Browser API responses were intercepted synthetic fixtures.
- `git diff --check`: passed.

Production remains the inspected pre-fix deployment. Its current import failure is confirmed by Vercel logs, not resolved by these local changes. Production startup with PostgreSQL, real storage access, custom endpoint TLS connections, live model entitlements, and live provider generation remain unverified. No paid provider tests were run.
