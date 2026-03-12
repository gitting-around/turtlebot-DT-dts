#!/bin/bash

echo "[EXECUTE] Running monitor for the turtlebot"

rm -f ../../../data/turtlebot-DT/*_data.csv
python ../../../tools/turtlebot-DT/tb-monitor.py

