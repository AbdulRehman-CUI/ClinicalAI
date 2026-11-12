import { apiClient } from "./client";
import type { ApiResponse } from "../types/api";

export type Provider = "openai" | "gemini";
export type LLMStatus = {
  configured: boolean;
  provider: Provider | null;
  model: string | null;
  has_api_key: boolean;
  tested: boolean;
  remember: boolean;
  expires_at: string | null;
};
export type LLMSelection = { provider: Provider; model: string; api_key?: string };
export const providerNames = { openai: "OpenAI", gemini: "Google Gemini" } as const;
export type ProviderCatalog = Record<Provider, string[]>;
const LLM_READ_TIMEOUT_MS = 12_000;

function readStatus(response: ApiResponse<LLMStatus>) {
  const status = response?.data;
  if (response?.success !== true || typeof status?.configured !== "boolean"
    || typeof status.has_api_key !== "boolean"
    || (status.provider !== null && status.provider !== "openai" && status.provider !== "gemini")) {
    throw new Error("The LLM configuration endpoint returned an unexpected response.");
  }
  return status;
}

export async function getLLMStatus(signal?: AbortSignal) {
  return readStatus((await apiClient.get<ApiResponse<LLMStatus>>("/llm/config", {
    signal, timeout: LLM_READ_TIMEOUT_MS,
  })).data);
}

export async function getLLMProviders(signal?: AbortSignal) {
  const { data: response } = await apiClient.get<ApiResponse<ProviderCatalog>>("/llm/providers", {
    signal, timeout: LLM_READ_TIMEOUT_MS,
  });
  const catalog = response?.data;
  if (response?.success !== true || !catalog || ![catalog.openai, catalog.gemini].every(
    (models) => Array.isArray(models) && models.every((model) => typeof model === "string" && model.length > 0),
  )) {
    throw new Error("The model catalog endpoint returned an unexpected response.");
  }
  return catalog;
}

export async function testLLM(selection: LLMSelection) {
  const { data } = await apiClient.post<ApiResponse<{ tested: boolean }>>("/llm/test", selection);
  if (data?.success !== true || data.data?.tested !== true) {
    throw new Error("The connection test endpoint returned an unexpected response.");
  }
}

export async function saveLLM(selection: LLMSelection & { remember: boolean }) {
  return readStatus((await apiClient.put<ApiResponse<LLMStatus>>("/llm/config", selection)).data);
}

export async function removeLLM() {
  const response = await apiClient.delete("/llm/config");
  if (response.status !== 204) throw new Error("The configuration removal endpoint returned an unexpected response.");
}
