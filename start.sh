#!/usr/bin/env bash

echo "Starting health service"
pipenv run python -O src/health.py &
echo "Starting bot"
pipenv run python -O src/dragonbot.py &

wait
