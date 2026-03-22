import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0f172a",
        panel: "#131b2f",
        panelSoft: "#1b2640",
        line: "#27344f",
        mist: "#eef2ff",
        frost: "#f8fafc",
        accent: "#3b82f6",
        teal: "#0f766e",
        cyan: "#0891b2",
        gold: "#c08a18"
      },
      fontFamily: {
        display: ["Manrope", "IBM Plex Sans", "sans-serif"],
        body: ["IBM Plex Sans", "sans-serif"]
      },
      boxShadow: {
        glow: "0 30px 80px rgba(15, 23, 42, 0.22)",
        card: "0 18px 48px rgba(15, 23, 42, 0.10)",
        soft: "0 24px 70px rgba(2, 6, 23, 0.28)"
      },
      borderRadius: {
        "4xl": "2rem"
      }
    }
  },
  plugins: []
} satisfies Config;
