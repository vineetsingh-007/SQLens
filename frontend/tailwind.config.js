/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#f0f7ff',
          100: '#e0effe',
          500: '#0284c7',
          600: '#0265d2',
          700: '#0369a1',
          900: '#0c4a6e',
        },
        slate: {
          850: '#1e293b',
          950: '#090d16'
        }
      }
    },
  },
  plugins: [],
}
