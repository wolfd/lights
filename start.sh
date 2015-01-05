#!/bin/bash

echo Killing running LED control script

pkill -15 ledcontrol.py
pkill -9 projectM-pulseaudio

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo Starting LED control script

nohup "$DIR/ledcontrol.py" >"$DIR/out.log" 2>"$DIR/err.log" &

echo Starting fadey visualizer

errcode=50
while [ $errcode != 0 ]; do
    wget -O /dev/null 'http://localhost:8080/lights/pattern/run_pattern?name=fadey' >"$DIR/wget.log" 2>"$DIR/wget.err"
    errcode=$?
done

echo Done
