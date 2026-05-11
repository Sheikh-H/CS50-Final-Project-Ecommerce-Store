/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./templates/**/*.html", "./**/*.html"],
  theme: {
    extend: {},
  },
  plugins: [],
};

// This is used to ensure that all files inside templates folder with the .html extension has the tailwind css intellisense enabled.
