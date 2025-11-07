export interface VectorRecord {
  id: string;
  text: string;
  vector: number[];
}

export interface VectorStore {
  add(items: VectorRecord[]): void;
  search(queryVector: number[], topK?: number): VectorRecord[];
  clear(): void;
}

const store: VectorRecord[] = [];

export const cosineSimilarity = (a: number[], b: number[]): number => {
  if (!a.length || a.length !== b.length) {
    return 0;
  }

  const dot = a.reduce((sum, value, index) => sum + value * b[index], 0);
  const normA = Math.sqrt(a.reduce((sum, value) => sum + value * value, 0));
  const normB = Math.sqrt(b.reduce((sum, value) => sum + value * value, 0));

  if (!normA || !normB) {
    return 0;
  }

  return dot / (normA * normB);
};

export const inMemoryVectorStore: VectorStore = {
  add: (items: VectorRecord[]) => {
    items.forEach((item) => {
      const existingIndex = store.findIndex((record) => record.id === item.id);

      if (existingIndex >= 0) {
        store[existingIndex] = item;
      } else {
        store.push(item);
      }
    });
  },
  search: (queryVector: number[], topK = 5) => {
    if (!queryVector.length) {
      return [];
    }

    return store
      .map((record) => ({
        record,
        score: cosineSimilarity(queryVector, record.vector),
      }))
      .sort((a, b) => b.score - a.score)
      .slice(0, topK)
      .map(({ record }) => record);
  },
  clear: () => {
    store.splice(0, store.length);
  },
};

let activeStore: VectorStore = inMemoryVectorStore;

export const setVectorStore = (nextStore: VectorStore): void => {
  activeStore = nextStore;
};

export const addToStore = (items: VectorRecord[]): void => {
  activeStore.add(items);
};

export const search = (queryVector: number[], topK = 5): VectorRecord[] => {
  return activeStore.search(queryVector, topK);
};

export const clearStore = (): void => {
  activeStore.clear();
};
