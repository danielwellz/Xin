import { NextFunction, Request, Response, Router } from "express";
import { z } from "zod";
import { chatWithUser } from "../services/chat.service.js";

export const chatRouter = Router();

const chatBodySchema = z.object({
  message: z.string().trim().min(1, "message is required"),
  userId: z.string().trim().min(1, "userId is required"),
  sessionId: z
    .string()
    .trim()
    .optional()
    .transform((value) => (value && value.length > 0 ? value : undefined)),
});

chatRouter.post("/", async (req: Request, res: Response, next: NextFunction) => {
  try {
    const parsed = chatBodySchema.safeParse(req.body ?? {});

    if (!parsed.success) {
      return res.status(400).json({
        message: "Invalid request body",
        issues: parsed.error.format(),
      });
    }

    const payload = await chatWithUser(parsed.data);

    return res.status(200).json({
      response: payload.response,
      cached: payload.cached,
      timestamp: payload.timestamp,
      sessionId: payload.sessionId,
    });
  } catch (error) {
    return next(error);
  }
});
