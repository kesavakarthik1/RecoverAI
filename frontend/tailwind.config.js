/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50:  '#f0f4ff',
          100: '#e0eaff',
          200: '#c7d7fd',
          300: '#a5b9fc',
          400: '#8193f9',
          500: '#6470f3',
          600: '#4f52e7',
          700: '#4240cc',
          800: '#3635a5',
          900: '#302f82',
          950: '#1e1d4e',
        },
        success: { light: '#d1fae5', DEFAULT: '#10b981', dark: '#065f46' },
        warning: { light: '#fef3c7', DEFAULT: '#f59e0b', dark: '#92400e' },
        danger:  { light: '#fee2e2', DEFAULT: '#ef4444', dark: '#7f1d1d' },
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
      },
    },
  },
  plugins: [],
}
