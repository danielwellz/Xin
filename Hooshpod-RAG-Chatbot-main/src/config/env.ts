import { config } from "dotenv";
import { z } from "zod";

config();

const optionalNumber = (schema: z.ZodNumber) =>
  z.preprocess((value) => {
    if (value === undefined || value === null) {
      return undefined;
    }

    const trimmed = String(value).trim();
    if (!trimmed) {
      return undefined;
    }

    const numeric = Number(trimmed);
    return Number.isNaN(numeric) ? undefined : numeric;
  }, schema.optional());

const envSchema = z.object({
  NODE_ENV: z.enum(["development", "test", "production"]).default("development"),
  PORT: z.coerce.number().int().positive().default(3000),
  MONGO_URI: z.string().min(1, "MONGO_URI is required"),
  REDIS_URL: z.string().min(1, "REDIS_URL is required"),
  OPENROUTER_API_KEY: z.string().min(1, "OPENROUTER_API_KEY is required"),
  OPENROUTER_MODEL: z.string().min(1, "OPENROUTER_MODEL is required"),
  OPENROUTER_MAX_TOKENS: optionalNumber(z.number().int().positive()),
  OPENROUTER_TOP_P: optionalNumber(z.number().min(0).max(1)),
  KNOWLEDGE_FILE: z.string().min(1).default("./knowledge.txt"),
  EMBEDDING_PROVIDER: z.enum(["xenova", "cohere"]).default("xenova"),
  COHERE_API_KEY: z.string().optional(),
  CHUNK_SIZE: z.coerce.number().int().positive().default(512),
  TOP_K: z.coerce.number().int().positive().default(5),
  CACHE_TTL_SECONDS: z.coerce.number().int().nonnegative().default(3600),
  CACHE_SIMILARITY_THRESHOLD: z.coerce.number().min(0).max(1).default(0.9),
  CACHE_MAX_SIMILARITY_CANDIDATES: z.coerce.number().int().positive().default(100),
});

const parsed = envSchema.safeParse(process.env);

if (!parsed.success) {
  const missing = Object.entries(parsed.error.flatten().fieldErrors)
    .filter(([, errors]) => errors && errors.length > 0)
    .map(([key]) => key)
    .join(", ");

  throw new Error(`Invalid environment configuration. Missing or invalid: ${missing}`);
}

export const env = parsed.data;
export const isProduction = env.NODE_ENV === "production";
export type AppEnvironment = typeof env;
