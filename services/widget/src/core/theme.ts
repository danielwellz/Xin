import type { ThemeConfig } from "../types";

export function applyTheme(root: HTMLElement, theme?: ThemeConfig) {
  if (!theme) {
    return;
  }
  const mapper: Record<string, string | number | undefined> = {
    "--xin-color-primary": theme.primary,
    "--xin-color-primary-contrast": theme.primaryContrast,
    "--xin-color-surface": theme.surface,
    "--xin-color-surface-alt": theme.surfaceAlt,
    "--xin-color-text": theme.text,
    "--xin-radius": theme.radius ? `${theme.radius}px` : undefined
  };
  Object.entries(mapper).forEach(([key, value]) => {
    if (value) {
      root.style.setProperty(key, String(value));
    }
  });
}
