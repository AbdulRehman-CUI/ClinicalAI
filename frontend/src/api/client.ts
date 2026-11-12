import axios from "axios";

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "/api/v1",
  timeout: 30000,
  withCredentials: true,
  headers: {
    Accept: "application/json",
  },
});

let workspaceReady: Promise<unknown> | undefined;

function isPublicRequest(url?: string) {
  return url === "/workspace" || url === "/health" || url === "/llm/providers";
}

apiClient.interceptors.request.use(async (request) => {
  if (!["get", "head", "options"].includes(request.method ?? "get")) {
    request.headers.set("X-ClinicalAI-Request", "1");
  }
  if (isPublicRequest(request.url)) return request;
  if (!workspaceReady) {
    const initialize = async () => {
      const response = await apiClient.post("/workspace");
      if (response.status !== 204) throw new Error("The workspace endpoint returned an unexpected response.");
    };
    workspaceReady = (navigator.locks
      ? navigator.locks.request("clinicalai-workspace", initialize)
      : initialize()).catch((error: unknown) => {
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
    const responseData = error.response?.data as
      | {
          message?: string;
          errors?: Record<string, string[]>;
          error?: string;
          detail?: string | { msg?: string; loc?: (string | number)[] }[];
        }
      | undefined;
    if (responseData?.error?.startsWith("llm_") && responseData.message) {
      return responseData.message;
    }
    if (error.response.status >= 500)
      return "ClinicalAI could not complete the request. Please try again. If this continues, contact your administrator.";

    const validationMessages = Object.values(responseData?.errors ?? {})
      .flat()
      .filter((item): item is string => Boolean(item));

    if (validationMessages.length > 0) {
      return validationMessages.join(" ");
    }

    if (responseData?.message) return responseData.message;

    if (responseData?.error) {
      return responseData.error;
    }

    if (typeof responseData?.detail === "string") return responseData.detail;
    if (Array.isArray(responseData?.detail)) {
      return responseData.detail
        .map(
          (item) =>
            `${item.loc?.filter((part) => part !== "body").join(" ") || "Field"}: ${item.msg || "Invalid value"}`,
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
