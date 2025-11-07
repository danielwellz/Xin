import { createHash, randomUUID } from "node:crypto";
import { env } from "../config/env.js";
import { getRedisClient } from "../db/redis.js";
import { cosineSimilarity } from "../lib/vector.js";

const CACHE_ENTRY_PREFIX = "rag:cache:entry:";
const CACHE_CANONICAL_PREFIX = "rag:cache:canonical:";
const CACHE_INDEX_KEY = "rag:cache:index";

export interface CachedContext {
  id: string;
  text?: string;
}

export interface CachedAnswerRecord {
  id: string;
  question: string;
  canonicalQuestion: string;
  answer: string;
  contexts: CachedContext[];
  vector: number[];
  createdAt: string;
}

const ttlSeconds = env.CACHE_TTL_SECONDS;
const similarityThreshold = env.CACHE_SIMILARITY_THRESHOLD;
const maxCandidates = env.CACHE_MAX_SIMILARITY_CANDIDATES;

const canonicalHash = (value: string): string => {
  return createHash("sha256").update(value).digest("hex");
};

const entryKey = (id: string): string => `${CACHE_ENTRY_PREFIX}${id}`;
const canonicalKey = (hash: string): string => `${CACHE_CANONICAL_PREFIX}${hash}`;

const writeEntry = async (record: CachedAnswerRecord): Promise<void> => {
  const redis = getRedisClient();
  const serialized = JSON.stringify(record);
  const key = entryKey(record.id);
  const canonical = canonicalKey(canonicalHash(record.canonicalQuestion));

  if (ttlSeconds > 0) {
    await Promise.all([
      redis.set(key, serialized, "EX", ttlSeconds),
      redis.set(canonical, record.id, "EX", ttlSeconds),
      redis.sadd(CACHE_INDEX_KEY, record.id),
    ]);
    await redis.expire(CACHE_INDEX_KEY, ttlSeconds);
  } else {
    await Promise.all([
      redis.set(key, serialized),
      redis.set(canonical, record.id),
      redis.sadd(CACHE_INDEX_KEY, record.id),
    ]);
  }
};

const readEntry = async (id: string): Promise<CachedAnswerRecord | null> => {
  const redis = getRedisClient();
  const raw = await redis.get(entryKey(id));

  if (!raw) {
    await redis.srem(CACHE_INDEX_KEY, id);
    return null;
  }

  try {
    const parsed = JSON.parse(raw) as CachedAnswerRecord;
    return parsed;
  } catch {
    await redis.del(entryKey(id));
    await redis.srem(CACHE_INDEX_KEY, id);
    return null;
  }
};

export const storeCachedAnswer = async (input: {
  question: string;
  canonicalQuestion: string;
  answer: string;
  contexts: CachedContext[];
  vector: number[];
}): Promise<CachedAnswerRecord> => {
  const id = randomUUID();
  const record: CachedAnswerRecord = {
    id,
    question: input.question,
    canonicalQuestion: input.canonicalQuestion,
    answer: input.answer,
    contexts: input.contexts,
    vector: input.vector,
    createdAt: new Date().toISOString(),
  };

  await writeEntry(record);
  return record;
};

export const updateCanonicalCache = async (
  canonicalQuestion: string,
  record: CachedAnswerRecord
): Promise<void> => {
  const redis = getRedisClient();
  const canonical = canonicalKey(canonicalHash(canonicalQuestion));

  if (ttlSeconds > 0) {
    await redis.set(canonical, record.id, "EX", ttlSeconds);
  } else {
    await redis.set(canonical, record.id);
  }
};

export const findCachedAnswer = async (
  canonicalQuestion: string,
  vector?: number[]
): Promise<CachedAnswerRecord | null> => {
  const redis = getRedisClient();
  const canonical = canonicalKey(canonicalHash(canonicalQuestion));
  const existingId = await redis.get(canonical);

  if (existingId) {
    const cached = await readEntry(existingId);
    if (cached) {
      return cached;
    }
    await redis.del(canonical);
  }

  if (!vector || !vector.length) {
    return null;
  }

  const candidateIds = await redis.smembers(CACHE_INDEX_KEY);
  if (!candidateIds.length) {
    return null;
  }

  let bestMatch: CachedAnswerRecord | null = null;
  let bestScore = -1;
  const limit = Math.min(candidateIds.length, maxCandidates);

  for (let index = 0; index < limit; index += 1) {
    const id = candidateIds[index];
    const candidate = await readEntry(id);

    if (!candidate) {
      continue;
    }

    const score = cosineSimilarity(vector, candidate.vector);
    if (score > bestScore) {
      bestScore = score;
      bestMatch = candidate;
    }
  }

  if (bestMatch && bestScore >= similarityThreshold) {
    await updateCanonicalCache(canonicalQuestion, bestMatch);
    return bestMatch;
  }

  return null;
};
