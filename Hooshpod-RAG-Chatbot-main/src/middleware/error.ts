import { NextFunction, Request, Response } from "express";
import { logger } from "../lib/logger.js";

export interface HttpError extends Error {
  status?: number;
  expose?: boolean;
  details?: unknown;
}

export const errorHandler = (
  error: HttpError,
  _req: Request,
  res: Response,
  _next: NextFunction
): void => {
  const status = typeof error.status === "number" && error.status >= 400 ? error.status : 500;

  logger.error("http.error", {
    status,
    message: error.message,
    details: error.details,
  });

  const responseBody = {
    error: status >= 500 && !error.expose ? "Internal Server Error" : error.message || "Internal Server Error",
  } as Record<string, unknown>;

  if (error.expose && error.details) {
    responseBody.details = error.details;
  }

  res.status(status).json(responseBody);
};

