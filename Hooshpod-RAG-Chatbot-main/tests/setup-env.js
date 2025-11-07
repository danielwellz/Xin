process.env.NODE_ENV = "test";
process.env.PORT = process.env.PORT ?? "3000";
process.env.MONGO_URI = process.env.MONGO_URI ?? "mongodb://localhost:27017/hooshpod-test";
process.env.REDIS_URL = process.env.REDIS_URL ?? "redis://localhost:6379";
process.env.OPENROUTER_API_KEY = process.env.OPENROUTER_API_KEY ?? "test-openrouter-key";
process.env.OPENROUTER_MODEL = process.env.OPENROUTER_MODEL ?? "test-model";
process.env.KNOWLEDGE_FILE = process.env.KNOWLEDGE_FILE ?? "./knowledge.txt";
process.env.EMBEDDING_PROVIDER = process.env.EMBEDDING_PROVIDER ?? "xenova";
process.env.CHUNK_SIZE = process.env.CHUNK_SIZE ?? "256";
process.env.TOP_K = process.env.TOP_K ?? "5";
process.env.CACHE_TTL_SECONDS = process.env.CACHE_TTL_SECONDS ?? "3600";
process.env.CACHE_SIMILARITY_THRESHOLD = process.env.CACHE_SIMILARITY_THRESHOLD ?? "0.9";
process.env.CACHE_MAX_SIMILARITY_CANDIDATES =
    process.env.CACHE_MAX_SIMILARITY_CANDIDATES ?? "50";
export {};
