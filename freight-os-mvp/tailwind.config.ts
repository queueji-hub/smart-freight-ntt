import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        bg: { DEFAULT: "#08090A", elevated: "#101113", subtle: "#1A1B1F" },
        border: { DEFAULT: "#23252B", strong: "#2E3037" },
        text: { primary: "#F7F8F8", secondary: "#9CA0A8", tertiary: "#62656B" },
        accent: { DEFAULT: "#5E6AD2", hover: "#6E7BE0", subtle: "#5E6AD220" },
        success: "#26B574",
        warning: "#F2994A",
        danger: "#E5484D",
      },
      fontFamily: { sans: ["Inter", "system-ui", "sans-serif"] },
      animation: {
        "pulse-soft": "pulse-soft 2s cubic-bezier(0.4,0,0.6,1) infinite",
      },
      keyframes: {
        "pulse-soft": { "0%,100%": { opacity: "1" }, "50%": { opacity: "0.6" } },
      },
    },
  },
  plugins: [],
};
export default config;
