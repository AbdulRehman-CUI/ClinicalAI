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

## Pre-deployment verification and cutover plan — 21 November 2026

This section supersedes the earlier verification blockers where explicitly stated. The deployed application and production database were not modified. The source under review is commit `9445b0d` plus the new PostgreSQL verification tests and this report update.

### Dependency provenance

The project uses pip and `backend/requirements.txt`; there is no Python dependency lockfile. That production file already declares `psycopg[binary]>=3.2,<4.0` and `boto3>=1.40,<2.0`. The root `vercel.json` selects service `backend` with root `backend`, framework FastAPI and entrypoint `app.main:app`; `backend/.python-version` selects Python 3.12. Neither Vercel ignore file excludes requirements.txt. The root pyproject.toml contains pytest configuration, not an alternative dependency declaration. Vercel supports requirements.txt for Python runtime dependencies: [official runtime documentation](https://vercel.com/docs/functions/runtimes/python).

For verification, pip accepted the complete requirements file in the existing local Python 3.12.16 Linux image, with psycopg/psycopg-binary 3.3.8 and boto3 1.44.1 already installed. This matches the deployment Python major/minor and avoids confusing missing Windows packages with application failures. The Windows environment was then successfully installed from the same requirements file: psycopg/psycopg-binary 3.3.9 and boto3/botocore 1.44.9. `python -m pip check` reported no broken requirements. No production dependency-file changes were necessary.

### Compatibility and required order

This migration is **not compatible with simultaneous old and new backend traffic**. The old backend upserts with `ON CONFLICT (workspace_id)`, but that unique key is removed by the new schema. A PostgreSQL regression now confirms the old upsert fails after migration. Old reads also do not filter `active`, and old deletes remove all entries in a workspace. Conversely, the new backend requires the new columns and cannot serve LLM configuration routes before migration. A Vercel alias/code rollback alone is therefore unsafe after this schema change.

Use a maintenance cutover, in this order, only after separate authorization:

1. Confirm the exact release commit, test results and Vercel build inputs. Install with `python -m pip install -r backend/requirements.txt`; check imports and `python -m pip check`. Prepare the release against an isolated staging database. Do not point an old preview deployment at the migrated production database.
2. Obtain the real bucket settings and configure the backend environment variables listed above for the intended production deployment. Preserve the existing `LLM_ENCRYPTION_KEY` and `WORKSPACE_SIGNING_SECRET`. `STORAGE_BUCKET` and `STORAGE_REGION` must identify the existing private bucket; `STORAGE_ACCESS_KEY_ID` and `STORAGE_SECRET_ACCESS_KEY` must be an existing usable pair authorized for that bucket. `STORAGE_ENDPOINT` must come from the S3-compatible provider, or be omitted for standard AWS S3. Do not invent these values. Confirm bucket CORS and permissions before cutover. Set frontend `VITE_DIRECT_REPORT_UPLOADS=true` and retain same-origin `/api/v1`.
3. Block application access to **all old deployment aliases**, including previews that share production credentials. Stop background cleanup/jobs and drain in-flight requests. Do not rely only on a frontend maintenance page: old API URLs must not remain usable. Confirm there are no application writers before copying the credential table. Keep the maintenance gate closed until the new release passes checks.
4. Capture a restorable database backup at this quiescent point, plus a secure record of the exact old release, environment configuration, encryption key and Alembic revision. Record row counts and expiry values without logging credentials. Preserve the report bucket and its recovery/versioning arrangements separately; a database dump does not contain S3 report objects. Verify restore into a separate empty database before proceeding.
5. From the new checkout's `backend` directory, in a trusted process with the **direct** production TLS URL loaded into `DIRECT_DATABASE_URL`, run `python -m alembic -c alembic.ini current`, then `python -m alembic -c alembic.ini upgrade head`, then `python -m alembic -c alembic.ini current`. Expect `20261120_0001`. All required core production settings must also be loaded because Alembic imports Settings. The runtime `DATABASE_URL` may be pooled; migrations should use the direct Neon endpoint. Run once, outside request handlers and deployment build hooks.
6. Confirm schema revision, preserved row count, encrypted-key bytes, expiry/session hashes and one active entry per existing workspace. PostgreSQL executes the migration transactionally: a failed migration must leave the old revision intact. If it fails, keep maintenance enabled, inspect the schema/revision, and fix or restore; do not use `alembic stamp head` to conceal a failure.
7. Deploy/promote the new backend and frontend together using the retained Vercel Services configuration. Keep old deployments and jobs blocked from the new database. Run the checks below while public traffic remains gated. Only reopen traffic once the checks pass.

### Backup and recovery procedure

Use the PostgreSQL client tools compatible with the server major version. Load credentials through secure libpq service/password configuration, not literal secrets in commands or logs. For example, with a preconfigured `clinicalai-production-direct` service and an approved secure backup destination:

```text
pg_dump --dbname=service=clinicalai-production-direct --format=custom --file=clinicalai-pre-migration.dump
pg_restore --list clinicalai-pre-migration.dump
pg_restore --dbname=service=clinicalai-restore-check --exit-on-error --single-transaction --no-owner --no-privileges clinicalai-pre-migration.dump
```

The restore service must point to a separate empty database. Verify ownership/grants required by the application explicitly when using `--no-owner --no-privileges`; verify the old release can read restored workspaces and decrypt credentials with the retained key. A dump listing alone is not a restore test. See [pg_dump](https://www.postgresql.org/docs/current/app-pgdump.html) and [pg_restore](https://www.postgresql.org/docs/18/app-pgrestore.html).

If the release fails before traffic reopens, keep the gate closed and restore the verified pre-migration snapshot into a separate database, then configure the old release to use that restored database and its matching encryption key. Recheck it before reopening. The migration deliberately refuses downgrade because multiple configurations cannot be collapsed without data loss. If traffic has already reopened, restoring the earlier snapshot would lose subsequent patient/configuration changes: stop writes and prefer a forward fix or explicitly reconcile those changes before any restore. Never blindly roll back only the code or run a lossy schema downgrade.

### Post-deployment smoke checks

- `GET /api/v1/health` returns 200; `GET /api/v1/readiness` returns 200 with database schema current and storage configured. Readiness checks configuration, not actual bucket permissions.
- `/openapi.json` and metadata/catalog routes load without creating a workspace. Six providers appear; fallback suggestions remain labeled unverified.
- A fresh browser can create a workspace, with Secure/HttpOnly/SameSite=Lax/Path=/, `__Host-` cookie and no Domain. Refresh restores it. Disallowed Origin or missing `x-clinicalai-request: 1` is rejected. Two browsers cannot retrieve each other's patient IDs or configuration entries.
- Existing migrated remembered/session entries retain the original active provider. Correct session credentials remain usable; expired or wrong-session credentials cannot be used. No automatic provider fallback occurs after active removal/expiry.
- With synthetic content only, verify direct report upload intent, upload, completion, download and deletion in the real private bucket. Confirm no false database persistence on a failed storage operation, no public bucket access, and no workspace cookies forwarded to storage.
- Connection tests, saves and clinical generation can incur provider charges. Run them only after explicit authorization, with synthetic data and approved test keys. Verify explicit activation controls the actual provider, structured-output validation still rejects malformed output, and secrets are absent from responses/logs.
- Review Vercel backend runtime logs for import failures, schema errors and sanitized storage/provider errors. Recheck readiness after the first cold start. Confirm old deployment URLs cannot continue using the new schema.

The preceding commands are an exact future deployment/recovery sequence, not actions performed during this verification.

### Final results from this verification

- Windows: `.venv/Scripts/python.exe -m pip install -r backend/requirements.txt` completed successfully; psycopg/psycopg-binary **3.3.9**, boto3/botocore **1.44.9**. `pip check`: **no broken requirements**. These were dependency/environment failures in the earlier run, not unresolved application defects.
- Windows full backend run with both isolated PostgreSQL test URLs set: **88 passed, 0 failed, 0 skipped** in 53.45 seconds.
- Python **3.12.16 Linux** full backend run with both PostgreSQL test URLs set: **88 passed, 0 failed, 0 skipped** in 43.35 seconds. All three originally failed tests passed. Seven warnings are existing FastAPI/Starlette/Alembic deprecations; no assertions were weakened or tests suppressed.
- The first Linux attempt had two test-harness failures because `scripts/check_environment.py` was not mounted into the container. Adding the source mount resolved both without changing application code or assertions.
- Database verification used a **real PostgreSQL 17.11** server in a disposable local Docker container, with `sslmode=require`. TLS was enabled with a synthetic one-day certificate. This verifies encrypted PostgreSQL transport, not Neon's infrastructure or production certificate policy. No remote database was accessed.
- Live PostgreSQL tests upgraded `20261112_0002` containing four synthetic configurations to `20261120_0001`, preserving ciphertext byte-for-byte, Fernet decryption, expiry, session hashes, and prior active selection. Correct sessions remained usable; wrong sessions and expired credentials/workspaces were rejected at the relevant service boundary. Adding, activating, switching back, and deleting another configuration worked on the migrated database. The database rejected two simultaneous active rows. The regression also proved the old upsert is incompatible with the new schema.
- A fresh isolated PostgreSQL database upgraded to head successfully. A new process then imported and ran the real ASGI app with `ENVIRONMENT=production`, `VERCEL=1`, TLS PostgreSQL, and missing S3 credentials. Health/OpenAPI/provider metadata, guest creation/restoration, production cookie attributes, origin checks, configuration reads, patient creation and cross-browser isolation passed. Readiness returned 503 with **database ready** and the three missing storage-variable names. Both ordinary upload and direct-upload intent returned the exact sanitized storage 503; the report table remained empty.
- The existing PostgreSQL patient/report lifecycle integration test also ran rather than skipping. Provider network calls are mocked; the missing-storage tests do not call S3. The S3 policy test uses local SDK signing with synthetic credentials. The production-style test uses local FastAPI TestClient requests, not a deployed Vercel instance.
- Added `tests/backend/test_predeployment_postgres.py`; application source and production dependency declarations needed no change in this follow-up. `git diff --check` passed. The frontend was not rerun because only backend verification tests and documentation changed.

Reproduce the complete backend run with `python -m pytest tests/backend -o addopts='' -q` after installing requirements and setting `TEST_POSTGRES_URL` to an empty disposable database and `TEST_POSTGRES_ADMIN_URL` to a localhost-only disposable PostgreSQL server with database-creation permission. Use TLS URLs. The new tests create UUID-named databases and remove those databases afterward. Never set either variable to production. The existing lifecycle test consumes its supplied empty database; discard it after the run.

Remaining external release prerequisites: obtain/confirm the existing bucket and real credentials, review bucket permissions/CORS and actual Neon configuration, authorize the backup/maintenance/migration/deployment sequence, then perform the deployed smoke checks. Real S3 permissions, live provider entitlements/generation and Vercel-hosted behavior remain unverified. No paid infrastructure, push, deployment or production migration was performed. All task-created verification containers and their disposable PostgreSQL volume were removed after testing.
