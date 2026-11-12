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

export async function getLLMStatus() {
  return (await apiClient.get<ApiResponse<LLMStatus>>("/llm/config")).data.data;
}

export async function getLLMProviders() {
  return (await apiClient.get<ApiResponse<Record<Provider, string[]>>>("/llm/providers")).data.data;
}

export async function testLLM(selection: LLMSelection) {
  await apiClient.post("/llm/test", selection);
}

export async function saveLLM(selection: LLMSelection & { remember: boolean }) {
  return (await apiClient.put<ApiResponse<LLMStatus>>("/llm/config", selection)).data.data;
}

export async function removeLLM() {
  await apiClient.delete("/llm/config");
}
