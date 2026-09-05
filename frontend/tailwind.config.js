/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        cream: {
          50: '#FFFDF9',
          100: '#FFF8F0',
          200: '#FDF0E0',
        },
        brand: {
          green: {
            50: '#F0FDF4',
            500: '#22C55E',
            600: '#16A34A',
            700: '#15803D',
          },
          orange: {
            50: '#FFF7ED',
            500: '#F97316',
            600: '#EA580C',
            700: '#C2410C',
          },
          dark: '#1F2937',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
      boxShadow: {
        soft: '0 4px 20px -2px rgba(234, 88, 12, 0.08)',
        card: '0 2px 12px 0 rgba(0, 0, 0, 0.04)',
      }
    },
  },
  plugins: [],
}
