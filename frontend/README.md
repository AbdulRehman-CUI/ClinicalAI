# ClinicalAI frontend

From the repository root, run `scripts/setup.ps1`, then start `scripts/start-backend.ps1` and `scripts/start-frontend.ps1` in separate PowerShell windows. For frontend-only setup, run `npm.cmd --prefix frontend ci` and `npm.cmd --prefix frontend run dev`.

Vite reads the shared root `.env`; its proxy forwards `/api` to the configured backend host and port (8000 by default). Keep `VITE_API_BASE_URL=/api/v1` to use this proxy. Only `VITE_` variables are exposed to browser code. See [Windows development](../docs/windows-development.md) for relocation recovery and full commands.

`npm run build` checks TypeScript and builds the production bundle.

## Browser regression tests

Run `npx playwright install chromium` once, then `npm test`. The test runner starts Vite automatically. Use `PLAYWRIGHT_BASE_URL` to test an existing local preview and `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` to use an already installed Chromium executable.

Tests intercept API calls with synthetic records. They verify frontend request contracts, authentication redirects, clinical forms, patient editing, reports, analysis rendering, role restrictions, error recovery, pending states, reduced motion, and layouts from 320 to 1920 pixels. They do not validate a live database, report extraction, or an AI provider.

Clinical records stay in React memory; the redesign adds no patient storage. Starting a new patient clears the workspace after confirmation, while server records remain saved. The existing app does not provide patient search or reopening saved cases. The status endpoint verifies backend responsiveness only; it cannot establish database, storage, or AI provider health.
