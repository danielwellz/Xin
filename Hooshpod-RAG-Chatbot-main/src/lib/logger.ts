interface LogMeta {
  [key: string]: unknown;
}

type LogLevel = "info" | "warn" | "error" | "debug";

const write = (level: LogLevel, event: string, meta: LogMeta = {}) => {
  const payload = {
    timestamp: new Date().toISOString(),
    level,
    event,
    ...meta,
  };

  const line = JSON.stringify(payload);

  switch (level) {
    case "error":
      console.error(line);
      break;
    case "warn":
      console.warn(line);
      break;
    case "debug":
      console.debug(line);
      break;
    default:
      console.info(line);
  }
};

export const logger = {
  info: (event: string, meta?: LogMeta) => write("info", event, meta),
  warn: (event: string, meta?: LogMeta) => write("warn", event, meta),
  error: (event: string, meta?: LogMeta) => write("error", event, meta),
  debug: (event: string, meta?: LogMeta) => write("debug", event, meta),
};
