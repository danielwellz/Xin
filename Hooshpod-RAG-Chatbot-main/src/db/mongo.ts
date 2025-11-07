import mongoose from "mongoose";
import { env } from "../config/env.js";
import { logger } from "../lib/logger.js";

mongoose.set("strictQuery", true);

let connectionPromise: Promise<typeof mongoose> | null = null;

export const connectMongo = async (): Promise<typeof mongoose> => {
  if (connectionPromise) {
    return connectionPromise;
  }

  connectionPromise = mongoose.connect(env.MONGO_URI);

  mongoose.connection.on("connected", () => {
    logger.info("mongo.connected");
  });

  mongoose.connection.on("error", (error: unknown) => {
    logger.error("mongo.error", { error: error instanceof Error ? error.message : error });
  });

  mongoose.connection.on("disconnected", () => {
    logger.warn("mongo.disconnected");
  });

  return connectionPromise;
};

export const disconnectMongo = async (): Promise<void> => {
  if (mongoose.connection.readyState !== 0) {
    await mongoose.disconnect();
    connectionPromise = null;
    logger.info("mongo.connection_closed");
  }
};


