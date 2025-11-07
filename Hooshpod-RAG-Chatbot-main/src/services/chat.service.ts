import { randomUUID } from "node:crypto";
import { promises as fs } from "node:fs";
import path from "node:path";
import { env } from "../config/env.js";
import { getEmbeddings as embed } from "../lib/embeddings.js";
import { addToStore, search, VectorRecord } from "../lib/vector.js";
import { getCompletion as llmChat } from "../lib/openrouter.js";
import { logger } from "../lib/logger.js";
import { Message, MessageDocument } from "../models/Message.js";
import {
  CachedAnswerRecord,
  findCachedAnswer,
  storeCachedAnswer,
} from "./cache.service.js";

let ragReady = false;
let ragPromise: Promise<void> | null = null;

export const chunkText = (text: string, size: number): string[] => {
  if (!text.trim()) {
    return [];
  }

  const normalized = text.replace(/\r\n/g, "\n");
  const paragraphs = normalized.split(/\n{2,}/).map((paragraph) => paragraph.trim());

  const chunks: string[] = [];

  paragraphs.forEach((paragraph) => {
    if (!paragraph) {
      return;
    }

    if (paragraph.length <= size) {
      chunks.push(paragraph);
      return;
    }

    let start = 0;
    while (start < paragraph.length) {
      const end = Math.min(start + size, paragraph.length);
      chunks.push(paragraph.slice(start, end));
      start = end;
    }
  });

  return chunks;
};

export const canonicalizeQuestion = (raw: string): string => {
  return raw.replace(/\s+/g, " ").trim().toLowerCase();
};

const loadKnowledge = async (): Promise<{ chunks: string[]; filePath: string }> => {
  const filePath = path.resolve(env.KNOWLEDGE_FILE);
  const raw = await fs.readFile(filePath, "utf-8");
  const chunks = chunkText(raw, env.CHUNK_SIZE);

  return { chunks, filePath };
};

export const initializeRAG = async (): Promise<void> => {
  if (ragReady) {
    return;
  }

  if (ragPromise) {
    return ragPromise;
  }

  ragPromise = (async () => {
    const { chunks, filePath } = await loadKnowledge();

    if (!chunks.length) {
      logger.warn("knowledge.empty", { filePath });
      ragReady = true;
      return;
    }

    const embeddings = await embed(chunks);

    const items: VectorRecord[] = embeddings.map((vector: number[], index: number) => ({
      id: `${filePath}:${index}`,
      text: chunks[index],
      vector,
    }));

    addToStore(items);
    ragReady = true;
    logger.info("knowledge.loaded", { chunks: items.length, filePath });
  })()
    .catch((error) => {
      ragReady = false;
      logger.error("knowledge.failed", { error: error instanceof Error ? error.message : error });
      throw error;
    })
    .finally(() => {
      ragPromise = null;
    });

  return ragPromise;
};

const SYSTEM_DIRECTIVE = [
  "You are the Hooshpod retrieval assistant.",
  "Use the supplied context snippets when answering questions.",
  "If the context does not contain the answer, reply with 'I don't know.'",
  "Respond concisely and use the same language as the user.",
].join(" ");

const buildPrompt = (question: string, contexts: VectorRecord[]): string => {
  const contextText = contexts.map((item: VectorRecord, index: number) => `Snippet ${index + 1}::\n${item.text}`).join("\n\n");

  return [
    contextText ? `Context:\n${contextText}` : "Context: (none)",
    `Question: ${question}`,
    "Answer:",
  ].join("\n\n");
};

const mapCachedContextsToRecords = (contexts: CachedAnswerRecord["contexts"]): VectorRecord[] => {
  return contexts.map((item, index) => ({
    id: item.id ?? `cached:${index}`,
    text: item.text ?? "",
    vector: [],
  }));
};

const serializeContexts = (contexts: VectorRecord[]) => {
  return contexts.map((item) => ({
    id: item.id,
    text: item.text,
  }));
};

export interface ChatRequestOptions {
  message: string;
  userId: string;
  sessionId?: string | null;
}

export interface ChatResponsePayload {
  response: string;
  cached: boolean;
  timestamp: string;
  sessionId: string;
}

export const chatWithUser = async ({
  message,
  userId,
  sessionId,
}: ChatRequestOptions): Promise<ChatResponsePayload> => {
  await initializeRAG();

  const trimmedMessage = message.trim();
  const canonicalQuestion = canonicalizeQuestion(message);
  const activeSessionId = sessionId && sessionId.trim().length ? sessionId.trim() : randomUUID();

  if (!trimmedMessage.length) {
    throw new Error("Message must not be empty");
  }

  const [questionVectorRaw] = await embed([trimmedMessage]);
  const questionVector = Array.isArray(questionVectorRaw) ? questionVectorRaw : [];

  let contexts: VectorRecord[] = [];
  let answer: string;
  let cached = false;
  let cacheRecord: CachedAnswerRecord | null = null;

  if (questionVector.length) {
    cacheRecord = await findCachedAnswer(canonicalQuestion, questionVector);
  }

  if (cacheRecord) {
    answer = cacheRecord.answer;
    cached = true;
    contexts = mapCachedContextsToRecords(cacheRecord.contexts);
  } else {
    contexts = questionVector.length ? search(questionVector, env.TOP_K) : [];
    const prompt = buildPrompt(trimmedMessage, contexts);
    answer = await llmChat({ prompt, system: SYSTEM_DIRECTIVE });

    if (questionVector.length) {
      cacheRecord = await storeCachedAnswer({
        question: trimmedMessage,
        canonicalQuestion,
        answer,
        contexts: serializeContexts(contexts),
        vector: questionVector,
      });
    }
  }

  const timestamp = new Date();

  await Message.create({
    userId,
    sessionId: activeSessionId,
    message: trimmedMessage,
    response: answer,
    cached,
    meta: {
      canonicalQuestion,
      contexts: cacheRecord ? cacheRecord.contexts : serializeContexts(contexts),
    },
  });

  return {
    response: answer,
    cached,
    timestamp: timestamp.toISOString(),
    sessionId: activeSessionId,
  };
};

export const getHistoryByUser = async (
  userId: string,
  limit = 20,
  page = 1
): Promise<MessageDocument[]> => {
  const safeLimit = Math.max(1, Math.min(limit, 100));
  const safePage = Math.max(1, page);
  const skip = (safePage - 1) * safeLimit;

  const documents = await Message.find({ userId })
    .sort({ createdAt: 1 })
    .skip(skip)
    .limit(safeLimit)
    .exec();

  return documents;
};
