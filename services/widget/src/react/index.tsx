import { createContext, useContext, useEffect, useRef, useState, type PropsWithChildren } from "react";
import XinBot, { type WidgetController, type WidgetOptions } from "..";

const WidgetContext = createContext<WidgetController | null>(null);

export function XinWidgetProvider({
  options,
  children
}: PropsWithChildren<{
  options: WidgetOptions;
}>) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [controller, setController] = useState<WidgetController | null>(null);

  useEffect(() => {
    let active = true;
    const container = containerRef.current ?? document.createElement("div");
    containerRef.current = container;
    document.body.appendChild(container);
    void XinBot.init({ ...options, container }).then((instance) => {
      if (!active) {
        instance.destroy();
        return;
      }
      setController(instance);
    });
    return () => {
      active = false;
      setController(null);
      container.remove();
    };
  }, [options]);

  return <WidgetContext.Provider value={controller}>{children}</WidgetContext.Provider>;
}

export function useXinBot() {
  const ctx = useContext(WidgetContext);
  if (!ctx) {
    throw new Error("useXinBot must be used within XinWidgetProvider");
  }
  return ctx;
}
