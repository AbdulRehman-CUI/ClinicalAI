# Authentication failure investigation

The reproduced failure was in `GET /api/v1/auth/users/me`. Registration and login issued valid JWTs, then the frontend loaded this endpoint. `AuthService.get_current_user` converted the database row to `AuthUser`, discarding `created_at` and `updated_at`. The route converted that object to `UserRead`, where both fields are required, producing a Pydantic `ValidationError` and HTTP 500. `AuthUser` now inherits the complete safe profile schema.

The local `LOG_FORMAT=json` also prevented a new backend process from starting: Python's percent-style logging formatter rejected the literal `json`. This mode now uses a standard-library JSON formatter. Existing percent-style formats continue to work.

The configured SQLite database was inspected read-only. It passed `PRAGMA quick_check`, contained all required users columns, and was already at migration `20260803_0001`. Three bcrypt `$2b$` accounts were present. No schema migration, account update, password rehash, database reset, or database replacement was necessary. Installed bcrypt 4.3.0 and PyJWT 2.13.0 completed hashing and token checks successfully.

Expected failures now return 401 for incorrect credentials and invalid/expired tokens, 403 for disabled-account login, and 409 for duplicate registration, including a duplicate insert race. Token subjects are validated before database lookups. New passwords cannot silently exceed bcrypt's 72-byte limit; login preserves the truncation behavior of existing bcrypt hashes. Validation logging excludes submitted values.

The frontend authenticates only after a successful server profile response. Cached profiles and decoded JWT claims cannot establish a session. Expired sessions can refresh and then validate the profile; authenticated API requests retry once after renewal. Unexpected server errors show a safe message instead of raw server details.

## Verification commands

Executed verification: 31 focused backend tests passed; 20 frontend browser tests passed against the production build; TypeScript/Vite production build passed. A real browser also completed registration, incorrect-password rejection, logout/re-login, session restoration, profile retrieval, refresh, duplicate rejection, and invalid-token rejection through the Vite proxy against an isolated FastAPI database. All three original database profiles validated through read-only connections, and the original database's SHA-256 fingerprint remained identical before and after verification. No live AI-provider call was made.

From the repository root:

```powershell
# Uses a separate test database. Never point destructive test fixtures at live data.
$env:DATABASE_URL = 'sqlite:///D:/ClinicalAI/backend/data/auth-diagnostic-test.db'
.\.venv\Scripts\python.exe -m pytest tests/backend/test_auth.py tests/backend/test_auth_regressions.py tests/backend/test_health.py tests/backend/test_api_endpoints.py tests/backend/test_analysis_workflow.py tests/backend/test_alembic_migrations.py
Remove-Item Env:DATABASE_URL

npm --prefix frontend run build
cd frontend
npx playwright install chromium
npm test
```

Existing-account bcrypt tests use known pre-existing hashes in isolated databases. The passwords for the three real local accounts were not provided, so successful password login to those particular accounts must be checked interactively. With the real backend running, this command prompts securely, checks login/profile/refresh/logout, and never prints tokens or passwords:

```powershell
.\.venv\Scripts\python.exe scripts/verify_auth.py
```

The Alembic configuration now resolves migration paths relative to its own location. The migration regression test uses a temporary database rather than the application's configured database. No migration needs to be applied to fix this profile-serialization error. Restart the backend to load the changes.
