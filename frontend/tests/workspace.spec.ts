import { expect, test, type Page, type Route } from "@playwright/test";

// Synthetic records are confined to intercepted test requests. No real service is called.
const user = {
  id: 1,
  full_name: "Test Clinician",
  email: "clinician@example.test",
  role: "Doctor",
  is_active: true,
  created_at: "2026-01-01",
  updated_at: "2026-01-01",
};
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

async function api(page: Page, role = "Doctor") {
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
    if (path === "/auth/users/me") return ok(route, { ...user, role });
    if (path === "/auth/login" || path === "/auth/register")
      return ok(route, {
        access_token: "test-access-token",
        refresh_token: "test-refresh-token",
      });
    if (path === "/patients") return ok(route, { ...patient, ...body });
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

async function session(page: Page, role = "Doctor") {
  await page.addInitScript(
    ({ user, role }) => {
      sessionStorage.setItem("clinicalai_access_token", "test-access-token");
      sessionStorage.setItem("clinicalai_refresh_token", "test-refresh-token");
      sessionStorage.setItem(
        "clinicalai_user",
        JSON.stringify({ ...user, role }),
      );
    },
    { user, role },
  );
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

test("protected routes redirect, sign in and logout preserve routing", async ({
  page,
}) => {
  const requests = await api(page);
  await page.goto("/status");
  await expect(page).toHaveURL(/\/login$/);
  await page.getByLabel(/^Email address/).fill(user.email);
  await page.getByLabel(/^Password/).fill("test-password");
  await page.getByRole("button", { name: "Show password" }).click();
  await expect(page.getByLabel(/^Password/)).toHaveAttribute("type", "text");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: /A clearer picture/ }),
  ).toBeVisible();
  expect(
    requests.some((r) => r.path === "/auth/login" && r.method === "POST"),
  ).toBeTruthy();
  await page.getByRole("button", { name: "Log out", exact: true }).click();
  await expect(page).toHaveURL(/\/login$/);
  await page.goto("/");
  await expect(page).toHaveURL(/\/login$/);
});

test("registration submits the existing role and token contract", async ({
  page,
}) => {
  const requests = await api(page, "Staff");
  await page.goto("/register");
  await page.getByLabel(/^Full name/).fill("Test Clinician");
  await page.getByLabel(/^Email address/).fill(user.email);
  await page.getByLabel(/^Password/).fill("test-password");
  await page.getByLabel(/^Clinical role/).selectOption("Staff");
  await page
    .getByRole("button", { name: "Create account", exact: true })
    .click();
  await expect(page).toHaveURL(/\/$/);
  expect(requests.find((r) => r.path === "/auth/register")?.body).toEqual({
    full_name: "Test Clinician",
    email: user.email,
    password: "test-password",
    role: "Staff",
  });
});

test("patient validation, every clinical form, profile editing, analysis objects and reset", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  const requests = await api(page);
  await session(page);
  await page.goto("/");
  await expect(page.getByLabel(/^First name/)).toHaveValue("");
  await page
    .getByRole("button", { name: "Create patient", exact: true })
    .click();
  expect(requests.filter((r) => r.path === "/patients")).toHaveLength(0);
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

test("report keyboard selection, removal, upload, and report-only analysis readiness", async ({
  page,
}) => {
  const requests = await api(page);
  await session(page);
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

test("Staff cannot run analysis", async ({ page }) => {
  await api(page, "Staff");
  await session(page, "Staff");
  await page.goto("/");
  await createPatient(page);
  await addSymptom(page);
  await page.getByRole("button", { name: /04 AI analysis/ }).click();
  await expect(
    page.getByRole("button", { name: "Run clinical analysis" }),
  ).toBeDisabled();
  await expect(page.getByText(/Your Staff role/)).toBeVisible();
});

test("profile failure cannot authenticate a decoded JWT", async ({ page }) => {
  await api(page);
  const token = `header.${Buffer.from(JSON.stringify({ sub: "1", role: "Doctor" })).toString("base64url")}.signature`;
  await page.route("**/api/v1/auth/login", (route) =>
    ok(route, { access_token: token, refresh_token: "test-refresh" }),
  );
  await page.route("**/api/v1/auth/users/me", (route) =>
    route.fulfill({
      status: 500,
      json: {
        message: "Internal server error",
        detail: "sensitive server details",
      },
    }),
  );
  await page.goto("/login");
  await page.getByLabel(/^Email address/).fill(user.email);
  await page.getByLabel(/^Password/).fill("test-password");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText(
    "ClinicalAI could not complete the request",
  );
  await expect(page.getByRole("alert")).not.toContainText(
    "sensitive server details",
  );
  await expect(page).toHaveURL(/\/login$/);
  expect(
    await page.evaluate(() =>
      sessionStorage.getItem("clinicalai_access_token"),
    ),
  ).toBeNull();
});

test("cached users cannot bypass failed server validation", async ({
  page,
}) => {
  await api(page);
  await session(page);
  await page.route("**/api/v1/auth/users/me", (route) =>
    route.fulfill({ status: 401, json: { message: "Invalid token" } }),
  );
  await page.route("**/api/v1/auth/refresh", (route) =>
    route.fulfill({ status: 401, json: { message: "Invalid refresh token" } }),
  );
  await page.goto("/");
  await expect(page).toHaveURL(/\/login$/);
  await expect(
    page.getByRole("heading", { name: /A clearer picture/ }),
  ).not.toBeVisible();
  expect(
    await page.evaluate(() => sessionStorage.getItem("clinicalai_user")),
  ).toBeNull();
});

test("an expired stored session is refreshed and validated before access", async ({
  page,
}) => {
  await api(page);
  await session(page);
  let refreshes = 0;
  await page.route("**/api/v1/auth/users/me", (route) =>
    route.request().headers().authorization === "Bearer renewed-access"
      ? ok(route, user)
      : route.fulfill({ status: 401, json: { message: "Expired token" } }),
  );
  await page.route("**/api/v1/auth/refresh", (route) => {
    refreshes++;
    return ok(route, {
      access_token: "renewed-access",
      refresh_token: "renewed-refresh",
    });
  });
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: /A clearer picture/ }),
  ).toBeVisible();
  expect(refreshes).toBe(1);
  expect(
    await page.evaluate(() =>
      sessionStorage.getItem("clinicalai_access_token"),
    ),
  ).toBe("renewed-access");
});

test("an expired API request renews the session and retries once", async ({
  page,
}) => {
  await api(page);
  await session(page);
  let attempts = 0;
  await page.route("**/api/v1/patients", (route) => {
    attempts++;
    return attempts === 1
      ? route.fulfill({ status: 401, json: { message: "Expired token" } })
      : ok(route, { ...patient, ...route.request().postDataJSON() });
  });
  await page.route("**/api/v1/auth/refresh", (route) =>
    ok(route, {
      access_token: "renewed-access",
      refresh_token: "renewed-refresh",
    }),
  );
  await page.goto("/");
  await createPatient(page);
  expect(attempts).toBe(2);
  expect(
    await page.evaluate(() =>
      sessionStorage.getItem("clinicalai_access_token"),
    ),
  ).toBe("renewed-access");
});

test("logout cannot be undone by an in-flight token renewal", async ({
  page,
}) => {
  await api(page);
  await session(page);
  let release: () => void = () => {};
  const held = new Promise<void>((resolve) => {
    release = resolve;
  });
  let renewalStarted: () => void = () => {};
  const started = new Promise<void>((resolve) => {
    renewalStarted = resolve;
  });
  await page.route("**/api/v1/health", (route) =>
    route.fulfill({ status: 401, json: { message: "Expired token" } }),
  );
  await page.route("**/api/v1/auth/refresh", async (route) => {
    renewalStarted();
    await held;
    return ok(route, {
      access_token: "late-access",
      refresh_token: "late-refresh",
    });
  });
  await page.goto("/status");
  await page.getByRole("button", { name: "Run health check" }).click();
  await started;
  await page.getByRole("button", { name: "Log out", exact: true }).click();
  release();
  await expect(page).toHaveURL(/\/login$/);
  await expect(
    page.getByRole("heading", { name: "Welcome back." }),
  ).toBeVisible();
  expect(
    await page.evaluate(() =>
      sessionStorage.getItem("clinicalai_access_token"),
    ),
  ).toBeNull();
});

test("analysis pending, failure, and retry preserve honest result states", async ({
  page,
}) => {
  await api(page);
  await session(page);
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
  await session(page);
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
  await session(page);
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
  await session(page);
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
    for (const route of ["/login", "/register"]) {
      await page.goto(route);
      await expect(page.getByRole("form")).toBeVisible();
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      ).toBeTruthy();
    }
    await session(page);
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
