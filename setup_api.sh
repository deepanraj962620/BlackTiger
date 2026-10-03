#!/usr/bin/env bash
set -e
if [ -f ".env" ]; then
  echo ".env already exists."
  exit 0
fi
cp .env.example .env
echo "Created .env"
echo "Open it with: nano .env"
echo 'Then replace PASTE_YOUR_NEW_GROQ_API_KEY_HERE with your NEW Groq API key.'
