import axios from "axios";

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "/api/v1",
  timeout: 30000,
  headers: {
    Accept: "application/json",
  },
});

export function getApiErrorMessage(error: unknown, fallback = "Request failed.") {
  if (axios.isAxiosError(error)) {
    const responseData = error.response?.data as
      | {
          message?: string;
          errors?: Record<string, string[]>;
          error?: string;
        }
      | undefined;

    if (responseData?.message) {
      return responseData.message;
    }

    const validationMessages = Object.values(responseData?.errors ?? {})
      .flat()
      .filter((item): item is string => Boolean(item));

    if (validationMessages.length > 0) {
      return validationMessages.join(" ");
    }

    if (responseData?.error) {
      return responseData.error;
    }

    if (error.message) {
      return error.message;
    }
  }

  return fallback;
}
