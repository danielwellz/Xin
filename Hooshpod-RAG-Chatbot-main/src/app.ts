import cors from "cors";
import express from "express";
import helmet from "helmet";
import rateLimit from "express-rate-limit";
import { logger } from "./lib/logger.js";
import { errorHandler } from "./middleware/error.js";
import { chatRouter } from "./routes/chat.route.js";
import { historyRouter } from "./routes/history.route.js";

const app = express();

app.use(helmet());
app.use((req, res, next) => {
  const start = Date.now();
  res.on("finish", () => {
    logger.info("http.request", {
      method: req.method,
      path: req.originalUrl,
      status: res.statusCode,
      durationMs: Date.now() - start,
    });
  });
  next();
});

// CORS is intentionally wide for local development; restrict `origin` before deploying to production.
app.use(cors());
app.use(express.json({ limit: "1mb" }));
app.use(express.urlencoded({ extended: true }));

app.get("/health", (_req, res) => {
  res.status(200).json({ status: "ok" });
});

const chatLimiter = rateLimit({
  windowMs: 60_000,
  max: 60,
  standardHeaders: true,
  legacyHeaders: false,
});

app.use("/chat", chatLimiter, chatRouter);
app.use("/history", historyRouter);

app.use(errorHandler);

export default app;


