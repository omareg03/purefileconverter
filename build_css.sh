#!/bin/bash
# Install the standalone tailwind CLI or use npx if Node.js is installed.
# We use npx here as it is standard. Ensure you have Node installed.
echo "Building Tailwind CSS..."
npx tailwindcss -i ./input.css -o ./static/tailwind.css --minify
echo "Done! The file is in ./static/tailwind.css"
