import http from "node:http";
import app from "./app.js";
import { env } from "./config/env.js";
import { connectMongo, disconnectMongo } from "./db/mongo.js";
import { connectRedis, disconnectRedis } from "./db/redis.js";
import { logger } from "./lib/logger.js";
import { initializeRAG } from "./services/chat.service.js";

const bootstrap = async (): Promise<void> => {
  try {
    await connectMongo();
    await connectRedis();
    await initializeRAG();

    const server = http.createServer(app);

    server.listen(env.PORT, () => {
      logger.info("server.listening", { port: env.PORT });
    });

    const shutdown = async (signal: NodeJS.Signals | string, exitCode = 0) => {
      logger.info("server.shutdown_initiated", { signal, exitCode });

      await new Promise<void>((resolve) => {
        server.close(() => {
          logger.info("server.http_closed");
          resolve();
        });
      });

      await Promise.all([disconnectMongo(), disconnectRedis()]);
      process.exit(exitCode);
    };

    process.once("SIGINT", (signal) => {
      void shutdown(signal, 0);
    });
    process.once("SIGTERM", (signal) => {
      void shutdown(signal, 0);
    });
    process.once("uncaughtException", (error) => {
      logger.error("server.uncaught_exception", { message: error.message });
      shutdown("uncaughtException", 1).catch((shutdownError) => {
        logger.error("server.shutdown_failed", { error: shutdownError });
        process.exit(1);
      });
    });
    process.once("unhandledRejection", (reason) => {
      logger.error("server.unhandled_rejection", { reason });
      shutdown("unhandledRejection", 1).catch((shutdownError) => {
        logger.error("server.shutdown_failed", { error: shutdownError });
        process.exit(1);
      });
    });
  } catch (error) {
    logger.error("server.bootstrap_failed", { error: error instanceof Error ? error.message : error });
    process.exit(1);
  }
};

bootstrap();


