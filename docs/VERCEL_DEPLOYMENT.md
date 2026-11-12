# Deploy ClinicalAI to Vercel

Use one Vercel project connected to `AbdulRehman-CUI/ClinicalAI` with the **Services** framework preset (Beta) and the repository root as its Root Directory. The root `vercel.json` builds Vite and FastAPI as separate services on one HTTPS origin. The backend uses Neon PostgreSQL and a private Amazon S3 bucket. Keep previews on a separate database or Neon branch, bucket, and credentials. [Vercel Services](https://vercel.com/docs/services)

## Prepare the private workspace

ClinicalAI opens without accounts. Each browser receives an isolated workspace. The browser loads the frontend and sends credentialed API requests on the same origin. FastAPI issues a host-only Secure, HttpOnly, SameSite=Lax cookie. If you use the standalone project configurations, use same-site HTTPS custom domains or an HTTPS reverse proxy that passes through cookies and `Set-Cookie`. [Cookie attributes](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Set-Cookie)

Apply edge rate limits to workspace creation and report signing. The app enforces a separate database-backed limit for outbound provider calls per workspace. Apply any network access controls required by your organization's clinical-data policy. [Vercel WAF access controls](https://vercel.com/kb/guide/supporting-compliance-with-vercel-waf)

Use synthetic records until the organization approves the hosting, storage, database, and selected AI provider for the intended data, including access, retention, and contractual requirements. Analysis sends the configured provider clinical context, which can include report text.

## Set up Neon and run migrations

1. In the Neon console, create or select the database and roles. Copy the **pooled** connection URL for the Vercel backend's `DATABASE_URL`. The hostname contains `-pooler`. Use a separate role with schema change permissions for the **direct** URL used by the migration operator. Keep the migration credentials out of Vercel if migrations run from a workstation or CI.
2. Keep the TLS parameters from Neon. PostgreSQL URL schemes `postgres://` and `postgresql://` select psycopg 3 and default to `sslmode=require`. Use `sslmode=verify-full` with a trusted root CA when available. With a compatible libpq and system trust store, set `sslrootcert=system`. Preserve percent-encoding in credentials. Runtime uses Neon's pool with SQLAlchemy `NullPool` and disables client-side prepared statements. [Neon pooling guidance](https://neon.com/blog/inside-lubots-database-per-tenant-architecture)
3. From the checkout root, install the backend dependencies and apply the migration once per database before serving traffic. Set the URLs in the operator shell or inject them from your secret manager. Use `current` to confirm the database reached the repository's head.

```bash
python -m pip install -r backend/requirements.txt
export DATABASE_URL='postgresql://RUNTIME_ROLE:URL_ENCODED_PASSWORD@POOLED_NEON_HOST/DB?sslmode=require'
export DIRECT_DATABASE_URL='postgresql://MIGRATION_ROLE:URL_ENCODED_PASSWORD@DIRECT_NEON_HOST/DB?sslmode=require'
python -m alembic -c backend/alembic.ini upgrade head
python -m alembic -c backend/alembic.ini current
```

In PowerShell, set the URLs with `$env:DATABASE_URL = '...'` and `$env:DIRECT_DATABASE_URL = '...'` before running the same Python commands. To review PostgreSQL DDL offline, run `python -m alembic -c backend/alembic.ini upgrade head --sql`. Run migrations before deploying code that depends on them. Hosted imports and requests perform no schema changes.

Alembic creates or upgrades the schema. Back up existing data and test the upgrade on a database copy. Legacy patients have no verified workspace ownership and remain outside guest access. Preserve their records and report objects. Follow the [retention and legacy migration guidance](GUEST_WORKSPACES.md) for any approved assignment of records to a workspace. For SQLite moves, verify row counts, generated ID sequences, and object integrity separately.

## Set up private S3 storage

1. Create a dedicated private Amazon S3 bucket in an approved region. Enable Block Public Access, bucket-owner-enforced object ownership, default encryption, and HTTPS-only access. Use a restricted service identity with `s3:PutObject`, `s3:GetObject` and `s3:DeleteObject` for the `pending-reports/*` and `reports/*` object ARNs. Grant any encryption key permissions required by your bucket policy. If you enable versioning, apply your retention and deletion policy to noncurrent object versions as well. [S3 Block Public Access](https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-control-block-public-access.html)
2. Apply a lifecycle rule to expire objects under **`pending-reports/`** after one day. This clears abandoned uploads and staged objects left after transient cleanup failures. Configure separate retention for finalized objects under `reports/`. [S3 lifecycle rules](https://docs.aws.amazon.com/AmazonS3/latest/userguide/intro-lifecycle-rules.html)
3. In the bucket's Permissions tab, set CORS for the frontend origin. Include any approved preview origins and the origins of browser clients that access the signed download. Replace the example hostname.

```json
[
  {
    "AllowedOrigins": ["https://YOUR-FRONTEND-DOMAIN"],
    "AllowedMethods": ["POST", "GET"],
    "AllowedHeaders": ["content-type"],
    "MaxAgeSeconds": 300
  }
]
```

The frontend requests an upload intent with its workspace cookie at `POST /api/v1/patients/{patient_id}/reports/upload-intent`. It POSTs the file directly to S3 using a 10-minute policy restricted to the workspace's staging key, declared MIME type, and exact byte length. Completion at `POST /api/v1/patients/{patient_id}/reports/complete` must use the same workspace, patient, and intent. The backend validates the file and writes it to `reports/<workspace_id>/<stored_filename>`. Completion can be retried for up to 30 minutes. The direct flow supports 20 MiB by default. The multipart route is subject to Vercel's 4.5 MB request limit, including overhead. [Vercel payload limits](https://vercel.com/docs/functions/limitations) · [S3 presigned POST conditions](https://docs.aws.amazon.com/botocore/latest/reference/services/s3/client/generate_presigned_post.html)

A workspace-scoped `GET /api/v1/patients/reports/{report_id}/download` responds with a 60-second private signed redirect on S3 and a file attachment locally. Treat the signed URL as a short-lived credential. In production, report JSON includes an `extracted_text` preview of up to 4 KiB. Full extracted text stays in PostgreSQL for analysis.

Report deletion commits a durable storage cleanup record before removing the object. If cleanup fails, retry the DELETE or drain the queue from the backend directory with the same runtime database and storage settings.

```bash
cd backend
python -m app.services.medical_report
```

An interrupted upload with an uncertain database commit may leave an unreferenced finalized object. Reconcile finalized keys against report filenames and their patients' workspace IDs, and against queued deletions with their workspace IDs. Preserve legacy keys without a workspace prefix according to the archive policy. Treat inventory and backups as sensitive.

## Configure the Services project

In Vercel, use the repository root and the **Services** framework preset. Enable automatic exposure of Vercel system environment variables. The backend service uses `backend/requirements.txt`, Python 3.12, the existing `app.main:app` entrypoint, and a 300-second function duration. Public routing sends `/api/*`, `/docs`, `/redoc`, and `/openapi.json` to FastAPI. The frontend serves `dist` and handles direct navigation to `/settings/llm` and `/status`. [Vercel Services routing](https://vercel.com/docs/services/routing)

Set these values in the intended Vercel environment. Generate `WORKSPACE_SIGNING_SECRET` with `python -c "import secrets; print(secrets.token_urlsafe(48))"`. Generate `LLM_ENCRYPTION_KEY` with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`. Put both values directly in the secret manager.

| Variable | Value |
| --- | --- |
| `ENVIRONMENT` | `production` for hosted production and previews |
| `DEBUG` | `false` |
| `DATABASE_URL` | Pooled Neon PostgreSQL URL with TLS |
| `DIRECT_DATABASE_URL` | Direct Neon URL for the migration operator only |
| `WORKSPACE_SIGNING_SECRET` | Generated secret of at least 32 bytes for workspace-bound report upload intents |
| `LLM_ENCRYPTION_KEY` | Generated Fernet key for encrypting each workspace's provider credential |
| `FRONTEND_URL` | `https://YOUR-FRONTEND-DOMAIN` |
| `ALLOWED_CORS_ORIGINS` | Optional additional exact HTTPS origins as a comma-separated list or JSON array |
| `STORAGE_PROVIDER` | `s3` |
| `STORAGE_BUCKET`, `STORAGE_REGION` | Private bucket name and its AWS region |
| `STORAGE_ACCESS_KEY_ID`, `STORAGE_SECRET_ACCESS_KEY` | Restricted storage credentials |
| `STORAGE_ENDPOINT` | Leave unset for AWS S3. For a compatible provider, set the HTTPS endpoint and verify signed POST and download behavior there. |
| `MAX_UPLOAD_SIZE_MB` | `20` |
| `OPENAI_MODELS`, `GEMINI_MODELS` | Optional CSV or JSON array of supported text-generation model IDs |
| `OPENAI_TIMEOUT` | Optional provider request timeout in seconds for either provider, defaults to `60` |
| `LOG_LEVEL` | `INFO` by default. Logs omit application payloads, provider response bodies, and credentials. |

Set `FRONTEND_URL` to the frontend's actual HTTPS origin. Additional origins require exact entries in `ALLOWED_CORS_ORIGINS`, including any approved same-site preview. Cookie-based writes require an approved Origin and `X-ClinicalAI-Request: 1`. Remove obsolete shared LLM credentials and JWT settings from deployment environments.

### Frontend build variables

```dotenv
VITE_API_BASE_URL=/api/v1
VITE_DIRECT_REPORT_UPLOADS=true
```

Vite includes these values in the browser bundle. Set `VITE_API_BASE_URL=/api/v1` or leave it unset to use the same-origin default. Use `VITE_DIRECT_REPORT_UPLOADS=true` for hosted storage. Leave direct uploads off for native development and Docker with local storage.

## Deploy or redeploy after approval

Use the dashboard to import or update the project, then deploy both services together. For manual CLI deployment, work from a clean checkout at the repository root and link to the intended Services project. The Vercel ignore files exclude local environment files and report data from CLI uploads.

```bash
npx vercel@latest link
npx vercel@latest deploy --prod
```

Use **Deployments → Redeploy** after changing runtime or build-time environment variables. Check `GET /api/v1/health` and `GET /api/v1/llm/providers` before testing the workspace flow. Both return JSON without creating a workspace or using a provider key. If they return `FUNCTION_INVOCATION_FAILED`, check the FastAPI runtime logs for the first import or startup error. Compare the required variable names above against the selected deployment environment. `FRONTEND_URL` must match the browser origin for workspace writes. Then verify that `POST /api/v1/workspace` returns 204 and the following configuration request includes the cookie.

## Verify with synthetic records

- Check `/api/v1/health`, `/docs`, `/redoc`, and `/openapi.json` on the backend. Health verifies that the app is serving. Login and patient CRUD verify database connectivity.
- Open and refresh `/`, `/settings/llm`, and `/status` on the frontend. Verify that the API sets a secure workspace cookie and that refresh resumes the same workspace. Open a separate browser profile and verify that it cannot read the first profile's patient IDs or LLM status.
- Create, read, edit, and delete a synthetic patient. Before deleting the patient, exercise medical history, medication, allergy, and symptom operations.
- Upload synthetic PDF, DOCX, and TXT reports. Include one between 5 MB and 20 MiB. Verify the browser sends bytes to S3, the backend returns report metadata, and the original is downloadable only through the authorized flow. Try an unsupported file, an oversized file, and another account's upload intent. Delete the reports and confirm object cleanup.
- Confirm analysis requires LLM configuration. Enter a dedicated test key, test and save the model, and run a synthetic analysis. Verify persistence, provider failures, and configuration removal. Provider tests may incur charges.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Backend build fails or cannot find the app | Verify the Root Directory, FastAPI preset, Python version, and dependency installation in the build logs. |
| Startup returns HTTP 500 | Check required environment values, TLS, CORS origins, and production settings. Keep runtime log extracts free of sensitive data. |
| Clinical routes fail while health works | Verify the pooled host, database role permissions, and migration head. Connection failures return HTTP 503. |
| Workspace setup fails or refresh loses access | Check same-site HTTPS domains, the deployed `VITE_API_BASE_URL`, cookie flags, backend CORS allow-list, and Vite rewrite configuration. Redeploy after build-time changes. |
| A report fails with HTTP 413 | Verify `VITE_DIRECT_REPORT_UPLOADS=true` in the built frontend. Large files must use the direct transfer. |
| Storage POST returns 403 | Verify the bucket region, IAM permissions, endpoint, policy lifetime, file size, signed content type, and S3 CORS. Keep form fields and signed URLs out of tickets and logs. |
| Analysis returns HTTP 503 or 504 | Check credentials, model access, provider availability, configured timeout, and the function duration. The analysis request runs synchronously and saves results after validation. If observed execution regularly reaches the budget, move it to a durable queue and an external worker before raising the client timeout. |

## Local verification commands

```bash
python -m pytest
npm --prefix frontend run build
npm --prefix frontend test
```

Set `TEST_POSTGRES_URL` to an empty disposable PostgreSQL database to include the live database test. That test runs migrations and writes synthetic rows. To test the direct upload in Playwright, set `VITE_DIRECT_REPORT_UPLOADS=true` and run `npm --prefix frontend test -- --grep "direct report upload"`. The browser and backend tests stub external storage and AI calls.
