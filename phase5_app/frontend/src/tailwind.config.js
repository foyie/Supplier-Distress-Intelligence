/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        display: ['"DM Serif Display"', "serif"],
        mono: ['"DM Mono"', "monospace"],
        sans: ['"DM Sans"', "sans-serif"],
      },
      colors: {
        ink: "#0D0F12",
        paper: "#F4F2EE",
        mist: "#E8E5DF",
        ash: "#9B9690",
        high: "#C0392B",
        mid: "#D4860A",
        low: "#27AE60",
        accent: "#1A4ED8",
      },
      animation: {
        "fade-up": "fadeUp 0.5s ease forwards",
        "pulse-dot": "pulseDot 2s infinite",
      },
      keyframes: {
        fadeUp: {
          "0%": { opacity: 0, transform: "translateY(12px)" },
          "100%": { opacity: 1, transform: "translateY(0)" },
        },
        pulseDot: {
          "0%, 100%": { opacity: 1 },
          "50%": { opacity: 0.3 },
        },
      },
    },
  },
  plugins: [],
};
