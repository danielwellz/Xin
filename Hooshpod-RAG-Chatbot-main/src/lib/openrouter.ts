import axios, { AxiosError } from "axios";
import { env } from "../config/env.js";

type Role = "system" | "user";

export interface ChatCompletionOptions {
  prompt: string;
  system?: string;
}

const REQUEST_TIMEOUT_MS = 45_000;
const MAX_ATTEMPTS = 2;

const client = axios.create({
  baseURL: "https://openrouter.ai/api/v1",
  timeout: REQUEST_TIMEOUT_MS,
  headers: {
    Authorization: `Bearer ${env.OPENROUTER_API_KEY}`,
    "Content-Type": "application/json",
    "HTTP-Referer": "https://hooshpod.com",
    "X-Title": "Hooshpod RAG Chatbot",
  },
});

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

const shouldRetry = (error: unknown, attempt: number): boolean => {
  if (attempt >= MAX_ATTEMPTS - 1) {
    return false;
  }

  if (!axios.isAxiosError(error)) {
    return false;
  }

  const status = error.response?.status;
  return status === 429 || (status !== undefined && status >= 500 && status < 600);
};

export const getCompletion = async ({ prompt, system }: ChatCompletionOptions): Promise<string> => {
  const messages: Array<{ role: Role; content: string }> = [
    ...(system ? [{ role: "system" as Role, content: system }] : []),
    { role: "user" as Role, content: prompt },
  ];

  let attempt = 0;
  let lastError: unknown;

  while (attempt < MAX_ATTEMPTS) {
    try {
      const response = await client.post("/chat/completions", {
        model: env.OPENROUTER_MODEL,
        messages,
        temperature: 0.2,
        max_tokens: env.OPENROUTER_MAX_TOKENS,
        top_p: env.OPENROUTER_TOP_P,
      });

      const message = response.data?.choices?.[0]?.message?.content;
      if (!message) {
        throw new Error("OpenRouter response missing message content");
      }

      return message;
    } catch (error) {
      lastError = error;

      if (!shouldRetry(error, attempt)) {
        break;
      }

      const backoff = 500 * (attempt + 1) + Math.floor(Math.random() * 250);
      await delay(backoff);
      attempt += 1;
    }
  }

  if (lastError instanceof AxiosError) {
    throw lastError;
  }

  throw new Error("Failed to fetch completion from OpenRouter");
};

