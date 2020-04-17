#!/bin/bash
while true; do
  python3 main.py
  sleep 259200
  kill -9 $(cat pid)
done;