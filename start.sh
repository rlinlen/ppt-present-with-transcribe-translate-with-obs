#!/bin/bash

cd "$(dirname "$0")"

if [ ! -f .env ]; then
    echo "Error: .env file not found!"
    echo "Please copy .env.example to .env and add your AWS credentials"
    exit 1
fi

source .venv/bin/activate
cd backend
python main.py
