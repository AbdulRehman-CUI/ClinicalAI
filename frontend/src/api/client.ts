import axios from "axios";

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "/api/v1",
  timeout: 30000,
  withCredentials: true,
  headers: {
    Accept: "application/json",
  },
});

const WORKSPACE_TIMEOUT_MS = 12_000;
let workspaceReady: Promise<void> | undefined;

function isPublicRequest(url?: string) {
  return url === "/workspace" || url === "/health" || url === "/llm/providers";
}

async function initializeWorkspace() {
  // Axios's request timeout starts after the browser grants the lock.
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), WORKSPACE_TIMEOUT_MS);
  try {
    const initialize = async () => {
      const response = await apiClient.post("/workspace", undefined, { signal: controller.signal });
      if (response.status !== 204) throw new Error("The workspace endpoint returned an unexpected response.");
    };
    if (navigator.locks) {
      await navigator.locks.request("clinicalai-workspace", { signal: controller.signal }, initialize);
    } else {
      await initialize();
    }
  } catch (error) {
    if (controller.signal.aborted) throw new Error("Workspace setup timed out. Please try again.");
    throw error;
  } finally {
    clearTimeout(timer);
  }
}

apiClient.interceptors.request.use(async (request) => {
  if (!["get", "head", "options"].includes(request.method ?? "get")) {
    request.headers.set("X-ClinicalAI-Request", "1");
  }
  if (isPublicRequest(request.url)) return request;
  if (!workspaceReady) {
    workspaceReady = initializeWorkspace().catch((error: unknown) => {
      workspaceReady = undefined;
      throw error;
    });
  }
  await workspaceReady;
  return request;
});

apiClient.interceptors.response.use(undefined, (error: unknown) => {
  if (axios.isAxiosError(error) && error.response?.status === 401 && !isPublicRequest(error.config?.url)) {
    workspaceReady = undefined;
  }
  return Promise.reject(error);
});

export function getApiErrorMessage(
  error: unknown,
  fallback = "Request failed.",
) {
  if (axios.isAxiosError(error)) {
    if (!error.response) {
      return error.code === "ECONNABORTED"
        ? "The request timed out. Please try again."
        : "Unable to connect to ClinicalAI. Check your connection and try again.";
    }
    if (error.response.status === 500 && typeof error.response.data === "string"
      && error.response.data.includes("FUNCTION_INVOCATION_FAILED")) {
      return "The deployed ClinicalAI API failed to start or respond. Contact your administrator.";
    }
    const responseData = error.response?.data as
      | {
          message?: string;
          errors?: Record<string, string[]>;
          error?: string;
          detail?: string | { msg?: string; loc?: (string | number)[] }[];
        }
      | undefined;
    if (typeof responseData?.error === "string"
      && /^(llm_|workspace_|database_)/.test(responseData.error)
      && typeof responseData.message === "string" && responseData.message) {
      return responseData.message;
    }
    if (error.response.status >= 500)
      return "ClinicalAI could not complete the request. Please try again. If this continues, contact your administrator.";

    const validationMessages = Object.values(responseData?.errors ?? {})
      .flat()
      .filter((item): item is string => typeof item === "string" && Boolean(item));

    if (validationMessages.length > 0) {
      return validationMessages.join(" ");
    }

    if (typeof responseData?.message === "string" && responseData.message) return responseData.message;

    if (typeof responseData?.detail === "string") return responseData.detail;
    if (Array.isArray(responseData?.detail)) {
      return responseData.detail
        .map(
          (item) => {
            const field = Array.isArray(item?.loc)
              ? item.loc.filter((part) => part !== "body").join(".")
              : "";
            return `${field || "Field"}: ${typeof item?.msg === "string" ? item.msg : "Invalid value"}`;
          },
        )
        .join(" ");
    }

    if (error.message) {
      return error.message;
    }
  }

  if (error instanceof Error && error.message) return error.message;
  return fallback;
}
