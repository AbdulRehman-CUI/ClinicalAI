import { expect, test, type Page, type Route } from "@playwright/test";

// Synthetic records are confined to intercepted test requests. No real service is called.
const patient = {
  id: 12,
  first_name: "Test",
  last_name: "Patient",
  age: 35,
  biological_sex: "Female",
  blood_group: "Unknown",
  height_cm: 165,
  weight_kg: 60,
  pregnancy_status: "Unknown",
  created_at: "2026-01-01",
  updated_at: "2026-01-01",
};
const result = {
  analysis_id: 7,
  patient_id: 12,
  possible_diagnoses: [
    {
      condition: "Test finding",
      confidence: "Low",
      reasoning: "Synthetic response for rendering verification",
    },
  ],
  critical_alerts: ["Test critical alert"],
  medication_warnings: [
    { medication: "Test medicine", warning: "Review required" },
  ],
  recommended_tests: ["Test investigation"],
  recommended_specialist: "Test specialist",
  summary: "Synthetic clinical review for frontend testing only.",
};
const ok = (route: Route, data: unknown) =>
  route.fulfill({ json: { success: true, message: "", data } });

async function api(page: Page, configured = true) {
  let llm = { configured, provider: "openai", model: "gpt-4.1-mini", has_api_key: configured, tested: configured, remember: false };
  let savedPatient: typeof patient | null = null;
  const requests: { path: string; method: string; body: unknown }[] = [];
  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname.replace("/api/v1", "");
    if (path.endsWith("/reports") && request.method() === "POST") {
      requests.push({
        path,
        method: request.method(),
        body: request.postData(),
      });
      return ok(route, {
        id: 20,
        patient_id: 12,
        original_filename: "test-report.txt",
        file_type: "TXT",
        upload_timestamp: "2026-01-01T10:00:00Z",
      });
    }
    const body = request.postData() ? request.postDataJSON() : null;
    requests.push({ path, method: request.method(), body });
    if (path === "/workspace") return route.fulfill({ status: 204 });
    if (path === "/llm/providers") return ok(route, { openai: ["gpt-4.1-mini", "gpt-4o-mini"], gemini: ["gemini-3.6-flash"] });
    if (path === "/llm/config") {
      if (request.method() === "DELETE") {
        llm = { ...llm, configured: false, has_api_key: false, tested: false };
        return route.fulfill({ status: 204 });
      }
      if (request.method() === "PUT") llm = {
        configured: true, provider: body.provider, model: body.model, has_api_key: true,
        tested: true, remember: body.remember,
      };
      return ok(route, llm);
    }
    if (path === "/llm/test") return ok(route, { tested: true });
    if (path === "/patients") {
      if (request.method() === "GET") return ok(route, savedPatient ? [savedPatient] : []);
      savedPatient = { ...patient, ...body };
      return ok(route, savedPatient);
    }
    if (path === "/patients/12" && request.method() === "PUT")
      return ok(route, { ...patient, ...body });
    if (path === "/patients/12/analyze") return ok(route, result);
    if (path === "/health") return ok(route, { status: "ok" });
    if (request.method() === "POST")
      return ok(route, { id: requests.length, patient_id: 12, ...body });
    return ok(route, []);
  });
  return requests;
}

async function createPatient(page: Page) {
  const form = page.getByRole("form", { name: "Patient profile" });
  await form.getByLabel(/^First name/).fill("Test");
  await form.getByLabel(/^Last name/).fill("Patient");
  await form.getByLabel(/^Age/).fill("35");
  await form.getByLabel(/^Biological sex/).selectOption("Female");
  await form.getByLabel(/^Blood group/).selectOption("Unknown");
  await form.getByLabel(/^Height/).fill("165");
  await form.getByLabel(/^Weight/).fill("60");
  await form.getByRole("button", { name: "Create patient" }).click();
  await expect(
    page.getByRole("form", { name: "Symptoms", exact: true }),
  ).toBeVisible();
}

async function addSymptom(page: Page) {
  const form = page.getByRole("form", { name: "Symptoms", exact: true });
  await form.getByLabel(/^Symptom/).fill("Test symptom");
  await form.getByLabel(/^Duration/).fill("2 days");
  await form.getByLabel(/^Severity/).fill("Mild");
  await form.getByRole("button", { name: "Add symptom" }).click();
  await expect(form.locator("input").first()).toHaveValue("");
}

test("dashboard and status open without a registered account", async ({ page }) => {
  const requests = await api(page, false);
  await page.goto("/");
  await expect(page.getByRole("form", { name: "Patient profile" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Configure LLM" })).toBeVisible();
  await expect(page.getByText("LLM Not Configured")).toBeVisible();
  expect(requests.filter((r) => r.path === "/workspace")).toHaveLength(1);
  expect(requests.some((r) => r.path.startsWith("/auth/"))).toBe(false);
  await page.goto("/status");
  await page.reload();
  await expect(page).toHaveURL(/\/status$/);
  await page.goto("/login");
  await expect(page.getByRole("form", { name: "Patient profile" })).toBeVisible();
});

test("guest can test, save, replace and remove their LLM settings", async ({ page }) => {
  const requests = await api(page, false);
  await page.goto("/");
  await page.getByRole("link", { name: "Configure LLM" }).click();
  await expect(page).toHaveURL(/\/settings\/llm$/);
  await page.getByLabel(/^Provider/).selectOption("gemini");
  await page.getByLabel(/^Model/).selectOption("gemini-3.6-flash");
  const key = page.getByLabel(/^API key/);
  await key.fill("synthetic-gemini-key");
  await expect(key).toHaveAttribute("type", "password");
  await page.getByRole("button", { name: "Show key" }).click();
  await expect(key).toHaveAttribute("type", "text");
  await page.getByRole("button", { name: "Test connection" }).click();
  await expect(page.getByRole("status")).toContainText("Connection tested");
  await page.getByRole("button", { name: "Save configuration" }).click();
  await expect(page.getByRole("status")).toContainText("configuration saved");
  await expect(key).toHaveValue("");
  await page.reload();
  await expect(page.getByText("LLM Configured", { exact: true })).toBeVisible();
  await expect(key).toHaveValue("");
  await key.fill("synthetic-replacement-key");
  await page.getByLabel(/Remember this encrypted key/).check();
  await page.getByRole("button", { name: "Save configuration" }).click();
  await expect(page.getByRole("status")).toContainText("configuration saved");
  const put = requests.filter((r) => r.path === "/llm/config" && r.method === "PUT");
  expect(put.at(-1)?.body).toEqual({
    provider: "gemini", model: "gemini-3.6-flash", api_key: "synthetic-replacement-key", remember: true,
  });
  await page.getByRole("link", { name: "Patient workspace" }).click();
  await expect(page.getByRole("link", { name: "Manage LLM" })).toBeVisible();
  await page.getByRole("link", { name: "Manage LLM" }).click();
  await page.getByRole("button", { name: "Remove configuration" }).click();
  await expect(page.getByRole("status")).toContainText("configuration removed");
});

test("patient validation, every clinical form, profile editing, analysis objects and reset", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  const requests = await api(page);
  await page.goto("/");
  await expect(page.getByLabel(/^First name/)).toHaveValue("");
  await page
    .getByRole("button", { name: "Create patient", exact: true })
    .click();
  expect(requests.filter((r) => r.path === "/patients" && r.method === "POST")).toHaveLength(0);
  await createPatient(page);
  const history = page.getByRole("form", {
    name: "Medical history",
    exact: true,
  });
  await history.getByLabel(/^Condition/).fill("Test condition");
  await history.getByLabel(/^Clinical notes/).fill("Test clinical notes");
  await history.getByRole("button", { name: "Add history" }).click();
  const allergy = page.getByRole("form", { name: "Allergies", exact: true });
  await allergy.getByLabel(/^Allergen/).fill("Test allergen");
  await allergy.getByLabel(/^Reaction/).fill("Test reaction");
  await allergy.getByLabel(/^Severity/).fill("Mild");
  await allergy.getByRole("button", { name: "Add allergy" }).click();
  const medication = page.getByRole("form", {
    name: "Medications",
    exact: true,
  });
  await medication.getByLabel(/^Medication/).fill("Test medicine");
  await medication.getByLabel(/^Dosage/).fill("Test dose");
  await medication.getByLabel(/^Frequency/).fill("Daily");
  await medication.getByLabel(/^Start date/).fill("2026-01-01");
  await medication.getByRole("button", { name: "Add medication" }).click();
  await addSymptom(page);
  for (const path of [
    "medical-history",
    "allergies",
    "medications",
    "symptoms",
  ])
    expect(
      requests.some(
        (r) => r.path === `/patients/12/${path}` && r.method === "POST",
      ),
    ).toBeTruthy();
  await page.getByRole("button", { name: /04 AI analysis/ }).click();
  await page.getByRole("button", { name: "Run clinical analysis" }).click();
  await expect(page.getByText("Test finding", { exact: true })).toBeVisible();
  await expect(
    page.getByText("Review required", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Test critical alert", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: /01 Patient profile/ }).click();
  await page.getByRole("button", { name: "Edit patient details" }).click();
  await page.getByLabel(/^Weight/).fill("62");
  await page.getByRole("button", { name: "Save patient details" }).click();
  expect(requests.find((r) => r.method === "PUT")?.body).toMatchObject({
    weight_kg: 62,
  });
  await page.getByRole("button", { name: /04 AI analysis/ }).click();
  await expect(
    page.getByText("Context changed", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "New patient", exact: true }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await dialog.getByRole("button", { name: "Keep working" }).click();
  await expect(dialog).not.toBeVisible();
  await page.getByRole("button", { name: "New patient", exact: true }).click();
  await dialog
    .getByRole("button", { name: "Start new patient", exact: true })
    .click();
  await expect(page.getByLabel(/^First name/)).toHaveValue("");
  expect(errors).toEqual([]);
});

test("direct report upload keeps workspace credentials off the storage request", async ({ page }) => {
  test.skip(process.env.VITE_DIRECT_REPORT_UPLOADS !== "true", "requires the hosted upload setting");
  await api(page);
  const storageURL = "https://storage.example.test/upload";
  const file = Buffer.alloc(5 * 1024 * 1024, "x");
  const steps: string[] = [];

  await page.route("**/reports/upload-intent", async (route) => {
    const request = route.request();
    expect(request.headers()["x-clinicalai-request"]).toBe("1");
    expect(request.postDataJSON()).toEqual({ filename: "direct.txt", size: file.length });
    steps.push("authorize");
    return ok(route, { token: "upload-intent", url: storageURL, fields: { key: "pending-reports/opaque.txt" } });
  });
  await page.route(storageURL, async (route) => {
    const request = route.request();
    const headers = { "access-control-allow-origin": "*" };
    if (request.method() === "OPTIONS") {
      return route.fulfill({ status: 204, headers: { ...headers, "access-control-allow-methods": "POST" } });
    }
    expect(request.method()).toBe("POST");
    expect(request.headers().authorization).toBeUndefined();
    expect(request.headers()["x-clinicalai-request"]).toBeUndefined();
    expect(request.headers().cookie).toBeUndefined();
    expect(request.postDataBuffer()!.length).toBeGreaterThan(file.length);
    expect(request.postData()!.slice(0, 512)).toContain("pending-reports/opaque.txt");
    steps.push("upload");
    return route.fulfill({ status: 204, headers });
  });
  await page.route("**/reports/complete", async (route) => {
    const request = route.request();
    expect(request.headers()["x-clinicalai-request"]).toBe("1");
    expect(request.postDataJSON()).toEqual({ token: "upload-intent" });
    steps.push("complete");
    return ok(route, {
      id: 21, patient_id: 12, original_filename: "direct.txt", file_type: "TXT",
      upload_timestamp: "2026-01-01T10:00:00Z",
    });
  });

  await page.goto("/");
  await createPatient(page);
  await page.getByRole("button", { name: /03 Medical reports/ }).click();
  await page.getByLabel("Choose medical report").setInputFiles({
    name: "direct.txt", mimeType: "text/plain", buffer: file,
  });
  await page.getByRole("button", { name: "Upload report", exact: true }).click();
  await expect(page.locator(".document-card")).toContainText("direct.txt");
  expect(steps).toEqual(["authorize", "upload", "complete"]);
});

test("report keyboard selection, removal, upload, and report-only analysis readiness", async ({
  page,
}) => {
  const requests = await api(page);
  await page.goto("/");
  await createPatient(page);
  await page.getByRole("button", { name: /03 Medical reports/ }).click();
  const file = page.getByLabel("Choose medical report");
  await file.setInputFiles({
    name: "invalid.exe",
    mimeType: "application/octet-stream",
    buffer: Buffer.from("test"),
  });
  await expect(page.getByRole("alert")).toContainText("Unsupported file type");
  await file.setInputFiles({
    name: "test-report.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("Synthetic report for frontend tests only"),
  });
  await expect(
    page.getByText("test-report.txt", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Remove selected file" }).click();
  await expect(
    page.getByText("test-report.txt", { exact: true }),
  ).not.toBeVisible();
  await file.setInputFiles({
    name: "test-report.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("Synthetic report for frontend tests only"),
  });
  await page
    .getByRole("button", { name: "Upload report", exact: true })
    .click();
  await expect(page.locator(".document-card")).toContainText("test-report.txt");
  expect(requests.find((r) => r.path.endsWith("/reports"))?.body).toContain(
    'filename="test-report.txt"',
  );
  await page.getByRole("button", { name: /04 AI analysis/ }).click();
  await expect(
    page.getByRole("button", { name: "Run clinical analysis" }),
  ).toBeEnabled();
});

test("analysis stays disabled until a visitor configures an LLM", async ({ page }) => {
  const requests = await api(page, false);
  await page.goto("/");
  await createPatient(page);
  await addSymptom(page);
  await page.getByRole("button", { name: /04 AI analysis/ }).click();
  await expect(page.getByRole("button", { name: "Run clinical analysis" })).toBeDisabled();
  await page.getByRole("link", { name: "Configure an LLM" }).click();
  await expect(page).toHaveURL(/\/settings\/llm$/);
  expect(requests.some((r) => r.path.endsWith("/analyze"))).toBe(false);
});

test("a returning visitor can open a saved patient after refresh", async ({ page }) => {
  await api(page);
  await page.goto("/");
  await createPatient(page);
  await page.reload();
  await page.getByLabel(/Open a saved patient/).selectOption("12");
  await expect(page.getByRole("form", { name: "Symptoms", exact: true })).toBeVisible();
});

test("analysis pending, failure, and retry preserve honest result states", async ({
  page,
}) => {
  await api(page);
  await page.goto("/");
  await createPatient(page);
  await addSymptom(page);
  let release: () => void = () => {};
  const held = new Promise<void>((resolve) => {
    release = resolve;
  });
  let attempts = 0;
  await page.route("**/api/v1/patients/12/analyze", async (route) => {
    attempts++;
    if (attempts === 1) {
      await held;
      return route.fulfill({
        status: 503,
        json: { message: "Test provider unavailable" },
      });
    }
    return ok(route, result);
  });
  await page.getByRole("button", { name: /04 AI analysis/ }).click();
  await page.getByRole("button", { name: "Run clinical analysis" }).click();
  await expect(
    page.getByRole("button", { name: "Analysis in progress…" }),
  ).toBeDisabled();
  await expect(
    page.getByText("Reviewing clinical information", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Response received", { exact: true }),
  ).not.toBeVisible();
  release();
  await expect(page.getByRole("alert").first()).toBeVisible();
  await page.getByRole("button", { name: "Run clinical analysis" }).click();
  await expect(page.getByText("Test finding", { exact: true })).toBeVisible();
});

test("report drag and drop retains a failed selection for retry", async ({
  page,
}) => {
  await api(page);
  await page.goto("/");
  await createPatient(page);
  await page.getByRole("button", { name: /03 Medical reports/ }).click();
  await page.locator(".upload-zone").evaluate((element) => {
    const transfer = new DataTransfer();
    transfer.items.add(
      new File(["Synthetic test report"], "test-report.txt", {
        type: "text/plain",
      }),
    );
    element.dispatchEvent(
      new DragEvent("drop", {
        bubbles: true,
        cancelable: true,
        dataTransfer: transfer,
      }),
    );
  });
  await expect(page.locator(".selected-file")).toContainText("test-report.txt");
  let attempts = 0;
  await page.route("**/api/v1/patients/12/reports", (route) =>
    ++attempts === 1
      ? route.fulfill({
          status: 503,
          json: { message: "Test storage unavailable" },
        })
      : ok(route, {
          id: 20,
          patient_id: 12,
          original_filename: "test-report.txt",
          file_type: "TXT",
          upload_timestamp: "2026-01-01T10:00:00Z",
        }),
  );
  await page
    .getByRole("button", { name: "Upload report", exact: true })
    .click();
  await expect(page.getByRole("alert").first()).toBeVisible();
  await expect(page.locator(".selected-file")).toContainText("test-report.txt");
  await page
    .getByRole("button", { name: "Upload report", exact: true })
    .click();
  await expect(page.locator(".document-card")).toContainText("test-report.txt");
});

test("API validation messages focus the error and allow patient retry", async ({
  page,
}) => {
  await api(page);
  await page.route("**/api/v1/patients", (route) =>
    route.fulfill({
      status: 422,
      json: {
        detail: [
          { loc: ["body", "age"], msg: "Age was rejected by the server" },
        ],
      },
    }),
  );
  await page.goto("/");
  const form = page.getByRole("form", { name: "Patient profile" });
  await form.getByLabel(/^First name/).fill("Test");
  await form.getByLabel(/^Last name/).fill("Patient");
  await form.getByLabel(/^Age/).fill("35");
  await form.getByLabel(/^Biological sex/).selectOption("Female");
  await form.getByLabel(/^Blood group/).selectOption("Unknown");
  await form.getByLabel(/^Height/).fill("165");
  await form.getByLabel(/^Weight/).fill("60");
  await form.getByRole("button", { name: "Create patient" }).click();
  await expect(page.getByRole("alert").first()).toContainText(
    "Age was rejected by the server",
  );
  await expect(page.locator(".notice-error")).toBeFocused();
  await expect(form.getByLabel(/^First name/)).toHaveValue("Test");
  await expect(
    form.getByRole("button", { name: "Create patient" }),
  ).toBeEnabled();
});

test("system health distinguishes successful, unknown and failed responses", async ({
  page,
}) => {
  await api(page);
  await page.goto("/status");
  await expect(
    page.getByText("Not checked", { exact: true }).first(),
  ).toBeVisible();
  await page.getByRole("button", { name: "Run health check" }).click();
  await expect(
    page.getByRole("heading", { name: "Connection healthy" }),
  ).toBeVisible();
  await expect(page.getByText("Verified healthy", { exact: true })).toHaveCount(
    1,
  );
  await page.route("**/api/v1/health", (route) =>
    ok(route, { status: "unknown" }),
  );
  await page.getByRole("button", { name: "Run health check" }).click();
  await expect(
    page.getByRole("heading", { name: "Status unverified" }),
  ).toBeVisible();
  await page.route("**/api/v1/health", (route) =>
    route.fulfill({
      status: 503,
      json: { detail: "Test backend unavailable" },
    }),
  );
  await page.getByRole("button", { name: "Run health check" }).click();
  await expect(
    page.getByRole("heading", { name: "Connection unavailable" }),
  ).toBeVisible();
  await expect(page.getByRole("status")).toContainText(
    "ClinicalAI could not complete the request",
  );
});

for (const width of [320, 375, 768, 1024, 1440, 1920]) {
  test(`routes and all workspace stages fit ${width}px with reduced motion`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 1000 });
    await page.emulateMedia({ reducedMotion: "reduce" });
    await api(page);
    for (const route of ["/settings/llm"]) {
      await page.goto(route);
      await expect(page.getByRole("form")).toBeVisible();
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      ).toBeTruthy();
    }
    await page.goto("/");
    for (let i = 1; i <= 4; i++) {
      await page.getByRole("button", { name: new RegExp(`0${i} `) }).click();
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      ).toBeTruthy();
    }
    await expect(page.locator(".brand-mark")).toHaveCSS(
      "animation-name",
      "none",
    );
    await page.goto("/status");
    await expect(
      page.getByRole("heading", { name: /Confidence starts/ }),
    ).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBeTruthy();
    if (width < 768) {
      await page.getByRole("button", { name: "Open navigation" }).click();
      await expect(
        page.getByRole("navigation", { name: "Primary navigation" }),
      ).toBeVisible();
      await page.keyboard.press("Escape");
      await expect(
        page.getByRole("button", { name: "Open navigation" }),
      ).toBeFocused();
    }
  });
}
