@echo off
echo Building Tailwind CSS...
npx tailwindcss -i ./input.css -o ./static/tailwind.css --minify
echo Done! The file is in ./static/tailwind.css
