import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const store = new Map<string, string>();
const sets = new Map<string, Set<string>>();

const fakeRedis = {
  get: vi.fn(async (key: string) => store.get(key) ?? null),
  set: vi.fn(async (key: string, value: string, mode?: string, ttl?: number) => {
    store.set(key, value);
    if (mode === "EX" && typeof ttl === "number") {
      // emulate ttl by ignoring; tests don't rely on expiry.
    }
    return "OK";
  }),
  sadd: vi.fn(async (key: string, value: string) => {
    const bucket = sets.get(key) ?? new Set<string>();
    bucket.add(value);
    sets.set(key, bucket);
    return bucket.size;
  }),
  smembers: vi.fn(async (key: string) => {
    const bucket = sets.get(key);
    return bucket ? Array.from(bucket) : [];
  }),
  srem: vi.fn(async (key: string, value: string) => {
    const bucket = sets.get(key);
    if (!bucket) {
      return 0;
    }
    const deleted = bucket.delete(value) ? 1 : 0;
    if (bucket.size === 0) {
      sets.delete(key);
    }
    return deleted;
  }),
  expire: vi.fn(async () => 1),
  del: vi.fn(async (key: string) => {
    const hadValue = store.delete(key) ? 1 : 0;
    sets.delete(key);
    return hadValue;
  }),
};

vi.mock("../src/db/redis.js", () => ({
  getRedisClient: () => fakeRedis,
}));

import {
  findCachedAnswer,
  storeCachedAnswer,
} from "../src/services/cache.service.js";

describe("cache.service", () => {
  beforeEach(() => {
    store.clear();
    sets.clear();
    vi.clearAllMocks();
  });

  afterEach(() => {
    store.clear();
    sets.clear();
  });

  it("returns cached record when canonical hash matches", async () => {
    const record = await storeCachedAnswer({
      question: "How do I install the product?",
      canonicalQuestion: "how do i install the product?",
      answer: "Download the installer.",
      contexts: [{ id: "snippet-1", text: "Install guide" }],
      vector: [1, 0, 0],
    });

    const match = await findCachedAnswer("how do i install the product?", [1, 0, 0]);

    expect(match).not.toBeNull();
    expect(match?.id).toEqual(record.id);
    expect(match?.answer).toEqual("Download the installer.");
  });

  it("reuses cached answer when similarity above threshold", async () => {
    await storeCachedAnswer({
      question: "How do I install?",
      canonicalQuestion: "how do i install",
      answer: "Use the setup wizard.",
      contexts: [{ id: "snippet-42", text: "Wizard instructions" }],
      vector: [1, 0, 0],
    });

    const similarVector = [0.95, 0.05, 0];
    const result = await findCachedAnswer("best way to install", similarVector);

    expect(result).not.toBeNull();
    expect(result?.answer).toEqual("Use the setup wizard.");
    expect(fakeRedis.get).toHaveBeenCalled();
  });

  it("returns null when similarity is below threshold", async () => {
    await storeCachedAnswer({
      question: "How do I install?",
      canonicalQuestion: "how do i install",
      answer: "Use the setup wizard.",
      contexts: [{ id: "snippet-42", text: "Wizard instructions" }],
      vector: [1, 0, 0],
    });

    const dissimilarVector = [0, 1, 0];
    const result = await findCachedAnswer("Tell me about pricing", dissimilarVector);

    expect(result).toBeNull();
  });
});
