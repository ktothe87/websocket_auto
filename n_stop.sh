#!/bin/bash

# 코인 배열 생성
if [ $# -eq 0 ]; then
    coins=("xrp" "pol" "blast" "btg")
else
    coins=("$1")
fi

# 배열을 반복하여 해당하는 파이썬 프로세스를 찾아 종료
for coin in "${coins[@]}"
do
    # pgrep으로 프로세스 ID를 찾고, 해당 ID를 kill 명령으로 종료
    pids=$(ps aux | grep "[p]ython3 -u websocket_auto.py ${coin}" | awk '{print $2}')
    if [ ! -z "$pids" ]; then
        echo "Killing processes for ${coin}: $pids"
        kill $pids
    else
        echo "No running processes found for ${coin}"
    fi
done
