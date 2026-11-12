# Guest workspaces and bring your own LLM

ClinicalAI opens the dashboard immediately. Each visitor can use patients, medical history, medications, allergies, symptoms, reports, and AI analysis in their own workspace. Use **Open a saved patient** to resume a record in the same browser.

## Workspace privacy and expiry

The server issues a random 256-bit bearer capability and stores its SHA-256 digest in the database. The browser keeps the capability in a host-only, HttpOnly cookie with SameSite=Lax and the Secure flag in production. The workspace ID scopes database queries and S3 object paths. Access requires the cookie. Clinical records inherit ownership from their patient, and a visitor who requests another workspace’s record receives HTTP 404. State changes require an approved Origin and the `X-ClinicalAI-Request` header.

A workspace credential lasts 30 days. A returning visitor can reopen their workspace while that cookie remains valid. Clearing cookies, changing browsers, or letting the credential expire can make the old workspace inaccessible. A browser profile with a valid cookie has access to that workspace, including on a shared computer. This capability provides browser continuity without verifying a person's identity. Use synthetic records until your organization has approved the data handling and access controls for its intended use.

## Configure analysis

1. Open **Configure LLM** on the dashboard or **LLM settings** in navigation.
2. Select OpenAI or Google Gemini and select a supported model. The server exposes a configurable registry. Provider access depends on the supplied key and account. Use **Test connection** to make a short model request without clinical data.
3. Enter your key and choose **Save configuration**. Saving also validates the selected model with the provider. Leave the key blank when changing models with the same provider to reuse an active saved key.
4. Choose **Remove configuration** to remove the workspace’s saved credential. Replace a key by entering the new key and saving again.

The default registry includes `gpt-4.1-mini` and `gpt-4o-mini` for OpenAI, and `gemini-3.6-flash` and `gemini-3.5-flash-lite` for Gemini. Configure `OPENAI_MODELS` or `GEMINI_MODELS` as a CSV list or JSON array to update the registry. [OpenAI model catalog](https://developers.openai.com/api/docs/models) · [Gemini model catalog](https://ai.google.dev/gemini-api/docs/models)

Session configuration uses a separate HttpOnly browser-session cookie and an eight-hour server expiry. A browser that restores its session can restore the session cookie within that window. Selecting **Remember** extends configuration access for up to seven days within the same workspace. The database stores authenticated Fernet ciphertext bound to the workspace, provider, and model. Keep `LLM_ENCRYPTION_KEY` in a backend secret manager. Rotating this key requires visitors to save their keys again. GET endpoints return only configuration status and metadata. ClinicalAI initializes a separate provider client for each test or analysis request. The workspace limit is eight provider attempts per minute, including tests, saves, and analysis.

Your provider bills your account according to its prices, quotas, and account settings. Tests and saves can incur a small provider charge. ClinicalAI does not control provider spending limits. Analysis sends the existing patient context and relevant report text to the chosen provider. Check the provider's data use, retention, and contractual terms before sending clinical information.

## API

| Method and path under `/api/v1` | Behavior |
| --- | --- |
| `POST /workspace` | Initialize a browser workspace or resume the valid cookie. |
| `GET /llm/providers` | List the supported provider and model IDs. |
| `GET /llm/config` | Read readiness, provider, model, saved-key indicator, and expiry. |
| `PUT /llm/config` | Test and save `provider`, `model`, optional replacement `api_key`, and `remember`. |
| `DELETE /llm/config` | Remove the active workspace's saved credential. |
| `POST /llm/test` | Test a supplied key or the same provider's active saved key. |

Clinical calls and workspace-specific LLM calls require the issued workspace cookie. Write calls also send the frontend Origin and `X-ClinicalAI-Request: 1`. A missing or expired workspace returns HTTP 401. Reload the browser to start a new workspace. A provider or credential error includes a safe `error` code, such as `llm_not_configured`, `llm_invalid_key`, `llm_quota`, `llm_rate_limited`, `llm_timeout`, or `llm_network`.

## Operator retention and migration

The Alembic upgrade preserves legacy patients, reports, analyses, and users. Legacy patients have a null workspace because earlier records were shared and have no trustworthy visitor owner. Guest routes cannot list or retrieve them. Keep legacy data in restricted backups or an approved archive. If verified records must move to a guest workspace, have an authorized operator review the exact patient IDs and ownership evidence, copy matching report objects into that workspace's storage prefix, then assign only those patient rows in a reviewed database transaction. Check counts and object integrity before releasing access.

Workspace expiry stops browser access and leaves clinical data available for controlled retention and backup. Apply the organization's retention policy to expired workspaces. If approved to purge, identify expired workspace IDs, inventory their patient records and report objects, remove database child records and report objects under the same controlled cleanup procedure, then remove the workspace. Exclude unassigned legacy records and legal holds. Use a dry run and verified backup before destructive maintenance.

Run these commands from the backend directory with the appropriate database and storage settings. Schedule credential cleanup in your approved operations environment. The second command retries queued report object deletion.

```bash
python -m app.services.llm
python -m app.services.medical_report
```
