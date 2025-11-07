import { env } from "../config/env.js";

type XenovaPipeline = (text: string, options?: Record<string, unknown>) => Promise<unknown>;

interface CohereLikeClient {
  embed: (input: { texts: string[]; model: string }) => Promise<{
    embeddings?: unknown;
    data?: unknown;
  }>;
}

let xenovaPipelinePromise: Promise<XenovaPipeline> | null = null;
let cohereClientPromise: Promise<CohereLikeClient> | null = null;

const loadXenovaPipeline = async (): Promise<XenovaPipeline> => {
  if (!xenovaPipelinePromise) {
    xenovaPipelinePromise = (async () => {
      const { pipeline } = await import("@xenova/transformers");
      return pipeline("feature-extraction", "Xenova/all-MiniLM-L6-v2");
    })();
  }

  return xenovaPipelinePromise;
};

const loadCohereClient = async (): Promise<CohereLikeClient> => {
  if (!env.COHERE_API_KEY) {
    throw new Error("COHERE_API_KEY is required when EMBEDDING_PROVIDER=cohere");
  }

  if (!cohereClientPromise) {
    cohereClientPromise = (async () => {
      const { CohereClient } = await import("cohere-ai");
      return new CohereClient({ token: env.COHERE_API_KEY as string });
    })();
  }

  return cohereClientPromise;
};

const toArray = (value: unknown): number[] => {
  if (!value) {
    return [];
  }

  if (Array.isArray(value)) {
    return value.map((item) => Number(item));
  }

  if (value instanceof Float32Array || value instanceof Float64Array) {
    return Array.from(value, (item) => Number(item));
  }

  if (typeof value === "object" && value !== null) {
    const data = (value as { data?: unknown }).data;
    return toArray(data);
  }

  return [];
};

const normalize = (vector: number[]): number[] => {
  if (!vector.length) {
    return vector;
  }

  const mean = vector.reduce((sum, value) => sum + value, 0) / vector.length;
  const meanCentered = vector.map((value) => value - mean);

  const norm = Math.sqrt(meanCentered.reduce((sum, value) => sum + value * value, 0));

  if (!norm) {
    return meanCentered;
  }

  return meanCentered.map((value) => value / norm);
};

export const getEmbeddings = async (inputs: string[]): Promise<number[][]> => {
  if (!inputs.length) {
    return [];
  }

  if (env.EMBEDDING_PROVIDER === "xenova") {
    const pipeline = await loadXenovaPipeline();

    const outputs = await Promise.all(
      inputs.map(async (text) => {
        const result = await pipeline(text, { pooling: "mean", normalize: false });
        return normalize(toArray(result));
      })
    );

    return outputs;
  }

  if (env.EMBEDDING_PROVIDER === "cohere") {
    const client = await loadCohereClient();

    const response = await client.embed({
      texts: inputs,
      model: "embed-english-v3.0",
    });

    const embeddings = response.embeddings ?? response.data ?? [];

    return (embeddings as unknown[]).map((item) => {
      const vector =
        typeof item === "object" && item !== null
          ? (item as { values?: number[] }).values ?? item
          : item;
      return normalize(toArray(vector));
    });
  }

  throw new Error(`Unsupported EMBEDDING_PROVIDER: ${env.EMBEDDING_PROVIDER}`);
};
