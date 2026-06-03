import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#101828",
        muted: "#667085",
        line: "#d9e2ec",
        panel: "#f6f8fb",
        brand: "#155EEF",
        risk: "#B42318",
        ok: "#067647"
      }
    }
  },
  plugins: []
};

export default config;
