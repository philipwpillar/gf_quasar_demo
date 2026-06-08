/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        surface: {
          DEFAULT: "#f8fafc",
          card: "#ffffff",
          muted: "#f1f5f9",
          inset: "#f8fafc",
        },
        ink: {
          DEFAULT: "#0f172a",
          secondary: "#475569",
          muted: "#64748b",
          faint: "#94a3b8",
        },
        line: {
          DEFAULT: "#e2e8f0",
          strong: "#cbd5e1",
        },
        brand: {
          DEFAULT: "#0b3d6a",
        },
        accent: {
          DEFAULT: "#2563eb",
          hover: "#1d4ed8",
          subtle: "#eff6ff",
        },
        trust: {
          ok: {
            bg: "#ecfdf5",
            border: "#10b981",
            text: "#047857",
          },
          warn: {
            bg: "#fffbeb",
            border: "#f59e0b",
            text: "#b45309",
          },
          fail: {
            bg: "#fef2f2",
            border: "#ef4444",
            text: "#b91c1c",
          },
          neutral: {
            bg: "#f1f5f9",
            border: "#cbd5e1",
            text: "#475569",
          },
        },
      },
      boxShadow: {
        card: "0 1px 3px 0 rgb(15 23 42 / 0.06), 0 1px 2px -1px rgb(15 23 42 / 0.06)",
        elevated:
          "0 10px 15px -3px rgb(15 23 42 / 0.08), 0 4px 6px -4px rgb(15 23 42 / 0.06)",
      },
      spacing: {
        "shell-sidebar": "15rem",
        "shell-app-bar": "4rem",
      },
    },
  },
  plugins: [],
};
