import { NextFunction, Request, Response, Router } from "express";
import { z } from "zod";
import { getHistoryByUser } from "../services/chat.service.js";

export const historyRouter = Router();

const historyParamsSchema = z.object({
  userId: z.string().trim().min(1, "userId is required"),
});

const historyQuerySchema = z.object({
  limit: z
    .string()
    .optional()
    .transform((value) => (value ? Number.parseInt(value, 10) : undefined))
    .pipe(z.number().int().positive().max(100).optional()),
  page: z
    .string()
    .optional()
    .transform((value) => (value ? Number.parseInt(value, 10) : undefined))
    .pipe(z.number().int().positive().optional()),
});

historyRouter.get("/:userId", async (req: Request, res: Response, next: NextFunction) => {
  try {
    const paramsResult = historyParamsSchema.safeParse(req.params ?? {});
    const queryResult = historyQuerySchema.safeParse(req.query ?? {});

    if (!paramsResult.success || !queryResult.success) {
      return res.status(400).json({
        message: "Invalid query parameters",
        issues: {
          params: paramsResult.success ? undefined : paramsResult.error.format(),
          query: queryResult.success ? undefined : queryResult.error.format(),
        },
      });
    }

    const { userId } = paramsResult.data;
    const { limit, page } = queryResult.data;
    const history = await getHistoryByUser(userId, limit ?? 20, page ?? 1);

    return res.status(200).json({
      history,
      userId,
      limit: limit ?? 20,
      page: page ?? 1,
    });
  } catch (error) {
    return next(error);
  }
});

