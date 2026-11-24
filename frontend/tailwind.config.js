/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: { sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'], mono: ['JetBrains Mono', 'ui-monospace', 'monospace'] },
      colors: {
        navy: { 50: '#f1f5fb', 100: '#dde6f5', 200: '#b9c9e8', 300: '#8aa4d3', 400: '#5a7dba', 500: '#3b5e9c', 600: '#2d4a7f', 700: '#243b66', 800: '#1b2c4d', 900: '#0f1b36', 950: '#0a1226' },
        brand: { 50: '#eef2ff', 100: '#e0e7ff', 200: '#c7d2fe', 300: '#a5b4fc', 400: '#818cf8', 500: '#6366f1', 600: '#4f46e5', 700: '#4338ca', 800: '#3730a3', 900: '#312e81' },
      },
      boxShadow: { card: '0 1px 2px rgba(15,27,54,.06), 0 4px 16px rgba(15,27,54,.06)' },
    },
  },
  plugins: [],
}
