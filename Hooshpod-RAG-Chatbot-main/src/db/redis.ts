import { Redis } from "ioredis";
import type { RedisOptions } from "ioredis";
import { env, isProduction } from "../config/env.js";
import { logger } from "../lib/logger.js";

type RedisClient = InstanceType<typeof Redis>;

let client: RedisClient | null = null;

const createClient = (): RedisClient => {
  const options: RedisOptions = {
    lazyConnect: true,
    maxRetriesPerRequest: null,
    showFriendlyErrorStack: !isProduction,
    tls: env.REDIS_URL.startsWith("rediss://") ? {} : undefined,
  };

  const redis = new Redis(env.REDIS_URL, options);

  redis.on("connect", () => {
    logger.info("redis.connected");
  });

  redis.on("error", (error: unknown) => {
    logger.error("redis.error", { error: error instanceof Error ? error.message : error });
  });

  redis.on("close", () => {
    logger.warn("redis.connection_closed");
  });

  return redis;
};

export const getRedisClient = (): RedisClient => {
  if (!client) {
    client = createClient();
  }

  return client;
};

export const connectRedis = async (): Promise<void> => {
  const redis = getRedisClient();

  if (redis.status === "wait" || redis.status === "end") {
    await redis.connect();
  }
};

export const disconnectRedis = async (): Promise<void> => {
  if (!client) {
    return;
  }

  await client.quit();
  client = null;
  logger.info("redis.disconnected");
};
