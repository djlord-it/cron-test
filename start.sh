#!/bin/bash

# Start EasyCron in background
DATABASE_URL="postgres://localhost/easycron?sslmode=disable" ./easycron serve &
EASYCRON_PID=$!

# Wait for EasyCron to be ready
sleep 2

# Start Crypto Tracker
python -m crypto_tracker serve

# Cleanup on exit
kill $EASYCRON_PID 2>/dev/null
