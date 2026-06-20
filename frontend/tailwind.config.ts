import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Background
        bg: {
          primary: "#080808",
          surface: "#111111",
          raised: "#1a1a1a",
        },
        // Borders
        border: {
          DEFAULT: "#2a2a2a",
          accent: "#3a3a3a",
        },
        // Gold
        gold: {
          DEFAULT: "#c9a84c",
          muted: "#999999",
        },
        // Text
        text: {
          primary: "#f0f0f0",
          secondary: "#888888",
          disabled: "#555555",
        },
        // Status
        danger: "#8b2020",
        approved: "#2a5a2a",
      },
      fontFamily: {
        cinzel: ["var(--font-cinzel)", "serif"],
        "cinzel-decorative": ["var(--font-cinzel-decorative)", "serif"],
        "im-fell": ["var(--font-im-fell)", "serif"],
        mono: ["var(--font-jetbrains)", "monospace"],
      },
    },
  },
  plugins: [],
};
export default config;
