#!/bin/bash

echo Creating DT...

if [ ! -d "turtlebot-DT-venv" ]; then 
echo Create virtual environment
python3 -m venv turtlebot-DT-venv
else
echo Python virtual environment already created
fi

source turtlebot-DT-venv/bin/activate

echo Installing requirements
python -m pip install --upgrade pip
pip install pika
pip install pandas
pip install sklearn-pandas

echo Give correct permissions to scripts
chmod +x analyze.sh   
chmod +x execute.sh   
chmod +x evolve.sh    

echo Run DT

./execute.sh #& ./analyze.sh & ./evolve.sh