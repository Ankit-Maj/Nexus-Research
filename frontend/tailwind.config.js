/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        // ── Crimson accent palette ──────────────────────────────────────────
        crimson: {
          50:  "#fff1f1",
          100: "#ffe4e4",
          200: "#fecaca",
          300: "#fca5a5",
          400: "#f87171",
          500: "#ef4444",
          600: "#dc2626",
          700: "#b91c1c",
          800: "#991b1b",
          900: "#7f1d1d",
          950: "#450a0a",
        },
        // ── Surface palette ─────────────────────────────────────────────────
        surface: {
          950: "#09090b",
          900: "#111113",
          800: "#18181b",
          700: "#1c1c1f",
          600: "#27272a",
          500: "#3f3f46",
        },
        // ── Zinc text ───────────────────────────────────────────────────────
        zinc: {
          50:  "#fafafa",
          100: "#f4f4f5",
          200: "#e4e4e7",
          300: "#d4d4d8",
          400: "#a1a1aa",
          500: "#71717a",
          600: "#52525b",
          700: "#3f3f46",
          800: "#27272a",
          900: "#18181b",
          950: "#09090b",
        },
      },
      fontFamily: {
        sans:  ["Inter", "system-ui", "sans-serif"],
        mono:  ["JetBrains Mono", "Fira Code", "monospace"],
      },
      backgroundImage: {
        "noise": "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.04'/%3E%3C/svg%3E\")",
      },
      animation: {
        "pulse-slow":   "pulse 3s cubic-bezier(0.4,0,0.6,1) infinite",
        "glow-pulse":   "glowPulse 2s ease-in-out infinite",
        "shimmer":      "shimmer 1.8s linear infinite",
        "fade-in":      "fadeIn 0.4s ease forwards",
        "slide-up":     "slideUp 0.35s ease forwards",
        "slide-left":   "slideLeft 0.3s ease forwards",
        "dot-bounce":   "dotBounce 1.2s ease-in-out infinite",
        "scan-line":    "scanLine 3s linear infinite",
        "border-flow":  "borderFlow 3s linear infinite",
      },
      keyframes: {
        glowPulse: {
          "0%,100%": { boxShadow: "0 0 12px 0 rgba(220,38,38,0.15)" },
          "50%":     { boxShadow: "0 0 28px 4px rgba(220,38,38,0.30)" },
        },
        shimmer: {
          "0%":   { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        fadeIn: {
          from: { opacity: 0 },
          to:   { opacity: 1 },
        },
        slideUp: {
          from: { opacity: 0, transform: "translateY(12px)" },
          to:   { opacity: 1, transform: "translateY(0)" },
        },
        slideLeft: {
          from: { opacity: 0, transform: "translateX(20px)" },
          to:   { opacity: 1, transform: "translateX(0)" },
        },
        dotBounce: {
          "0%,80%,100%": { transform: "scale(0.6)", opacity: 0.4 },
          "40%":          { transform: "scale(1)",   opacity: 1   },
        },
        scanLine: {
          "0%":   { transform: "translateY(-100%)" },
          "100%": { transform: "translateY(100vh)" },
        },
        borderFlow: {
          "0%,100%": { borderColor: "rgba(185,28,28,0.25)" },
          "50%":     { borderColor: "rgba(220,38,38,0.55)" },
        },
      },
      boxShadow: {
        "glow-red":  "0 0 30px -4px rgba(220,38,38,0.25)",
        "glow-red-lg":"0 0 60px -8px rgba(220,38,38,0.30)",
        "panel":     "0 4px 32px -4px rgba(0,0,0,0.6)",
        "inset-top": "inset 0 1px 0 rgba(255,255,255,0.05)",
      },
    },
  },
  plugins: [],
};
