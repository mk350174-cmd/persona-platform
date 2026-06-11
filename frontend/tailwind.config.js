/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Material Design 3 - Primary
        "primary-fixed-dim": "#c3c0ff",
        "primary-fixed": "#e2dfff",
        "primary-container": "#4f46e5",
        "primary": "#c3c0ff",
        "on-primary": "#1d00a5",
        "on-primary-fixed": "#0f0069",
        "on-primary-fixed-variant": "#3323cc",
        "on-primary-container": "#dad7ff",

        // Material Design 3 - Secondary
        "secondary-fixed": "#eaddff",
        "secondary-fixed-dim": "#d2bbff",
        "secondary-container": "#6001d1",
        "secondary": "#d2bbff",
        "on-secondary": "#3f008e",
        "on-secondary-fixed": "#25005a",
        "on-secondary-fixed-variant": "#5a00c6",
        "on-secondary-container": "#c9aeff",

        // Material Design 3 - Tertiary
        "tertiary-fixed": "#acedff",
        "tertiary-fixed-dim": "#4cd7f6",
        "tertiary-container": "#006a7c",
        "tertiary": "#4cd7f6",
        "on-tertiary": "#003640",
        "on-tertiary-fixed": "#001f26",
        "on-tertiary-fixed-variant": "#004e5c",
        "on-tertiary-container": "#93e8ff",

        // Material Design 3 - Error
        "error": "#ffb4ab",
        "error-container": "#93000a",
        "on-error": "#690005",
        "on-error-container": "#ffdad6",

        // Material Design 3 - Surface & Background
        "background": "#12121d",
        "surface": "#12121d",
        "surface-dim": "#12121d",
        "surface-bright": "#383845",
        "surface-container-lowest": "#0d0d18",
        "surface-container-low": "#1b1a26",
        "surface-container": "#1f1e2a",
        "surface-container-high": "#292935",
        "surface-container-highest": "#343440",
        "surface-tint": "#c3c0ff",
        "surface-variant": "#343440",
        "on-surface": "#e3e0f1",
        "on-surface-variant": "#c7c4d8",

        // Material Design 3 - Inverse
        "inverse-surface": "#e3e0f1",
        "inverse-primary": "#4d44e3",
        "inverse-on-surface": "#302f3b",

        // Material Design 3 - Outline
        "outline": "#918fa1",
        "outline-variant": "#464555",

        // Custom domain colors
        "philosophy-purple": "#8b5cf6",
        "science-cyan": "#06b6d4",
        "ethics-blue": "#3b82f6",
        "leadership-gold": "#f59e0b",
        "arts-orange": "#f97316",
        "literature-green": "#34d399",
        "fiction-pink": "#ec4899",
        "mythology-lilac": "#a78bfa",
        "power-red": "#ef4444",

        // Utility colors
        "border-glass": "rgba(255, 255, 255, 0.08)",
        "surface-glass": "rgba(26, 26, 46, 0.6)",
      },
      borderRadius: {
        "DEFAULT": "0.25rem",
        "lg": "0.5rem",
        "xl": "0.75rem",
        "full": "9999px",
      },
      spacing: {
        "margin-desktop": "40px",
        "unit": "8px",
        "gutter": "24px",
        "margin-mobile": "16px",
        "container-max": "1280px",
      },
      fontFamily: {
        "body-md": ["Inter", "sans-serif"],
        "display-lg-mobile": ["Geist", "sans-serif"],
        "body-lg": ["Inter", "sans-serif"],
        "label-caps": ["Geist", "sans-serif"],
        "headline-md": ["Geist", "sans-serif"],
        "mono-data": ["Geist", "monospace"],
        "display-lg": ["Geist", "sans-serif"],
      },
      fontSize: {
        "body-md": ["16px", { lineHeight: "1.5", fontWeight: "400" }],
        "display-lg-mobile": ["32px", { lineHeight: "1.2", fontWeight: "700" }],
        "body-lg": ["18px", { lineHeight: "1.6", fontWeight: "400" }],
        "label-caps": ["12px", { lineHeight: "1.0", letterSpacing: "0.1em", fontWeight: "600" }],
        "headline-md": ["24px", { lineHeight: "1.3", fontWeight: "600" }],
        "mono-data": ["14px", { lineHeight: "1.4", letterSpacing: "-0.01em", fontWeight: "500" }],
        "display-lg": ["48px", { lineHeight: "1.1", letterSpacing: "-0.02em", fontWeight: "700" }],
      },
    },
  },
  plugins: [],
  darkMode: "class",
}
