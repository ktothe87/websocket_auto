#!/bin/bash

# 오늘 날짜 설정
today=$(date +%Y%m%d)

# 코인 배열 생성
if [ $# -eq 0 ]; then
#    coins=("blast" )
    coins=("xrp" "blast" "btg" "pol")
else
    coins=("$1")
fi

if [ $# -eq 2 ]; then
    memid="$2"
else
    memid="1"
fi

# 배열을 반복하여 명령 실행
for coin in "${coins[@]}"
do
#    nohup python3 server_auto_${coin}.py 2>&1 >> csv/auto_${today}_${coin}.csv &
#     nohup python3 server_auto_${coin}.py  >> csv/auto_${today}_${coin}.csv &

    nohup python3 -u websocket_auto.py ${coin} ${memid} >> csv/auto_${today}_${coin}.log 2>&1 &
    # 잠시 대기 (프로세스 시작을 위해)
    sleep 2
    
    # 프로세스 찾기
    # 'grep' 명령어의 출력에서 'grep' 자체의 프로세스를 제외하기 위해 'grep -v grep'을 사용합니다.
    # 'awk'를 사용하여 프로세스 번호(PID)만을 추출합니다.
    pid=$(ps aux | grep "[p]ython3 -u websocket_auto.py ${coin}" | awk '{print $2}')
    
    # 찾은 PID와 명령어 출력
    if [ ! -z "$pid" ]; then
        echo "PID: $pid, nohup python3 -u websocket_auto.py ${coin} 2>&1 >> csv/auto_${today}_${coin}.log 2>&1 &"
    else
        echo "해당 프로세스를 찾을 수 없습니다."
    fi
done

