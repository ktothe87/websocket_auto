import sys
import json
import time
import threading
from datetime import datetime
from marketApi import *
from wsPrivateClass import *
from MyThreadManager import *
from wsClass import *
from MyApi import *
import copy
import asyncio
import uvloop
import signal
from decimal import Decimal, ROUND_DOWN



if len(sys.argv) < 2:
    log_str = f"error no input coinName program exit 3 "
    print(log_str)
    sys.exit(1)
elif len(sys.argv) < 3:
    memid = 1
else:
    memid = int(sys.argv[2])

maxThread = 5
spairThread = 2

coin = sys.argv[1].upper()
coin_code ="KRW-"+ coin

myApi = MyApi(coin.lower(), memid) # 일반과퀵모드 여분쓰레드가 기본2개 있으니  쓰레드1개 사용 시 3으로 넣어야 함.
coin_settings = myApi.settings

market_event = {'bit':False,'up':False}
current_market = ""
r_current_market = ""

up_coinList = {'ADA', 'ALGO', 'BLUR', 'CELO', 'ELF', 'EOS', 'GRS', 'GRT', 'ICX', 'MANA', 'MINA', 'POL', 'SAND', 'SEI', 'STG', 'TRX'}

bit_api = marketApiClass(coin_code, 'bit',myApi.userinfo.b_key, myApi.userinfo.b_skey);
up_api = marketApiClass(coin_code, 'up',myApi.userinfo.u_key, myApi.userinfo.u_skey);
myThreadManager = MyThreadManager(maxThread + spairThread)

#order_id1 = thread_manager.create_thread(escapeCheck, "order1", "market1", "order1", "BTC")
#thread_manager.shutdown()

marketApi = {'bit': bit_api,'up': up_api}


RealTime_coin = myApi.coinSet
tmp_RealTime_coin = MyApi.CoinSet()

               
def getBalance(market):    
    while(True):
        res = marketApi[market].getBalance()
        if res.success:
            # 성공적인 응답 처리
            response = res.data
        else:
            # 에러 처리
            program_shutdown(res.error)
        
        #print(f'market:{market}. {result.json()}:{result.json()}')
        if len(response.json()[0]) > 0:   
            RealTime_coin[market]['coin_amount'] = 0
            for item in response.json():
                if item['currency'] == coin:
                    RealTime_coin[market]['coin_amount'] =changeDecimal(item['balance'],2)
                elif item['currency'] =='KRW':
                    RealTime_coin[market]['krw_price'] = changeDecimal(item['balance'],2)
            
            break;

def getBothBalance():
    getBalance('bit')
    getBalance('up')


completed_units = 0
time_diff = 0



######min_units_price = 10 #업비트는 최소단위가 5천원이고 현재 이코인 값이 대략 50,60원대라서.
min_units_price = 0 #업비트는 최소단위가 5천원이고 현재 이코인 값이 대략 50,60원대라서.

bit_ws_class = None
up_ws_class = None

def program_shutdown(log_str=""):
    log_str += f"로 인한 프로그램 종료 시작 [{myThreadManager.active_thread_count}/{myThreadManager.max_threads}]"
    print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}]{log_str}")

    myThreadManager.shutdown()

    bit_ws_class.stop()
    up_ws_class.stop()
    bitCheckMyOrder_Class.stop()
    upCheckMyOrder_Class.stop()
    #log_str = f"프로그램종료를 위한 쓰레드종료 완료.[{myThreadManager.active_thread_count}/{myThreadManager.max_threads}]"
    myApi.insertLog(log_str,-1,"error")
    print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}]{log_str}")
    print("kill에 의한 종료")
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    asyncio.run(myApi.error_message(0,RealTime_coin,myApi.err_log_str))
    sys.exit(1)


def signal_handler(sig,frame):
    program_shutdown("kill")


signal.signal(signal.SIGINT,signal_handler)
signal.signal(signal.SIGTERM,signal_handler)



# def changeDecimal(value, count):
#     if type(value) == str:
#         try:
#             value = float(value)
#         except ValueError:
#             value = 0  # 문자열을 float으로 변환할 수 없는 경우
#     elif value is None:
#         value = 0
        
#     value = round(value,9)

#     return (int(value * 10**count) / 10**count)   

def changeDecimal(value, count):
    if isinstance(value, str):
        try:
            value = Decimal(value)
        except ValueError:
            value = Decimal('0')
    elif value is None:
        value = Decimal('0')
    elif isinstance(value, (int, float)):
        value = Decimal(str(value))
    elif not isinstance(value, Decimal):
        raise TypeError("Unsupported type for value")

    quantizer = Decimal('1.' + '0' * count)
    result =  value.quantize(Decimal('1.' + '0' * count), rounding=ROUND_DOWN)
    return result.normalize()


def SellToMarket(market, bought_order_id, thread_id, cp_trade_info):
    market_str = {'bit':"빗썸",'up': "업빗"}
    if market == 'bit':
        r_market = 'up'
    else:
        r_market = 'bit'

    bought_amount = cp_trade_info.bought_amount

    # 업비트 판매루틴 
    ####################33 여기 루프 걸어야하지 않나? 역방향에서는 했는데.     
    
    log_str = f"[{thread_id}]{market_str[market]}매도신청:{cp_trade_info.sell_price}, bought_amount:{bought_amount}, 매수:{bought_order_id} ,{market}_coin_amount:{RealTime_coin[market]['coin_amount']}"
    myApi.insertLog(log_str,thread_id, f"{market_str[market]}매도신청")
    
    res = marketApi[market].sell(thread_id,bought_amount)
    if res.success:
        # 성공적인 응답 처리
        response = res.data
    else:
        # 에러 처리
        program_shutdown(res.error)
    
    if response.status_code == 429:
        # 어차피 메시지 회답 받은 시점에서 시간이 꽤 지났을테니까 없어도 될거 같아서 0.1초 대기하는거 뺌
        while(True):
            log_str = f"[{thread_id}]{market_str[market]}에 과다요청으로 인한 에러 발생. 다시 매도신청. 강제로 0.1초 대기"
            myApi.insertLog(log_str,thread_id,"error")
            res = marketApi[market].sell(bought_amount)
            if res.success:
                # 성공적인 응답 처리
                response = res.data
            else:
                # 에러 처리
                program_shutdown(res.error)
           

            log_str = f"[{thread_id}]{market_str[market]} 재매도 결과 response.status_code:{response.status_code}, response:{response.json()}" 
            myApi.insertLog(log_str,thread_id,"error")
            if response.status_code == 201:
                break;
            else:
                if response.status_code == 429:
                    log_str = f"[{thread_id}]{market_str[market]} 또 과다요청이라 0.1초 강제 대기" 
                    myApi.insertLog(log_str,thread_id,"error")
                    time.sleep(0.1)
                else:
                    log_str = f"[{thread_id}]{market_str[market]} error SellToMarket program exit 00 매수금액:{cp_trade_info.buy_price}, 매수량:{bought_amount}"
                    myApi.insertLog(log_str,thread_id,"exit")
                    
                    myApi.err_log_str = f"매수금액:{cp_trade_info.buy_price}, 매수량:{bought_amount}\n [{thread_id}]{market_str[market]} SellToMarket program exit 00"
                    myThreadManager.program_run = False


    elif response.status_code != 201:
        log_str = f"[{thread_id}]{market_str[market]} error SellToMarket sell response.status_code:{response.status_code}, response:{response.json()}" 
        myApi.insertLog(log_str,thread_id,"error")
        # 뭔가의 이유로 못 팔았다는건데.
        # 코인 갯수가 적거나, 금액이 문제거나, 에러
        # 경우에 따라서 여기서 샀을 때 금액이랑 팔아야하는 갯수 남겨놓고 루틴 끝나고
        # 별도로 남은 부분만 금액애 맞춰서 팔게끔 해도 될 듯.
        # 업빗에 판매수량을 잘못해도 400 나오네. 소수점 5자리였어서 나는 4자리까지만 체크하니까 0개를 팔려고 해서 에러났었음.
        if response.status_code == 400:
            #{'message': '주문가능한 금액(PYTH)이 부족합니다.', 'name': 'insufficient_funds_ask'}
            getBalance('bit')
            getBalance('up')
            log_str = f"[{thread_id}]{market_str[market]}에 내 코인이 부족해서 매도 실패. {market_str[market]}양:{RealTime_coin[market]['coin_amount']}, 매수금액:{cp_trade_info.buy_price},매수량:{bought_amount}、  {market}보유코인:{RealTime_coin[market]['coin_amount']},{market}보유현금:{RealTime_coin[market]['krw_price']}, {r_market}보유코인:{RealTime_coin[r_market]['coin_amount']},{r_market}보유현금:{RealTime_coin[r_market]['krw_price']}"
            myApi.insertLog(log_str,thread_id,"error")
            
        # 요청을 너무 많이 보내면 나옴. 이건 그냥 잠깐 대기하고 다시 보내면 될거 같은데.

        # 판매수량이 너무 작은 경우 무시하고 그 외에는 종료.
        if bought_amount > 0.001 :
            log_str = f"[{thread_id}]{market_str[market]} error SellToMarket program exit 0 매수금액:{cp_trade_info.buy_price}, 매수량:{bought_amount}"
            myApi.insertLog(log_str,thread_id,"exit")

            myApi.err_log_str = f"매수금액:{cp_trade_info.buy_price}, 매수량:{bought_amount}\n [{thread_id}]{market_str[market]} error SellToMarket program exit 0"
            myThreadManager.program_run = False
        
        ########## 판매 자체에 실패한 경우니까 다시 팔아야하는데. 
        ########## 잘못하면 계속 팔게 되버릴거라 좀 걱정이네. 여길 어떻게 해야할까
        ########## 구매시에 잘 체크했으면 문제 없었을건데 
        ########## 팔 때 문제가 되는건 코인이 부족한 경우뿐인거 같은데. 
        ########## 전에 수정했던 부분판매 했을 때, 성공한 만큼이 아닌 처음 계산했던 양을 팔려 했을 때 문제가 된적은 있음.    

    else :
        result = response.json()
        order_id = result['uuid'] 
        # 매도쪽 오더 아이디로 매칭시킬꺼라 꼭 여기서 넣어야 함.
        # 오더 받는 쓰레드로 가져가면 매수쪽 오더아이디로 들어갈거라 매도 오더 왔을 때 죽음
        cp_trade_info.sell_amount = bought_amount
        cp_trade_info.sell_remaining_amount = bought_amount        
        myThreadManager.trade_list[order_id] = cp_trade_info
        
        print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}][{thread_id}]{market} 555555555555555 매도신청 완료 ({order_id}),{result}")
        #log_str = f"[{thread_id}]{market_str[market]}매도신청 완료:{cp_trade_info.buy_price}, units:{units}, order:{order_id}, {market}_coin_amount:{RealTime_coin[market]['coin_amount']}"
        log_str = f"[{thread_id}]{market_str[market]}매도신청 완료, 매수:{bought_order_id} 매도:{order_id}, 매도량:{bought_amount}, {result}"
        #print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}]{log_str}")
        myApi.insertLog(log_str,thread_id,f"{market_str[market]}매도신청 완료")
        

def compare_and_update_coinset(original: MyApi.CoinSet, new_data: MyApi.CoinSet):
    changed = False
    for market in ['bit', 'up']:
        for key in ['buy', 'sell', 'buy_amount', 'sell_amount']:
            if original[market][key] != new_data[market][key]:
                original[market][key] = new_data[market][key]
                changed = True
    return changed

def orderbook_message(ws,message, market):

    if market =='up':
        r_market ='bit'
    else:
        r_market ='up'
    orderbook = json.loads(message)

    item=orderbook
    try:
        if item.get("error"):
            log_str = f"{market} error orderbook_messag item:{item}"
            myApi.insertLog(log_str,-1,"error")

        elif item.get("code") == coin_code :  # Check if the market is in the coins list
            
            if RealTime_coin[market]['buy'][0] != changeDecimal(item['orderbook_units'][0]['bid_price'],2) or RealTime_coin[market]['buy'][1] != changeDecimal(item['orderbook_units'][1]['bid_price'],2)  or RealTime_coin[market]['buy_amount'][0] != changeDecimal(item['orderbook_units'][0]['bid_size'],8) or RealTime_coin[market]['buy_amount'][1] != changeDecimal(item['orderbook_units'][1]['bid_size'],8) or RealTime_coin[market]['sell'][0] != changeDecimal(item['orderbook_units'][0]['ask_price'],2) or RealTime_coin[market]['sell_amount'][0] != changeDecimal(item['orderbook_units'][0]['ask_size'],8) and changeDecimal(item['orderbook_units'][0]['bid_size'],8) > 0:
                RealTime_coin.coin = coin.lower()
                RealTime_coin[market]['ori_buy'] = item['orderbook_units'][0]['bid_price']
                for i in range(5):  # 0부터 4까지 반복
                    RealTime_coin[market]['buy'][i] = changeDecimal(item['orderbook_units'][i]['bid_price'], 2)
                    RealTime_coin[market]['buy_amount'][i] = changeDecimal(item['orderbook_units'][i]['bid_size'], 8)
                    RealTime_coin[market]['sell'][i] = changeDecimal(item['orderbook_units'][i]['ask_price'], 2)
                    RealTime_coin[market]['sell_amount'][i] = changeDecimal(item['orderbook_units'][i]['ask_size'], 8)
                
                RealTime_coin.BitToUp_diff = changeDecimal(RealTime_coin['up']['buy'][0] - RealTime_coin['bit']['buy'][0], 3)
                RealTime_coin.UpToBit_diff = changeDecimal(RealTime_coin['bit']['buy'][0] - RealTime_coin['up']['buy'][0], 3)
                RealTime_coin.BitToUp_fee = changeDecimal( (RealTime_coin['up']['buy'][0] * coin_settings.up_fee) + (RealTime_coin['bit']['sell'][0] * coin_settings.bit_fee), 3)
                RealTime_coin.UpToBit_fee = changeDecimal( (RealTime_coin['bit']['buy'][0] * coin_settings.bit_fee) + (RealTime_coin['up']['sell'][0] * coin_settings.up_fee) ,3)
                coin_settings.BitToUp_comp_money_risk = changeDecimal(RealTime_coin['bit']['buy'][0] * coin_settings.BitToUp_comp_money_risk_rate ,3)
                coin_settings.UpToBit_comp_money_risk = changeDecimal(RealTime_coin['up']['buy'][0] * coin_settings.UpToBit_comp_money_risk_rate,3)

                market_event[market] = True
                myThreadManager.orderbook_event.set()

                log_str = f"[{myThreadManager.active_thread_count}/{myThreadManager.max_threads}]{market},{RealTime_coin.coin},{RealTime_coin['bit']['buy'][0]}, {RealTime_coin['up']['buy'][0]}, {RealTime_coin['bit']['buy_amount'][0]}, {RealTime_coin['up']['buy_amount'][0]}, {RealTime_coin.BitToUp_fee}, ||  ,{RealTime_coin.BitToUp_diff}({RealTime_coin.BitToUp_diff2}),   ,{RealTime_coin.UpToBit_diff}({RealTime_coin.UpToBit_diff2}), || , {RealTime_coin['bit']['buy'][1]},{RealTime_coin['bit']['buy_amount'][1]}, {RealTime_coin['up']['buy'][1]}, {RealTime_coin['up']['buy_amount'][1]}, total:{changeDecimal(RealTime_coin['bit']['coin_amount']+RealTime_coin['up']['coin_amount'],8)}, bit:{changeDecimal(RealTime_coin['bit']['coin_amount'],8)}, {'up'}:{changeDecimal(RealTime_coin['up']['coin_amount'],8)}, kwr:{changeDecimal(RealTime_coin['bit']['krw_price']+RealTime_coin['up']['krw_price'],2)}, bit:{int(RealTime_coin['bit']['krw_price'])}, up:{int(RealTime_coin['up']['krw_price'])}, BitToUp:{coin_settings.BitToUp_comp_money_risk}, UpToBit:{coin_settings.UpToBit_comp_money_risk}"
                myApi.insertLog(log_str)
            
        elif item.get('status'): 
            #log_str = f"{market} orderbook :{item}"
            #myApi.insertLog(log_str,-1,'status')
            ws_msg = "PING"
            ws.send(ws_msg)
        else:
            log_str = f"{market} error orderbook_message, up socket start status else item:{item}"
            myApi.insertLog(log_str,-1,"error")
            

    except TypeError as e:
            log_str = f"{market} error orderbook_message, TypeError e:{e}"
            myApi.insertLog(log_str,-1,"error")

bit_ws_class = wsClass(coin,'bit',orderbook_message)
bit_ws_class.start()

up_ws_class = wsClass(coin,'up',orderbook_message)
up_ws_class.start()



current_time = datetime(1,1,1, second=0)
send_time =  datetime(1,1,1, second=0)

def escapeCheck(market, thread_id, order_id, stop_event):

    market_str = {'bit':"빗썸",'up': "업빗"}
    r_market_str = {'bit':"업빗",'up': "업빗"}

    # 매수 상태를 체크.

    if market =='up':
        r_market ='bit'
    else:
        r_market ='up'

    trade_info = myThreadManager.get_trade(order_id)
    
    while(True) :
       
        myThreadManager.orderbook_event.wait()
        myThreadManager.orderbook_event.clear()

        goExit = False
        log_str = ""
        buy2_thread_id = 0

        if not stop_event.is_set() :
            # 이거 여기다 안하면 프로그램 종료되었을 때 다음 시세데이터가 올 때까지 기다리게 됨.
            # 보통은 금방 시세가 오니까 상관없는데 가끔 늦을 때가 있음
            if not myThreadManager.program_run:
                log_str = f"{market_str[market]} 프로그램 종료로 인한 탈출"
                myThreadManager.orderbook_event.set()
                myApi.insertLog(log_str,thread_id, f"error")
                # 브레이크로 빠져나가면 안됨. 쓰레드를 종료 시키지만, 매수취소는 하고 꺼야 하니까.
                goExit = True

            if not goExit:
                diff = changeDecimal(RealTime_coin[r_market]['buy'][0] - trade_info.buy_price,2)
                r_diff = RealTime_coin[r_market]['buy'][0] - RealTime_coin[r_market]['buy'][1]
                buy_amount = RealTime_coin[r_market]['buy_amount'][0] - myThreadManager.get_total_units(market,order_id)
                last_index = last_profitable_index( trade_info.buy_price, RealTime_coin[r_market]['buy'])
                buy2_thread_id = myThreadManager.get_buy2_last_thread(market, RealTime_coin[r_market]['buy'][0])

                if last_index < 0 :
                    if market =='up':
                        #역방향
                        log_str = f"차익 부족{diff}({coin_settings.UpToBit_comp_money_risk})"
                    else:
                        #정방향
                        log_str = f"차익 부족{diff}({coin_settings.BitToUp_comp_money_risk})"
                    
                    goExit = True
            
                elif last_index == 0 and r_diff > gethighRiskValue(r_market):                    
                    # last_index가 0이라는건 매수1 이외의 매수호가는 차액을 만족하지 못한다는거
                    # 그 상태에서 매수1과 매수2의 차액이 크면 진입 안함.
                    log_str = f"{market_str[r_market]}쪽 마켓 매수1, 2 차이가 큼 {r_market}_매수1:{RealTime_coin[r_market]['buy'][0]}, {r_market}_매수2:{RealTime_coin[r_market]['buy'][1]}, {r_market}_매수 단위:{gethighRiskValue(r_market)}, r_diff:{r_diff}"
                else:
                    #업빗매수2과도 차익이 허용범위니까 물량을 포함해서 계산.
                    buy_amount += sum(RealTime_coin[r_market]['buy_amount'][1:last_index+1])

                ####### 매수신청량의 2배보다 떨어지면 빠져나오게 했었는데, 2배까진 필요 없을 듯
                ####### 내가 매수 성공하고 남은 거 보다도 적으면. 나올 생각인데. 너무 소량만 남으면 가격이 떨어진채로 갑자기 구매될 수도 있을거 같은데...
                ####### 미리 사둔게 없어서 안전하지만 그렇다고 미리 탈출을 안하면 그것도 조금은 손해가..?
                
                
                
                
                if trade_info is None :
                    stop_event.set()
                    print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}][{thread_id}]{market_str[market]}trade_info is None")
                # 매수2 마지막 쓰레드인데, 현재 매수신청한 양이 매도쪽 마켓에 남은 물량보다 적은 경우. 
                # 전체 쓰레드 중에서 내가 빠지는게 아니고, 매수2 들어있는 쓰레드 중에서 마지막 쓰레드가 빠짐.
                elif buy2_thread_id == trade_info.thread_id and RealTime_coin[r_market]['buy_amount'][0] < myThreadManager.get_total_units(market) :
                    log_str = f"매수2 마지막 쓰레드 취소"
                # 내가 매수신청해서 매수되고 남은 수량보다, 매수마켓쪽 수량이 더 적으면 수량부족이니까 탈출.
                elif buy_amount < trade_info.buy_remaining_amount:
                    # 내가 탈출해야 하는 상황이지만, 매수2에 들어있는 쓰레드가 있으면 그걸 먼저 탈출 시킴. 
                    # buy2_thread_id == 0 이라는건 매수2에 대기하고 있는 쓰레드가 없다는 것, 즉 내가 탈출해야 함.
                    if buy2_thread_id == 0:
                        log_str = f"최종적으로 수량 부족으로 탈출. {market_str[r_market]}매수2차익:{changeDecimal(RealTime_coin[r_market]['buy'][1] - trade_info.buy_price,2)}, BitToUp:{coin_settings.BitToUp_comp_money_risk}, UpToBit:{coin_settings.UpToBit_comp_money_risk}, 남은매수/신청매수:{trade_info.buy_remaining_amount}/{trade_info.buy_amount}, buy_amount:{buy_amount}, get_total_units:{myThreadManager.get_total_units(market, order_id)}, up_buy1_amount:{RealTime_coin[r_market]['buy_amount'][0]}, up_buy2_amount:{RealTime_coin[r_market]['buy_amount'][1]}, buy2_thread_id:{buy2_thread_id}"
                        goExit = True
                    else:
                        log_str = f"매수2에 대기하고 있는 쓰레드가 있어서 대신 탈출 안함. 매수2 쓰레드 탈출 되야 함. buy2_thread_id:{buy2_thread_id}"
                    
                elif (trade_info.buy_remaining_amount * RealTime_coin[r_market]['buy'][0]) < 6000:
                    log_str = f"매수하고 남은 양이 너무 적음. 매수되버리면 짜투리 됨 {trade_info.buy_remaining_amount}"
                    goExit = True


                if trade_info.buy_price < RealTime_coin[market]['buy'][1]:
                    log_str = f"{market_str[market]}매수3까지 내려옴. 매수금액({trade_info.buy_price}), 매수2({RealTime_coin[market]['buy'][1]})"
                    goExit = True 

                
                # # 원래는 내 업비트 물량이랑 계산이 맞아야 하는데, 안 맞는 경우가 생겼어서 임시로 추가함
                # # 대기 중에도 체크해서 코인이 부족해 보인다 싶으면 빠져나갈 것.
                # # 지금 이거 메인 쓰레드꺼 가져온건데. 왜 half로 계산하는거지?? 그래서 안 맞는건가??
                # compare_up_coin = RealTime_coin[r_market]['coin_amount'] - myThreadManager.get_total_units(market, order_id)
                # if(compare_up_coin < coin_settings.once_units) :
                #     log_str = f"{r_market_str[r_market]}쪽 내 코인 계산이 안 맞았던거 같음. 다른 쓰레드 신청양({myThreadManager.get_total_units(market, order_id)}), {r_market_str[r_market]}쪽 내 코인양:{RealTime_coin[r_market]['coin_amount']}"
                #     goExit = True


                if RealTime_coin[r_market]['coin_amount'] < (myThreadManager.get_total_units(market, order_id) + trade_info.buy_remaining_amount) :
                    log_str = f"{r_market_str[r_market]}쪽 내 코인 계산이 안 맞았던거 같음. 다른 쓰레드 신청양({myThreadManager.get_total_units(market, order_id)}), 매수미체결양:{trade_info.buy_remaining_amount}, {r_market_str[r_market]}쪽 내 코인양:{RealTime_coin[r_market]['coin_amount']}"
                    goExit = True
                
            # 위에서 확인한 조건에 의해 탈출하거나 업빗매수1 혹은 업빗매수1,2 의 물량이 내 요청물량의 2배가 안되면 탈출          
            if goExit :
                log_str = f"[{thread_id}]{market_str[market]}탈출신청({order_id}) mode:{trade_info.isChange}, {log_str}" 
                print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}]{log_str}")
                myApi.insertLog(log_str,thread_id, f"{market_str[market]}탈출신청")
                
                
                #startTime = time.time()
                res = marketApi[market].cancel(order_id)
                if not res.success:
                    # 에러 처리
                    program_shutdown(res.error)

                # 성공적인 응답 처리
                response = res.data

                try:
                    cancel_result = response.json()
                except json.JSONDecodeError as e:
                    log_str = f"[{thread_id}]{market_str[market]}error escapeCheck 탈출신청 결과의 데이터 피상 에러:{response.status_code}, order_id:{order_id}, {cancel_result}"
                    myApi.insertLog(log_str,thread_id,"error")
                    continue
                log_str = f"[{thread_id}]{market_str[market]}탈출신청결과({order_id}) status_code:{response.status_code} , {cancel_result}"
                print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}]{log_str}")
                myApi.insertLog(log_str,thread_id, f'{market_str[market]}탈출신청결과')

                #print(f"{market}탈출1 {response}")
                #print(f"{market}탈출2 {response.json()}")
                # 매수 신청시의 통신 자체의 응답이 제대로 안 왔으면 넘어감.
                
                if response.status_code == 200:
                    #print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}][{thread_id}]{market_str[market]}탈출완료({order_id})")
                    log_str = f'[{thread_id}]{market_str[market]}탈출신청완료'
                    myApi.insertLog(log_str,thread_id, f'{market_str[market]}탈출신청완료')
                elif response.status_code == 400:
                    ## 이미 체결된 주문  빗썸은 name, 업빗은 message로 옴
                    if cancel_result['error'].get('name') == 'done_order' or cancel_result['error'].get('message') == 'done_order':
                        log_str = f"[{thread_id}]{market_str[market]}error escapeCheck cancel fail(already bought), order_id:{order_id}, {cancel_result}"
                        myApi.insertLog(log_str,thread_id,"no_Order")
                    else:
                        log_str = f"[{thread_id}]{market_str[market]}error escapeCheck cancel request fail, order_id:{order_id}, {cancel_result}"
                        myApi.insertLog(log_str,thread_id,"error")
                elif response.status_code == 404:
                    log_str = f"[{thread_id}]{market_str[market]}주문을 찾지 못함:{order_id}, {cancel_result}"
                    myApi.insertLog(log_str,thread_id,"no_Order")
                else:  
                    log_str = f"[{thread_id}]{market_str[market]}error escapeCheck cancel status_code:{response.status_code}, order_id:{order_id}, {cancel_result}"
                    myApi.insertLog(log_str,thread_id,"error")

        if not myThreadManager.program_run or stop_event.is_set():
            #print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}]{market_str[market]}[{thread_id}][MyApi]쓰레드 종료")
            log_str = f"{market_str[market]} [{thread_id}][MyApi]쓰레드 종료"
            myApi.insertLog(log_str,thread_id, f"info")
            print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}]{log_str}")
            break
            
            
def parseMyOrder(ws,message,market):
    isOK = False
    isClear = False
    if market =='bit':
        r_market ='up'
    else:
        r_market ='bit'
    log_str = ""
    # 바이트 문자열을 일반 문자열로 디코딩
    decoded_message = message.decode("utf-8")
    
    # JSON 파싱
    parsed_data = json.loads(decoded_message)

    # 메시지 유형에 따라 처리
    if parsed_data.get('status') =='UP':
        #log_str = f"{market} CheckMyOrder Status: UP"
        #myApi.insertLog(log_str,-1,'status')   
        ws_msg = "PING"
        ws.send(ws_msg)
    
    elif parsed_data.get('type') =='myAsset':
        try:
            currency = parsed_data['assets'][0]['currency']
            if currency =='KRW':
                RealTime_coin[market]['krw_price'] = changeDecimal(parsed_data['assets'][0]['balance'],2) 
                #print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}]{market}:{RealTime_coin[market]['krw_price']}")
                #log_str = f"[{myThreadManager.active_thread_count}/{myThreadManager.max_threads}]{market}, 현금:{RealTime_coin[market]['krw_price']}"
                #myApi.insertLog(log_str)
                
            elif currency == coin:
                RealTime_coin[market]['coin_amount'] = changeDecimal(parsed_data['assets'][0]['balance'] , 2)        
                #print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}]{market}:{parsed_data}")
                #log_str = f"[{myThreadManager.active_thread_count}/{myThreadManager.max_threads}]{market}, {coin}:{RealTime_coin[market]['coin_amount'] }"
                #myApi.insertLog(log_str)
        except Exception as e: 
            print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}]myAsset error:{parsed_data}, e:{e}")

    
    elif parsed_data.get('type') == "myOrder":
        ask_bid = parsed_data['ask_bid']
        order_status = parsed_data["state"]
        order_id = parsed_data['uuid']
        completed_units = 0
       
        trade_info = myThreadManager.get_trade(order_id)
        if trade_info is None :
            log_str = f"[{market}]프로그램으로 신청한게 아닌거 같음. 확인 필요.{order_id}, {order_status}, {parsed_data}"
            #print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}]{log_str}")
            print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}]{log_str}")
            myApi.insertLog(log_str,-1,'error')
            
        else:
            thread_id = trade_info.thread_id

            log_str = f"[{thread_id}][{market}]({ask_bid}) 주문상태:{order_status}, {parsed_data}"
            myApi.insertLog(log_str,thread_id,"주문이력")
            print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}]{log_str}")

            try:
                if ask_bid =='BID' :    

                    # 빗썸은 부분매수 후의 마지막 부분매수는 완료로 옴. 업빗은 따로 완료가 한번 더 옴.
                    # 한번에 다 사져도 executed_volume, volume 이 같으니까 무조건 executed_volume 이걸로.
                    #### 그런 줄 알았는데 부분매수인 경우 업빗은 volume이게 실제 체결양임.
                    if market =='up' :
                        completed_units = changeDecimal(parsed_data['volume'],8)
                        # trade는 executed_volume 이게 매수신청양이 됨.
                        # 1번에 사져도 어차피 trade가 오고 done이 오고, done은 무시하니까 trade기준으로 하면 됨.
                        units = changeDecimal(parsed_data['executed_volume'],8)
                    else:
                        completed_units = changeDecimal(parsed_data['executed_volume'],8)
                        units = changeDecimal(parsed_data['volume'],8)                  
                    
                
                    buy_amount = RealTime_coin[r_market]['buy_amount'][0] - myThreadManager.get_total_units(market, order_id)
                    diff = changeDecimal(RealTime_coin[r_market]['buy'][0] - trade_info.buy_price,2)
                    
                    # 성공. 체결된 양 확인해서 isOk로 반대쪽에 매도. 
                    # 빗썸은 부분매수 후의 마지막 부분매수는 완료로 옴.
                    if order_status == "done" :
                        # 업빗은 부분체결있으면 마지막 수량까지 부분체결로 하고 최종적으로 완료가 한번 더옴.
                        # 따라서 업빗인 경우 trades_count 확인해서 1보다 크면 부분매수가 있던거라. 이 완료는 이미 다 체결이 된 후에 오는 알림용 완료이므로 걸러낼것
                        #### 한번에 사져도 trade로 오고 같은걸로 완료가 오네. 무조건 완료는 버려야 하네.
                        if market =='up' :
                            log_str = f"[{thread_id}]{market} 부분매수 체결 후의 최종 매수 완료 알림이므로 무시."
                            myApi.insertLog(log_str,thread_id,f"info")
                            print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}][{thread_id}]{market}업빗 done이므로 무시.({order_id}), 체결량:{completed_units}, {parsed_data}")
                        else:
                            
                            sell_money = changeDecimal(completed_units * RealTime_coin[r_market]['buy'][0],2)
                            if completed_units > 0 and sell_money < 5000:
                                log_str = f"[{thread_id}]({order_id}){r_market}(done)짜투리 코인 매도 불가({sell_money}원), 짜투리코인:{completed_units}개, {trade_info.buy_price}"
                                myApi.insertLog(log_str,thread_id,'error')
                                print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}][{thread_id}]{market}333333333333333 매수성공 짜투리 처리불가({order_id}), 짜투리코인:{completed_units}개")
                            else:
                                isOK = True

                            isClear = True
                            log_str = f"[{thread_id}]{market}매수가격:{changeDecimal(parsed_data['price'],2)}, 체결량:{completed_units}, 예상 차익:{diff},  {parsed_data}"
                            #print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}]{log_str}")
                            myApi.insertLog(log_str,thread_id,f"매수성공",market)
                            print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}][{thread_id}]{market}3333333333333333 매수성공({order_id}), 체결량:{completed_units}, {parsed_data}")

                       
                        
                    elif order_status == "wait" : 
                        ## 대기가 안들어오고 바로 trade가 온적이 있음.
                        ## 대기를 안타서 코인정보가 안만들어졌어서 신청했을 때 만드는걸로 변경.
                        
                        log_str = f"[{thread_id}]{market}차익:{diff}, 신청량:[{completed_units}/{units}({buy_amount}), up_buy:{changeDecimal(parsed_data['price'],2)}, bit_buy1:{RealTime_coin[r_market]['buy'][0]}, {parsed_data}"
                        myApi.insertLog(log_str,thread_id,'매수대기',market)

                        print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}][{thread_id}]{market}22222222222222222 매수대기 ({order_id}),{parsed_data}")
                    
                    elif order_status == "trade":
                        # 기존에 있던 짜투리 코인고 지금 부분매수된 걸 더해서 5천원이 넘으면 헙쳐서 매도.
                        completed_units += trade_info.trash_coin
                        sell_money = changeDecimal(completed_units * RealTime_coin[r_market]['buy'][0],2)
                        if completed_units > 0 and sell_money < 5000:
                            # 5000천원이 안넘으면 누적한 양으로 교체.
                            log_str = f"[{thread_id}]({order_id}){r_market}(trade )짜투리 코인 매도 불가({sell_money}원), 짜투리코인:{completed_units}개, 매수금액{trade_info.buy_price}, 기존 짜투리:{trade_info.trash_coin}"
                            trade_info.trash_coin = completed_units
                            #print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}][{thread_id}]{market}짜투리코인 매수({completed_units}), 가격:{changeDecimal(parsed_data['price'],2)}, {parsed_data}")
                            
                            #myApi.insertLog(log_str,thread_id,"error")
                            print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}][{thread_id}]{market}33333333333333333 매수 짜투리 누적({order_id}), 짜투리코인:{completed_units}개")

                        else:
                            isOK = True                            
                            #print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}][{thread_id}]{market}부분매수 매수가격:{changeDecimal(parsed_data['price'],2)}, 체결량:{completed_units}, 포함 된 짜투리 코인:{trade_info.trash_coin}, 예상 차익:{diff},  {parsed_data}")
                            log_str = f"[{thread_id}]{market}부분매수가격:{changeDecimal(parsed_data['price'],2)}, 체결량:{completed_units}, 예상 차익:{diff},  {parsed_data}"
                            #print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}]{log_str}")
                            myApi.insertLog(log_str,thread_id,'부분매수성공',market)
                            print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}][{thread_id}]{market}33333333333333333 매수 부분매수({order_id}), {parsed_data}")
                            trade_info.trash_coin = 0

                        
                            
                    elif order_status == "cancel":
                        # 짜투리 코인이 있는채로 취소 된 경우.
                        completed_units = changeDecimal(trade_info.trash_coin,8)
                        sell_money = changeDecimal(completed_units * RealTime_coin[r_market]['buy'][0],2)
                        isClear = True
                        print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}][{thread_id}]{market}33333333333333333 매수취소({order_id}), {parsed_data}")
                        if completed_units > 0 and sell_money < 5000:
                            log_str = f"[{thread_id}]up_myOrder({order_id}){r_market}(cancel)짜투리 코인 매도 불가({sell_money}원), 짜투리코인:{completed_units}개, 매수금액{trade_info.buy_price}"
                            #print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}]{log_str}")
                            myApi.insertLog(log_str,thread_id,'error')
                            print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}][{thread_id}]{market}333333333333 매수취소 짜투리 처리불가({order_id}), 짜투리코인:{completed_units}개")
                        else:
                            trade_info.trash_coin = 0

                    else:                       
                        log_str = f"[{thread_id}]error bit order_status :{order_status}, {parsed_data}" 
                        #print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}]{log_str}")
                        myApi.insertLog(log_str,thread_id,"error")

                    if isOK :
                        trade_info.trade_count += 1
                        trade_info.bought_amount = completed_units
                        trade_info.sell_amount = completed_units
                        trade_info.buy_remaining_amount -= completed_units

                        cp_trade_info = copy.deepcopy(trade_info)

                        # 남은양을 다 쓴거면 마지막이라는거니까 클리어도 시켜 줄 것.
                        if trade_info.buy_remaining_amount < 0.000001:
                            isClear = True

                        print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}][{thread_id}]SellToMarket({r_market}) 시작 ({order_id}),{parsed_data}")
                        SellToMarket(r_market, order_id, thread_id, cp_trade_info)

                    # 업빗의 done인 경우 여기 들어가버리겠는데? 아닌데 done는 수량 지우지 않으니까.
                    if isClear :
                        print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}][{thread_id}]{market} 4444444444444 쓰레드 정리 isclear isClear({order_id}), 남은양:{trade_info.buy_remaining_amount}, {parsed_data}")
                        # 매수 완료 되었으니까 일단 탈출은 쓰레드는 종료 시키고 밑에서 매도 신청함.
                        log_str = f"[{thread_id}]stop_threads 시작 {order_id}"
                        myApi.insertLog(log_str)
                        myThreadManager.stop_thread(order_id, thread_id)
                        log_str = f"[{thread_id}]myOrder {market} 쓰레드 클리어:{order_id}, {parsed_data}"
                        #print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}]{log_str}")
                        myApi.insertLog(log_str,thread_id)

                    
                
                elif ask_bid =='ASK' :   
                    isOk = False
                    order_status = parsed_data["state"]
                    order_id = parsed_data['uuid']
                    completed_units = 0
                    

                    if order_status =='trade':
                        completed_units = changeDecimal(parsed_data['volume'],8)                          
                        isOk = True
                    # 빗썸 done만 executed_volume
                    elif  market == 'bit' and  order_status =='done':
                        completed_units = changeDecimal(parsed_data['executed_volume'],8) 
                        isOk = True
                    elif order_status =='wait' or order_status =='done':
                        # 아무것도 안함. 밑에 에러랑 구분짓기 위해서 넣음.
                        log_str = ""
                    else:
                        log_str = f"[{thread_id}]{market}매도 error parseMyOrder"
                        myApi.insertLog(log_str,thread_id,"error")


                    if isOk:
                        trade_info.sell_remaining_amount -= completed_units

                        cp_trade_info = copy.deepcopy(trade_info)
                        cp_trade_info.sold_price = changeDecimal(parsed_data['price'],2)
                        cp_trade_info.sold_amount = completed_units
                        cp_trade_info.sell_id = order_id
                        cp_trade_info.success_time = datetime.now()

                        ### 남은양이 0에 가까우면 trade_list에 판매쪽 오더아이디로 만든거 제거해야함.
                        # 매수 신청한 만큼 다 매도 된 경우 코인정보 삭제.
                        if cp_trade_info.sell_remaining_amount < 0.0000001 :
                            myThreadManager.del_trade(order_id)
                    
                        print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}][{thread_id}]{market} 77777777777 매도 완료 매수:{cp_trade_info.buy_id}, 매도:({order_id}), {parsed_data}")

                        log_str = f"[{thread_id}]{market}매도완료"
                        #print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}]{log_str}")
                        myApi.insertLog(log_str,thread_id,f"{market}매도완료")

                        if market == 'up':
                            buy_fee = myApi.settings.bit_fee
                            sell_fee = myApi.settings.up_fee
                        else:
                            buy_fee = myApi.settings.up_fee
                            sell_fee = myApi.settings.bit_fee

                        
                        total_today = myApi.insertTradeInfo(r_market, cp_trade_info, buy_fee, sell_fee)
                        
                        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
                        asyncio.run(myApi.info_message(r_market, cp_trade_info, order_id, total_today))

            except Exception as e: 
                log_str = f"myOrder error:{order_id}, {parsed_data}, e:Type({type(e)}), Message({str(e)}))"
                print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}]{log_str}")
                myApi.insertLog(log_str,thread_id,"error")
        
    else:
        log_str = f"{market} error parseMyOrder Unknown message type:{parsed_data}"
        print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}]{log_str}")
        myApi.insertLog(log_str,-1,"error")

def getMyOrder(ws,message,market): 
    thread = threading.Thread(target=parseMyOrder, args=(ws,message,market))
    thread.start()                        

bitCheckMyOrder_Class = wsPrivateClass(coin,'bit',getMyOrder,myApi.userinfo.b_key, myApi.userinfo.b_skey);
bitCheckMyOrder_Class.start()

upCheckMyOrder_Class = wsPrivateClass(coin,'up',getMyOrder,myApi.userinfo.u_key, myApi.userinfo.u_skey);
upCheckMyOrder_Class.start()



log_str = f"while start myThreadManager.program_run:{myThreadManager.program_run}"
myApi.insertLog(log_str)
wait_amount = 0


getBothBalance()

#발생 대기시간 체크할 때 첫 발생에 set_interval 만큼 기다림.
# 보통 여기서 다 기다려지는데, 중간에 데이터가 들어오면 풀리고
# 그럼 타임2부터 set_interval의 1/5 만큼씩 체크함.
delay_interval = coin_settings.set_interval / 5.0


thread_id = 0
temp_thread_id = 0
isSendCoinOver = False

def last_profitable_index(min_sell_price, sell_price_list):
    index = -1
    min_sell_price += coin_settings.BitToUp_comp_money_risk

    
        
    for i, price in enumerate(sell_price_list):
        if price >= min_sell_price:
            index = i
        else:
            break
    
    return index


def checkForBuy(market,r_market):
    global thread_id, temp_thread_id,current_time

    market_str = {'bit':"빗썸",'up': "업빗"}

    sell_price = 0
    mode = 1
    buy_price = 0


    if market =='bit':
        fee = coin_settings.bit_fee
    else:
        fee = coin_settings.up_fee
    
    temp_thread_id = thread_id +1 
    min_buy_amount = changeDecimal(6000 / RealTime_coin[market]['buy'][0],8)
    compare_money = RealTime_coin[market]['buy'][0] * min_buy_amount
    compare_my_coin = RealTime_coin[r_market]['coin_amount'] - myThreadManager.get_total_units(market)
    last_index = last_profitable_index(RealTime_coin[market]['buy'][0], RealTime_coin[r_market]['buy'])
    r_diff = changeDecimal(RealTime_coin[r_market]['buy'][0] - RealTime_coin[r_market]['buy'][1],2)
    if last_index > -1 :
        can_buy_market_amount = sum(RealTime_coin[r_market]['buy_amount'][0:last_index+1])
    else:
        can_buy_market_amount= 0
    can_buy_market_amount-= myThreadManager.get_total_units(market)
    highRiskValue = gethighRiskValue(market)
    log_str = f"[{temp_thread_id}]{market_str[market]}진입준비 {market}_buy1:{RealTime_coin[market]['buy'][0]}, {r_market}_buy1:{RealTime_coin[r_market]['buy'][0]}, {r_market}_buy1_amount:{RealTime_coin[r_market]['buy_amount'][0]}, {r_market}_매수1,2차이:{r_diff},{market}_매수단위:{highRiskValue}, {r_market}_매수단위:{gethighRiskValue(r_market)},"
    myApi.insertLog(log_str,temp_thread_id,f"{market_str[market]}진입준비")

    isOk = False
    if RealTime_coin[market]['krw_price'] < 5000 :
        log_str = f"보유 자산부족(5000원 미만), 사용가능 현금:({RealTime_coin[market]['krw_price']}원)"
    elif (compare_money > RealTime_coin[market]['krw_price']) :
        log_str = f"{market_str[market]} 현금 부족(최소수량 매수 불가), 최소수량:{min_buy_amount}, 최소수량 매수금액:{compare_money}, {market}krw_price:{RealTime_coin[market]['krw_price']}"
    elif RealTime_coin[r_market]['coin_amount'] < min_buy_amount:
        log_str = f"{market_str[r_market]}쪽 내 코인 부족(최소수량 매도 불가), 사용가능 내 코인:{RealTime_coin[r_market]['coin_amount']}, 최소수량:{min_buy_amount}, 최소수량 매수금액:{compare_money}, {r_market}_coin:{RealTime_coin[r_market]['coin_amount']}, 다른쓰레드 사용양:{myThreadManager.get_total_units(market)}"
    elif compare_my_coin < min_buy_amount:
        log_str = f"{market_str[r_market]}쪽 사용가능한 내 코인 부족(다른 쓰레드에서 다 사용 중), 사용가능 내 코인:{compare_my_coin}, 다른쓰레드 사용양:{myThreadManager.get_total_units(market)}, 최소수량:{min_buy_amount}, 최소수량 매수금액:{compare_money}, {r_market}_coin:{RealTime_coin[r_market]['coin_amount']}"
    elif can_buy_market_amount< min_buy_amount :
        log_str = f"{market_str[r_market]}쪽 마켓 코인 부족(최소수량 매수 불가), 최소수량:{min_buy_amount}, 최소수량 매수금액:{compare_money}, {r_market}_매수{last_index+1}:{RealTime_coin[r_market]['buy'][last_index]}, {r_market}_매수{last_index+1}까지 코인양:{can_buy_market_amount}, 다른쓰레드 사용양:{myThreadManager.get_total_units(market)}, {market}진입예상금액{RealTime_coin[market]['buy'][0]}, 설정값{coin_settings.BitToUp_comp_money_risk}, {RealTime_coin[market]['buy'][0]+coin_settings.BitToUp_comp_money_risk}, {r_market}쪽 호가{RealTime_coin[r_market]['buy']}, last_index:{last_index}"
    elif last_index == 0 and r_diff > gethighRiskValue(r_market):
        # last_index가 0이라는건 매수1 이외의 매수호가는 차액을 만족하지 못한다는거
        # 그 상태에서 매수1과 매수2의 차액이 크면 진입 안함.
        log_str = f"{market_str[r_market]}쪽 마켓 매수1, 2 차이가 큼 {r_market}_매수1:{RealTime_coin[r_market]['buy'][0]}, {r_market}_매수2:{RealTime_coin[r_market]['buy'][1]}, {r_market}_매수 단위:{gethighRiskValue(r_market)}"
    #elif(compare_money <= 5000) :
    #    log_str = f"최소수량 매수 금액이 5000원 미만. 최소수량:{half_once_units}, 최소수량 매수금액:{compare_money}"

    # 내물량이 적은건 크게 신경 안써도 될 듯. 어차피 최소물량 찾을거고. 그만큼 매수하면 되는거니까.
    # 그리고 매수시 바로바로 팔게 되서 탈출 시간 벌어야 하는 것도 좀 줄었으니까.
    #elif(compare_my_coin < half_once_units) :
    #    log_str = f"{market_str[r_market]}쪽 내 코인부족, 다른 쓰레드 신청양({myThreadManager.get_total_units(market)})"
        ######### 추후에 여기에 송금 기능 추가해야하고, 주석이랑 소스도 다시 확인할 것..
    else:
        isOk = True


    if isOk :    

        coin_settings.highRiskValue = highRiskValue
        sell_price = RealTime_coin[r_market]['buy'][last_index]
        mode = 1
        buy_price = RealTime_coin[market]['buy'][0]

        
        # 새로만들 매수1 만들 가격 계산
        buy0 = changeDecimal( buy_price + (coin_settings.highRiskValue * 1) , 3)

        # 일반모드 가능한지 계산        
        normal_last_index = last_profitable_index(RealTime_coin[market]['sell'][0], RealTime_coin[r_market]['buy'])
        
        # 퀵모드 가능한지 계산
        quick_last_index = last_profitable_index(buy0, RealTime_coin[r_market]['buy'])

        # 일반모드로 진입 가능한 경우.
        if normal_last_index > -1 :
            # 일반모드인 경우의 물량 계산
            normal_amount = sum(RealTime_coin[r_market]['buy_amount'][:last_index+1]) - myThreadManager.get_total_units(market)
            # 물량이 매수.매도 가능한 최소수량보다 높음
            if normal_amount < min_buy_amount :
                sell_price = RealTime_coin[r_market]['buy'][normal_last_index]
                mode = 0
                buy_price = RealTime_coin[market]['sell'][0]                
                can_buy_market_amount= normal_amount
        
        # 퀵모드로 진입 가능한 경우.
        elif quick_last_index > -1 :
            # 퀵모드인 경우의 물량 계산
            
            quick_amount = sum(RealTime_coin[r_market]['buy_amount'][:last_index+1]) - myThreadManager.get_total_units(market)
            # 물량이 매수.매도 가능한 최소수량보다 높음
            if quick_amount < min_buy_amount :
                sell_price = RealTime_coin[r_market]['buy'][quick_last_index]
                mode = 2
                buy_price = buy0
                can_buy_market_amount= quick_amount

    else:
        log_str = f"[{temp_thread_id}]{market_str[market]}진입보류 : {log_str}"
        myApi.insertLog(log_str,temp_thread_id,f"{market_str[market]}진입보류")
        current_time = datetime(1,1,1, second=0)
        return

    
    #기록용 시간이 0인 경우 현재 시간을 대입.(지금부터 지정시간만큼 차익이 유지되는지 체크가 됨)
    if current_time == datetime(1,1,1, second=0) :
        current_time = datetime.now()
        log_str = f"[{temp_thread_id}]count_time1  wait timeout {coin_settings.set_interval}"
        myApi.insertLog(log_str,temp_thread_id)
        myThreadManager.orderbook_event.wait(timeout=coin_settings.set_interval)
        myThreadManager.orderbook_event.clear()
        return
    # 차익이 발생해서 현재 유지중인 상태이므로 얼마나 유지중인지 확인함.
    else:
        time_diff = datetime.now() - current_time
        #log_str = f"count_time2,{time_diff.total_seconds()}"
        #myApi.insertLog(log_str,thread_id)
        # 유지된 시간이 지정한 시간보다 작으면 아직 진입하지 않도록. 
        if time_diff.total_seconds() < coin_settings.set_interval:
            myThreadManager.orderbook_event.wait(timeout=delay_interval)
            myThreadManager.orderbook_event.clear()
            return
    #내가 살 수 있는 수량 계산(최소 1회신청량의 절반 매수가능, 위에서 이미 체크함)

    

    canBuyAmount = changeDecimal((RealTime_coin[market]['krw_price']) / (buy_price + (buy_price * fee)),5)
    #{market_str[market]}매수물량의 반, 내가 살 수 있는 수량, {market_str[market]}에 남은 내 코인수량, 1회 신청량 중에 최소 수량 계산            
    buy_amount = changeDecimal(min(canBuyAmount, coin_settings.once_units, compare_my_coin, can_buy_market_amount),5)

    # 여분뺀 최대 허용보다 많으면 일단 확인 들어감.
    if myThreadManager.active_thread_count >= (myThreadManager.max_threads - spairThread):
        # 여분 포함해도 최대치를 넘으면 무조건 진입 안함.
        if myThreadManager.active_thread_count >= myThreadManager.max_threads:
            current_time = datetime(1,1,1, second=0)
            return
        
        count2 = 0
        if not myThreadManager.trade_list:
            for trade_info in myThreadManager.trade_list.items():
                if trade_info.buy_price > RealTime_coin[market]['buy'][0]:
                    count2 += 1
        
        if count2 > spairThread:
            count2 = spairThread
        
        # 여분 제외한 실제 최대 허용가능 쓰레드 수
        max_threads = myThreadManager.max_threads - spairThread
        # 여분용 말고 실제 사용중인 쓰레드 수
        active_thread_count = myThreadManager.active_thread_count - count2 
        
        # 여분용 제외한 쓰레드 수가 실제 최대 허용수보다 많은지
        if active_thread_count >= max_threads:
            current_time = datetime(1,1,1, second=0)
            return
        

        # count1 = 0
        # count2 = 0
        # #일반이나 퀵이 몇개인지 확인
        # for trade_info in myThreadManager.trade_list.items():
        #     if trade_info.isChange == 0 or trade_info.isChange == 2:
        #         count1 += 1

        # for trade_info in myThreadManager.trade_list.items():
        #     if trade_info.buy_price > RealTime_coin[market]['buy'][0]:
        #         count2 += 1

        # temp_spairThread = spairThread - count1 - count2
        # #매수2에서 쓰레드가 여분 쓰레드보다 많으면 여분쓰레드 만큼만 인정.
        # if temp_spairThread < 0:
        #     temp_spairThread =  0

 
        # if active_thread_count >= (myThreadManager.max_threads + temp_spairThread):
        #     current_time = datetime(1,1,1, second=0)
        #     return
        # else:
        #     if temp_spairThread == spairThread and mode == 1:
        #         current_time = datetime(1,1,1, second=0)
        #         return
       
    market_event[current_market] = False
    
    #매수 신청.
    wait_amount = RealTime_coin[market]['buy_amount'][0]
    log_str = f"[{temp_thread_id}]{market_str[market]}매수신청, mode:{mode}, 매수가격:{buy_price},예상매도가격:{sell_price}, 사용가능 내 코인:{compare_my_coin}, 매도가능 마켓코인:{can_buy_market_amount}, 다른쓰레드:{myThreadManager.get_total_units(market)}, {r_market}_매수1:{RealTime_coin[r_market]['buy'][0]}, {r_market}_매수1양:{RealTime_coin[r_market]['buy_amount'][0]}, {market}_sell1:{RealTime_coin[market]['sell'][0]}, {market}_sell1_amount:{RealTime_coin[market]['sell_amount'][0]} wait_amount:{wait_amount},buy_amount:{buy_amount}"
    myApi.insertLog(log_str,temp_thread_id,f"{market_str[market]}매수신청")
    
    res = marketApi[market].buy(buy_price, buy_amount)
    if not res.success:
        # 에러 처리
        program_shutdown(res.error)
    
    # 성공적인 응답 처리
    response = res.data
            
    # 매수 신청시의 통신 자체의 응답이 제대로 안 왔으면 넘어감.
    if response.status_code != 201:
        log_str = f"[{temp_thread_id}]error {market} buy_coin status_code:{response.status_code}, {response.json()}"
        myApi.insertLog(log_str,temp_thread_id,"error")
        ##{'error': {'name': 'invalid_volume_bid', 'message': '주문수량 단위를 잘못 입력하셨습니다. 확인 후 시도해주세요.'}}
    #매수 신청시의 통신 자체의 응답이 제대로 왔으면 json으로 파싱
    else:
        result = response.json()
        order_id = result["uuid"] 
        
        # escapeCheck 에서 사용할 데이터도 있어서 쓰레드 생성 전에 add_trade 할 것.
        #### 매수신청 완료가 찍히고 바로 대기상태가 온적이 있어서 쓰레드 만드는걸 매수신청 완료 찍는거 보다 앞으로 당겨 봄.
        trade_info = myThreadManager.add_trade(order_id, buy_amount, buy_price, buy_amount, sell_price, mode, 0)
        thread_id = myThreadManager.create_thread(escapeCheck, market, order_id)
        trade_info.thread_id = thread_id
              
        log_str = f"[{temp_thread_id}]{market_str[market]}매수신청 완료{order_id}), mode:{mode}"
        myApi.insertLog(log_str,temp_thread_id,f"{market_str[market]}매수신청 완료")
        
        
        print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}][{thread_id}]{market_str[market]}1111111111111매수신청 완료({order_id}), mode:{mode}, result:{result}")
        log_str = f"[{temp_thread_id}]{market_str[market]} 쓰레드 생성 : {thread_id}"
        myApi.insertLog(log_str,temp_thread_id)

    current_time = datetime(1,1,1, second=0)      
    

def gethighRiskValue(market):

    temp_buy1 = RealTime_coin[market]['buy'][0]
    if temp_buy1 < 0.0001:
        highRiskValue = Decimal('0.00000001')
    elif temp_buy1 < 0.001:
        highRiskValue = Decimal('0.0000001')
    elif temp_buy1 < 0.01:
        highRiskValue = Decimal('0.000001')
    elif temp_buy1 < 0.1:
        highRiskValue = Decimal('0.00001')
    elif temp_buy1 < 1:
        highRiskValue = Decimal('0.0001')
    elif temp_buy1 < 10:
        highRiskValue = Decimal('0.001')
    elif temp_buy1 < 100:
        highRiskValue = Decimal('0.01')
    elif temp_buy1 < 1000:
        # 업비트는 원래 0.1원인데 일부 코인만 1원으로 하고 있음.
        if market == 'bit' or (market == 'up' and (coin in up_coinList)):
            highRiskValue = 1
        else:
            highRiskValue = Decimal('0.1')
    elif temp_buy1 < 10000:
        highRiskValue = 1
    elif temp_buy1 < 100000:
        highRiskValue = 10
    elif temp_buy1 < 500000:
        highRiskValue = 50
    elif temp_buy1 < 1000000:
        highRiskValue = 100
    elif temp_buy1 < 5000000:
        highRiskValue = 500
    elif temp_buy1 < 10000000:
        highRiskValue = 1000

    return highRiskValue


while(myThreadManager.program_run): 
    if bit_ws_class.is_alive() and up_ws_class.is_alive() :
        # current_time에 시간이 있다는건 진입 조건을 만족했고 지정한 시간이상 유지되고 있는지 체크중인거임
        # 따라서 이 때는 이벤트 대기를 하면 안됨.
        if current_time == datetime(1,1,1, second=0) :
            # startTime = time.time()
            #log_str = f"[{temp_thread_id}]myThreadManager.orderbook_event.wait():{current_time}"
            #myApi.insertLog(log_str,temp_thread_id,"temp")
            # endTime = time.time()
            # latency = endTime - startTime
            # print(f"[DB추가시간]Latency: {latency} seconds")
            myThreadManager.orderbook_event.wait()
            myThreadManager.orderbook_event.clear()
            market_event['bit'] = False
            market_event['up'] = False
        else:
            log_str = f"[{temp_thread_id}]count_time  checking myThreadManager.orderbook_event ignore current_time:{current_time}"
            myApi.insertLog(log_str,temp_thread_id,"info")
    else:
        time.sleep(1)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}]bit_ws_class.is_alive():{bit_ws_class.is_alive()}, up_ws_class.is_alive():{up_ws_class.is_alive()}")

    if not myThreadManager.program_run :
        while(myThreadManager.active_thread_count > 0):
            log_str = f"[{temp_thread_id}]프로그램 종료를 위하 쓰레드 종료 대기.[{myThreadManager.active_thread_count} / {myThreadManager.max_threads}]"
            myApi.insertLog(log_str,temp_thread_id,"error")
            time.sleep(1)

        continue;


    isChecking = True
    isUpbitcheck = True
    completed_units = 0
    units = coin_settings.once_units
    
    # 이미 쓰레드가 꽉 찬거라 새로운 진입점이 발생하는지 체크할 필요 없음.
    if myThreadManager.active_thread_count >= myThreadManager.max_threads:
        current_time = datetime(1,1,1, second=0)
        log_str = f"쓰레드 오버 .{myThreadManager.active_thread_count} / {myThreadManager.max_threads} "
        myApi.insertLog(log_str,temp_thread_id,"error")
        continue

    if changeDecimal(RealTime_coin['bit']['coin_amount']+RealTime_coin['up']['coin_amount'],8) > coin_settings.max_coin_amount + coin_settings.once_units :
        if not isSendCoinOver :
            print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}]코인 오버 [{changeDecimal(RealTime_coin['bit']['coin_amount']+RealTime_coin['up']['coin_amount'],8)}/{coin_settings.max_coin_amount + coin_settings.once_units}], 1회 거래량:{coin_settings.once_units}, 빗썸:{changeDecimal(RealTime_coin['bit']['coin_amount'],8)}, 업빗:{changeDecimal(RealTime_coin['up']['coin_amount'],8)}")
            log_str = f"코인오버 [{changeDecimal(RealTime_coin['bit']['coin_amount']+RealTime_coin['up']['coin_amount'],8)}/{coin_settings.max_coin_amount + coin_settings.once_units}], 1회 거래량:{coin_settings.once_units}, bit_coin_amount:{RealTime_coin['bit']['coin_amount']},up_coin_amount:{RealTime_coin['up']['coin_amount']}"
            myApi.insertLog(log_str,temp_thread_id,"코인오버")
            isSendCoinOver = True
            asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
            asyncio.run(myApi.error_message(1,RealTime_coin))

        current_time = datetime(1,1,1, second=0)
        continue
        
    if RealTime_coin['bit']['buy'][0] == 0 :
        myThreadManager.orderbook_event.wait()
        myThreadManager.orderbook_event.clear()
        continue

    isSendCoinOver = False

    #print(f"{RealTime_coin.BitToUp_diff}, {coin_settings.BitToUp_comp_money_risk}")
### 원래는 업빗매수1, 물량 등등이 바뀌면 시간을 초기화해야 원래 취지에 맞음.
### 다 확인하기에는 좀 많은데, 이것도 모드에 따라서 해야 하나? 일반모드였으면 빗썸매도1 변경하는지 본다거나.
############################
    if (RealTime_coin.BitToUp_diff >= coin_settings.BitToUp_comp_money_risk) :
        
        # 직전 상황이 역방향 체크였으면, 체크중이던 시간을 초기화 해야함
        # 역방향에서 시간체크를 위해서 슬립걸리고 다시 내려왔을 때 상황이 정방향이 되었을 때
        # 시간이 역방향께 남아 있어서 그 상태로 진행되버리는 경우가 발생할 수 있음
        #print("정방향")

        if current_market =='up':
            current_time = datetime(1,1,1, second=0)

        current_market ='bit'
        r_current_market = 'up'
        checkForBuy(current_market,r_current_market)
        
        
    elif (RealTime_coin.UpToBit_diff >= coin_settings.UpToBit_comp_money_risk) :
        
        # 직전 상황이 역방향 체크였으면, 체크중이던 시간을 초기화 해야함
        # 역방향에서 시간체크를 위해서 슬립걸리고 다시 내려왔을 때 상황이 정방향이 되었을 때
        # 시간이 역방향께 남아 있어서 그 상태로 진행되버리는 경우가 발생할 수 있음
        #print("역방향")
        
        if current_market =='bit':
            current_time = datetime(1,1,1, second=0)
        
        current_market ='up'
        r_current_market = 'bit'
        checkForBuy(current_market,r_current_market)
            
        
    else:
        # 시간 체크 중인게 있었다면 리셋함
        if current_time != datetime(1,1,1, second=0) :
            current_time = datetime(1,1,1, second=0)
            log_str = f"[{temp_thread_id}]count_time reset  ({current_market})" 
            myApi.insertLog(log_str,temp_thread_id) 


program_shutdown()
# myThreadManager.shutdown()
# bit_ws_class.stop()
# up_ws_class.stop()
# bitCheckMyOrder_Class.stop()
# upCheckMyOrder_Class.stop()
# log_str = f"[{temp_thread_id}]시스템 종료[{myThreadManager.active_thread_count} / {myThreadManager.max_threads}]"
# myApi.insertLog(log_str,temp_thread_id,"error") 
# print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}]{log_str}")
# asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
# asyncio.run(myApi.error_message(0,RealTime_coin,myApi.err_log_str))
# sys.exit(0)