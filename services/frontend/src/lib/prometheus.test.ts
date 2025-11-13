import { parsePrometheusMetrics } from "./prometheus";

describe("parsePrometheusMetrics", () => {
  it("extracts numeric values", () => {
    const body = `
# HELP automation_queue_depth depth
automation_queue_depth 5
# HELP ingestion_jobs_inflight inflight
ingestion_jobs_inflight 2
`;
    const result = parsePrometheusMetrics(body, ["automation_queue_depth", "ingestion_jobs_inflight"]);
    expect(result.automation_queue_depth).toBe(5);
    expect(result.ingestion_jobs_inflight).toBe(2);
  });
});
