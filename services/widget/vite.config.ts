import path from "node:path";

import { defineConfig } from "vite";
import { visualizer } from "rollup-plugin-visualizer";

const isReport = process.env.VITE_BUNDLE_REPORT === "true";
const entryMain = path.resolve(__dirname, "src/index.ts");
const entryReact = path.resolve(__dirname, "src/react/index.tsx");

export default defineConfig({
  build: {
    lib: {
      entry: entryMain,
      name: "XinBot",
      formats: ["es", "umd"],
      fileName: (format) => `xin-widget.${format}.js`
    },
    rollupOptions: {
      external: ["react", "react-dom", "react/jsx-runtime"],
      input: {
        main: entryMain,
        react: entryReact
      },
      output: [
        {
          format: "es",
          entryFileNames: (chunk) => (chunk.name === "react" ? "react.es.js" : "xin-widget.es.js"),
          exports: "named"
        },
        {
          format: "umd",
          name: "XinBot",
          entryFileNames: (chunk) => (chunk.name === "react" ? "react.umd.cjs" : "xin-widget.umd.cjs"),
          exports: "named"
        }
      ]
    },
    sourcemap: true,
    minify: "esbuild",
    target: "es2019",
    cssCodeSplit: false
  },
  plugins: [isReport ? visualizer({ filename: "dist/bundle-report.html", gzipSize: true }) : null].filter(
    Boolean
  )
});
