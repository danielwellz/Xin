import type { Config } from "tailwindcss";
import forms from "@tailwindcss/forms";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./index.html",
    "./src/**/*.{ts,tsx}",
    "./.storybook/**/*.{ts,tsx}",
    "./stories/**/*.{ts,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: "var(--color-brand)",
          foreground: "var(--color-on-brand)",
          muted: "var(--color-brand-muted)"
        },
        surface: {
          DEFAULT: "var(--color-surface)",
          foreground: "var(--color-on-surface)"
        },
        border: "var(--color-border)"
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        display: ["var(--font-display)", "system-ui", "sans-serif"]
      },
      boxShadow: {
        card: "0 10px 40px rgba(15, 23, 42, 0.08)"
      },
      spacing: {
        gutter: "var(--layout-gutter)"
      }
    }
  },
  plugins: [
    forms,
    function rtlVariant({ addVariant }) {
      addVariant("rtl", ":where([dir='rtl'] &)");
      addVariant("ltr", ":where([dir='ltr'] &)");
    }
  ]
};

export default config;
