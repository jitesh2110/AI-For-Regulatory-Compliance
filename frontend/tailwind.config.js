/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        cyber: {
          dark: '#0b0f19',
          panel: '#151b2b',
          border: '#2a3143',
          accent: '#3b82f6',
          glow: '#8b5cf6',
          success: '#10b981'
        }
      }
    },
  },
  plugins: [],
}
