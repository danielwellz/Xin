export function parsePrometheusMetrics(body: string, targetMetrics: string[]) {
  const lines = body.split("\n");
  const result: Record<string, number> = {};
  for (const line of lines) {
    if (line.startsWith("#") || !line.trim()) {
      continue;
    }
    for (const metric of targetMetrics) {
      if (line.startsWith(metric)) {
        const parts = line.split(" ");
        const value = Number(parts.at(-1));
        if (!Number.isNaN(value)) {
          result[metric] = value;
        }
      }
    }
  }
  return result;
}
