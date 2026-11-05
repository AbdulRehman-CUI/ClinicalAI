/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        clinical: {
          navy: "var(--navy)",
          teal: "var(--teal)",
          cyan: "var(--cyan)",
          background: "var(--background)",
          muted: "var(--muted)",
          border: "var(--border)",
        },
      },
      fontFamily: { sans: ["Inter", "Segoe UI", "Arial", "sans-serif"] },
      boxShadow: { panel: "var(--shadow-panel)" },
      borderRadius: { panel: "var(--radius-panel)" },
    },
  },
  plugins: [],
};
