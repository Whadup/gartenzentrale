#!/usr/bin/env bash

_term() { 
  echo "Caught SIGTERM signal!" 
  kill -TERM "$child" 2>/dev/null
}
trap _term SIGTERM
while true
do
    echo "(Re-)Starting Garten Server"
    python3 gartenzentrale.py&
    child=$!
    wait "$child"
	sleep 1
done
