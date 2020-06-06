#!/usr/bin/env bash
while true
do
	echo "(Re-)Starting Garten Server"
    python3 -m gartenzentrale.gartenzentrale
	sleep 1
done