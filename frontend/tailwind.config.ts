import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        /* ── Legacy aliases (keep for migration safety) ── */
        ink: "#1A2332",
        muted: "#6B7B8D",
        line: "#E2E8F0",
        panel: "#F8F9FC",
        risk: "#D32F2F",
        ok: "#1B7A4E",

        /* ── Primary: Antique Gold ── */
        gold: {
          DEFAULT: "#C9A84C",
          light: "#E8D48B",
          surface: "#FBF7ED",
          glow: "rgba(201, 168, 76, 0.15)",
        },

        /* ── Secondary: Emerald ── */
        emerald: {
          DEFAULT: "#1B7A4E",
          light: "#2ECC71",
          surface: "#E8F5E9",
        },

        /* ── Accent: Royal Blue ── */
        accent: {
          DEFAULT: "#1565C0",
          light: "#1E88E5",
          surface: "#E3F2FD",
        },

        /* ── Backgrounds ── */
        navy: {
          DEFAULT: "#0A1929",
          light: "#0F2744",
          teal: "#0F3D3E",
        },

        /* ── Surfaces ── */
        surface: {
          DEFAULT: "#FFFFFF",
          secondary: "#F8F9FC",
          warm: "#FAFAF8",
          elevated: "#FFFFFF",
        },

        /* ── Text ── */
        "text-primary": "#1A2332",
        "text-secondary": "#3A4A5C",
        "text-muted": "#6B7B8D",
        "text-on-dark": "#E8ECF1",
        "text-on-dark-muted": "#B0BEC5",

        /* ── Borders ── */
        "border-default": "#E2E8F0",
        "border-subtle": "#F0F0F0",

        /* ── Semantic ── */
        success: { DEFAULT: "#1B7A4E", surface: "#E8F5E9" },
        warning: { DEFAULT: "#E6A817", surface: "#FFF8E1" },
        danger: { DEFAULT: "#D32F2F", surface: "#FFEBEE", muted: "#E57373" },

        /* keep brand alias pointing to gold */
        brand: "#C9A84C",
      },
      fontFamily: {
        heading: ["'Outfit'", "sans-serif"],
        body: ["'Inter'", "sans-serif"],
      },
      fontSize: {
        "display-xl": ["2.5rem", { lineHeight: "1.15", letterSpacing: "-0.02em", fontWeight: "700" }],
        "display-lg": ["1.75rem", { lineHeight: "1.25", letterSpacing: "-0.01em", fontWeight: "600" }],
        "display-md": ["1.25rem", { lineHeight: "1.35", fontWeight: "600" }],
        "display-sm": ["1rem", { lineHeight: "1.4", fontWeight: "600" }],
        "body-lg": ["1.125rem", { lineHeight: "1.65", fontWeight: "400" }],
        "body-md": ["0.9375rem", { lineHeight: "1.6", fontWeight: "400" }],
        "body-sm": ["0.8125rem", { lineHeight: "1.55", fontWeight: "400" }],
        "caption": ["0.75rem", { lineHeight: "1.4", letterSpacing: "0.04em", fontWeight: "500" }],
        "label": ["0.8125rem", { lineHeight: "1.4", fontWeight: "500" }],
      },
      borderRadius: {
        card: "16px",
        button: "24px",
        input: "12px",
        badge: "9999px",
      },
      boxShadow: {
        sm: "0 1px 3px rgba(10, 25, 41, 0.06)",
        md: "0 4px 12px rgba(10, 25, 41, 0.08)",
        lg: "0 8px 24px rgba(10, 25, 41, 0.1)",
        xl: "0 16px 48px rgba(10, 25, 41, 0.12)",
        "gold-glow": "0 0 0 3px rgba(201, 168, 76, 0.1)",
        "gold-hover": "0 8px 24px rgba(201, 168, 76, 0.25)",
        "card-hover": "0 8px 24px rgba(10, 25, 41, 0.08), 0 0 0 1px rgba(201, 168, 76, 0.15)",
        inset: "inset 0 2px 4px rgba(10, 25, 41, 0.04)",
      },
      spacing: {
        18: "4.5rem",
        22: "5.5rem",
        sidebar: "260px",
      },
      transitionTimingFunction: {
        smooth: "cubic-bezier(0.4, 0, 0.2, 1)",
        spring: "cubic-bezier(0.34, 1.56, 0.64, 1)",
      },
      keyframes: {
        "fade-in-up": {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "pulse-dot": {
          "0%, 100%": { opacity: "0.4", transform: "scale(0.8)" },
          "50%": { opacity: "1", transform: "scale(1)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
      animation: {
        "fade-in-up": "fade-in-up 0.3s ease-out forwards",
        "pulse-dot": "pulse-dot 1.4s ease-in-out infinite",
        shimmer: "shimmer 2s linear infinite",
      },
    },
  },
  plugins: [require("@tailwindcss/typography")],
};

export default config;
