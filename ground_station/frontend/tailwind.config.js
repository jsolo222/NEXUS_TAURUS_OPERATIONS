/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // NASA-inspired color palette
        'nasa-blue': '#0B3D91',
        'nasa-red': '#FC3D21',
        'space-black': '#0a0a0f',
        'panel-dark': '#12121a',
        'panel-border': '#2a2a3a',
        'text-primary': '#e0e0e0',
        'text-secondary': '#8888aa',
        'status-green': '#00ff88',
        'status-yellow': '#ffcc00',
        'status-red': '#ff4444',
      },
      fontFamily: {
        'mono': ['JetBrains Mono', 'Consolas', 'monospace'],
      },
    },
  },
  plugins: [],
}
