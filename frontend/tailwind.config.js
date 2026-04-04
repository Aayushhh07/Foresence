/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        forest: {
          50: '#f0fdf4',
          100: '#dcfce7',
          200: '#bbf7d0',
          300: '#86efac',
          400: '#4ade80',
          500: '#22c55e',
          600: '#16a34a',
          700: '#15803d',
          800: '#166534',
          900: '#14532d',
        },
        sidebar: '#0f172a',
        severity: {
          critical: '#dc2626',
          high: '#ea580c',
          medium: '#d97706',
          low: '#2563eb',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-in-out',
        'slide-in': 'slideIn 0.3s ease-out',
        'pulse-green': 'pulseGreen 2s infinite',
      },
      keyframes: {
        fadeIn: { from: { opacity: 0 }, to: { opacity: 1 } },
        slideIn: { from: { transform: 'translateY(-8px)', opacity: 0 }, to: { transform: 'translateY(0)', opacity: 1 } },
        pulseGreen: { '0%, 100%': { boxShadow: '0 0 0 0 rgba(22, 163, 74, 0.4)' }, '50%': { boxShadow: '0 0 0 8px rgba(22, 163, 74, 0)' } },
      }
    },
  },
  plugins: [],
}
