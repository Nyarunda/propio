/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  presets: [require('frappe-ui/tailwind').default],
  content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        propio: {
          50: '#e8f0f8',
          100: '#c5d9ed',
          200: '#9ebfdf',
          300: '#77a5d1',
          400: '#5790c6',
          500: '#1a4d8c',
          600: '#15407a',
          700: '#0f2f5c',
          800: '#0a1f3d',
          900: '#050f1f'
        }
      }
    }
  },
  plugins: []
}
