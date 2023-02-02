/** @type {import('tailwindcss').Config} */
module.exports = {
    content: ["./tech/**/*.{j2,js}"],
    theme: {
        extend: {
            fontFamily: {sans: ['Inter var']},
        },
    },
    plugins: [
        require('tailwindcss'),
        require('autoprefixer'),
        require('@tailwindcss/forms'),
        require('@tailwindcss/line-clamp'),
        require('@tailwindcss/aspect-ratio'),
    ],
}
