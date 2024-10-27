import sys
import json
import uuid
import time
from datetime import datetime
import telegram
import concurrent.futures  # 이 부분을 추가해주세요.
import psycopg2
#from psycopg2 import pool
import threading
import copy
from dataclasses import dataclass


class MyApi:
    @dataclass
    class CoinSet:
        thread_id: str = ""
        bit = {
            'buy': [0.0] * 5,
            'sell': [0.0] * 5,
            'buy_amount': [0.0] * 5,
            'sell_amount': [0.0] * 5,
            'coin_amount': 0.0,
            'krw_price': 0.0
        }
        up = {
            'buy': [0.0] * 5,
            'sell': [0.0] * 5,
            'buy_amount': [0.0] * 5,
            'sell_amount': [0.0] * 5,
            'coin_amount': 0.0,
            'krw_price': 0.0
        }

        BitToUp_diff: float = 0.0
        UpToBit_diff: float = 0.0

        BitToUp_diff2: float = 0.0
        UpToBit_diff2: float = 0.0

        buy_price: float = 0.0
        buy_amount: float = 0.0
        buy_req_amount: float = 0.0

        sell_price: float = 0.0
        sell_last_price: float = 0.0
        sell_amount: float = 0.0

        buy_extra_sell1: float = 0.0
        buy_extra_sell1_amount: float = 0.0
        sell_extra_sell1: float = 0.0
        sell_extra_sell1_amount: float = 0.0

        estimated_sell_price: float = 0.0
        estimated_diff: float = 0.0
        sub_diff: float = 0.0


        UpToBit_fee: float = 0.0
        BitToUp_fee: float = 0.0

        bit_fee: float = 0.0004
        up_fee: float = 0.0005
        total_today: float = 0.0
        isChange: int = 1
        success_time: datetime = datetime(1, 1, 1, second=0)
        trash_coin: float = 0.0
        remaining_amount:float = 0.0

        def __getitem__(self, key):
            if key not in ['bit', 'up']:
                raise KeyError(f"Invalid key: {key}. Use 'bit' or 'up'.")
            return self.bit if key == 'bit' else self.up

    @dataclass
    class Settings:
        BitToUp_comp_money_risk_rate: float = 0.0
        UpToBit_comp_money_risk_rate: float = 0.0
        BitToUp_comp_money: float = 100.0
        UpToBit_comp_money: float = 100.0
        BitToUp_comp_money_risk: float = 0.0
        UpToBit_comp_money_risk: float = 0.0
        send_wait_time: float = 0.0  # 7200
        wait_amount: float = 0.0
        check_wait_time: float = 0.0
        once_units: float = 0.0
        max_coin_amount: float = 0.0
        set_interval: float = 0.0  # 1.8초 유지 시에 만
        minimum: float = 100.0
        highRiskScope: float = 0.0
        isAutoSend: int = 0  # 0: False, 1: 업비트로, 2: 빗썸으로
        send_coin: str = ""  # coin 변수를 사용해야 함
        send_units: float = 0.0
        send_ko_name: str = "김동규"
        send_en_name: str = "KIM DONGGYU"
        send_exchange_name: str = "Upbit"
        send_address: str = ""
        send_destination: str = ""
        telegram: str = ""
        highRisk: bool =True
        highRiskValue: float = 1
        bit_fee: float = 0.0004
        up_fee: float = 0.0005
    
    @dataclass
    class UserInfo:
        memid: int = 0
        b_key: str = ""
        b_skey: str = ""
        u_key: str = ""
        u_skey: str = ""
        name:str = ""

    def __init__(self,coin,memid=1):
        self.coin = coin
        self.connection = psycopg2.connect(host='localhost', database='coinlog', user='coinlogger', password='coinlogger8709')
        self.connection.autocommit = True
        self.cur = self.connection.cursor()

        # self.postgreSQL_pool = psycopg2.pool.SimpleConnectionPool(1, 20,host='localhost', database='coinlog', user='coinlogger', password='coinlogger8709')
        # self.postgreSQL_pool_cursors = {}
        self.coinSet = self.CoinSet()
        self.settings = self.Settings()
        self.userinfo = self.UserInfo()

        self.load_userinfo(memid)
        self.load_settings()
        self.trad_match = {}

        
        self.err_log_str = ""
        
    

    def insertLog(self, log, thread_id=-1, type_data="info",mode=""):
        sql = "INSERT INTO datalog (memid, coin, log, thread_id, type) VALUES (%s,%s,%s,%s,%s)"
        if mode == 'bit':
            mode_str = '빗썸'
        elif mode == 'up':
            mode_str = '업빗'
        else:
            mode_str =""
	
        # 디버그용
        #if type_data != 'temp' and type_data != 'status':
        #    print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}]{log}")

        type_data = mode_str + type_data
        values = (self.userinfo.memid,self.coin, log, thread_id, type_data)
        try :
            # if self.postgreSQL_pool_cursors.get(thread_id) is None:
            #     cursor = self.cur
            # else:
            #     cursor = self.postgreSQL_pool_cursors[thread_id][1] # 0이 conn
            # cursor.execute(sql, values)


            self.cur.execute(sql, values)
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}]insertLog 오류 발생: {e}, sql:{sql}")
        #self.connection.commit()
    
    def insertCoin(self, market, RealTime_coin):     

        sql = "INSERT INTO coinlog (memid,coin, market, b_buy_price1, b_buy_amount1, b_buy_price2, b_buy_amount2, b_sell_price1, b_sell_amount1, b_sell_price2, b_sell_amount2, u_buy_price1, u_buy_amount1, u_buy_price2, u_buy_amount2, u_sell_price1, u_sell_amount1, u_sell_price2, u_sell_amount2) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s, %s, %s, %s, %s, %s, %s, %s, %s)"
        values = (self.userinfo.memid,self.coin, market, RealTime_coin.bit_buy1,RealTime_coin.bit_buy1_quantity, RealTime_coin.bit_buy2,RealTime_coin.bit_buy2_quantity, RealTime_coin.bit_sell1, RealTime_coin.bit_sell1_quantity, RealTime_coin.bit_sell2, RealTime_coin.bit_sell2_quantity, RealTime_coin.up_buy1,RealTime_coin.up_buy1_quantity, RealTime_coin.up_buy2,RealTime_coin.up_buy2_quantity, RealTime_coin.up_sell1, RealTime_coin.up_sell1_quantity, RealTime_coin.up_sell2,RealTime_coin.up_sell2_quantity)
        try :
            self.cur.execute(sql, values)
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}]insertCoin 오류 발생: {e}, sql:{sql}")
        #self.connection.commit()

    def updateTodayKrw(self, todaykrw):
        while(True):    
            # 오늘 날짜 구하기
            today = datetime.now().date()

            # SQL 쿼리 작성
            sql = f"SELECT memid, coin, todaykrw FROM todaykrw WHERE memid = {self.userinfo.memid} AND coin = '{self.coin}' and DATE(created_at) = '{today}'"
            # 쿼리 실행 및 결과 가져오기
            try :
                self.cur.execute(sql)
            except Exception as e:
                print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}]updateTodayKrw 오류 발생1: {e}, sql:{sql}")
            
            # 원래 쿼리 결과가 없을 수 있음. 날이 바뀌면 새로 만들거니까
            # loadsettings처럼 카운트 0 을 여기다 넣으면 안됨.
            try:
                # 결과 가져오기
                results = self.cur.fetchone()
                #print(results)
                if results is None:
                    sql = "INSERT INTO todaykrw(memid, market, coin, todaykrw) values (%s,%s,%s,%s)"
                    values = (self.userinfo.memid,'test',self.coin,todaykrw)
                    
                else:
                    self.coinSet.total_today = todaykrw + float(results[2])
                    sql = "UPDATE todaykrw SET todaykrw = %s WHERE memid = %s AND coin = %s and  DATE(created_at) = '{today}'"
                    values = (self.coinSet.total_today,results[0],results[1])

                try :
                    self.cur.execute(sql, values)
                except Exception as e:
                    print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}]updateTodayKrw 오류 발생2: {e}, sql:{sql}")
                #self.connection.commit()
                break
            except Exception as e:
                    log_str = f'[{datetime.now().strftime("%H:%M:%S.%f")[:-3]}]error updateTodayKrw Query execution error: {e}'
                    self.insertLog(log_str)
                    print(log_str)
            
            time.sleep(1)
                
                

    def load_settings(self):
        while(True):
            
            # SQL 쿼리 작성
            sql = f"SELECT * FROM public.settings WHERE memid = {self.userinfo.memid} AND coin = '{self.coin}'"
            # 쿼리 실행 및 결과 가져오기
            self.cur.execute(sql)
            # print(self.cur.description)
            # print(self.cur.statusmessage) 
            # for notice in self.connection.notices:
            #     print(notice)
            if self.cur.rowcount == 0:
            ### 값이 없는 경우
                log_str = f'[{datetime.now().strftime("%H:%M:%S.%f")[:-3]}]error load_settings self.cur.rowcount 0 '
                self.insertLog(log_str)
                print(log_str)
            else:
                try:
                    results = self.cur.fetchone()
                    if results is None:
                        log_str = f'[{datetime.now().strftime("%H:%M:%S.%f")[:-3]}]error load_settings results None'
                        self.insertLog(log_str)
                        print(log_str)
                    else:
                        # 결과 가져오기
                        #print(results[3])
                        self.settings.BitToUp_comp_money_risk_rate = results[3]  # btu_money_diff_rate
                        self.settings.UpToBit_comp_money_risk_rate = results[4]  # utb_money_diff_rate
                        self.settings.send_wait_time = results[5]  # send_wait_time
                        self.settings.wait_amount = results[6]  # wait_amount
                        self.settings.once_units = results[7]  # once_units
                        self.settings.max_coin_amount = results[8]  # max_coin_amount
                        self.settings.set_interval = results[9]
                        self.settings.check_wait_time = self.settings.send_wait_time
                        self.settings.highRiskScope = results[10]  # highRiskScope
                        self.settings.isAutoSend = results[11]  # settings.isAutoSend
                        self.settings.send_units = results[12]  # settings.send_units
                        self.settings.send_ko_name = results[13]  # settings.send_ko_name
                        self.settings.send_en_name = results[14]  # settings.send_en_name
                        self.settings.send_exchange_name = results[15]  # settings.send_exchange_name
                        self.settings.send_address = results[16]  # send_addres
                        self.settings.send_destination = results[17]  # settings.send_destination
                        self.settings.telegram = results[19] #18은 created_at
                        self.settings.highRisk = results[20] 
                        self.settings.highRiskValue = results[21]
                        self.settings.bit_fee = results[22]
                        self.settings.up_fee = results[23]

                        if not self.settings.highRisk :
                            self.settings.set_interval *= 2

                        log_str = f'load_settings'
                        self.insertLog(log_str)
                        break;
                except Exception as e:
                    log_str = f'[{datetime.now().strftime("%H:%M:%S.%f")[:-3]}] error load_settings Query execution error: {e}'
                    self.insertLog(log_str)
                    print(log_str)                 
                
            time.sleep(1)

    def load_userinfo(self, memid):
        while(True):
            # SQL 쿼리 작성
            
            sql = "SELECT * FROM public.member WHERE memid = %s"
            print(self.cur.mogrify(sql, (memid,)).decode('utf-8'))

            # 쿼리 실행 및 결과 가져오기
            self.cur.execute(sql, (memid,))
            
            if self.cur.rowcount == 0:
            ### 값이 없는 경우
                log_str = f'[{datetime.now().strftime("%H:%M:%S.%f")[:-3]}]error load_userinfo self.cur.rowcount 0 '
                self.insertLog(log_str)
                print(log_str)
                results = self.cur.fetchall()
                row_count = len(results)
                print(row_count)
                print(results)
                sys.exit(1) 
            else:
                try:
                    results = self.cur.fetchone()
                    if results is None:
                        log_str = f'[{datetime.now().strftime("%H:%M:%S.%f")[:-3]}]error load_userinfo results None'
                        self.insertLog(log_str)
                        print(log_str)
                    else:
                        # 결과 가져오기
                        print(results[1])
                        self.userinfo.memid = results[1]  # memid
                        self.userinfo.b_key = "86585d7c1baee326041c38c9293780de7d93f7ca3f87ca" #results[2]  # memid
                        self.userinfo.b_skey = "YTdiNDVmZGRkYmYxOTQyMTU0NzkxN2EyZTAyNjcyNmMzZWNjMjMzZDgzZGU3NTliZjZjYjNiODZjYjAzNQ==" #results[3]  # memid
                        self.userinfo.u_key = results[4]  # memid
                        self.userinfo.u_skey = results[5]  # memid
                        self.userinfo.name = results[6]  # memid

                        
                        log_str = f'load_userinfo'
                        self.insertLog(log_str)
                        break;
                except Exception as e:
                    log_str = f'[{datetime.now().strftime("%H:%M:%S.%f")[:-3]}] error load_userinfo Query execution error: {e}'
                    self.insertLog(log_str)
                    print(log_str)                 
            time.sleep(1)

    def cutFloat(self, value, count):
        if type(value) == str:
            try:
                value = float(value)
            except ValueError:
                value = 0  # 문자열을 float으로 변환할 수 없는 경우
        elif value is None:
            value = 0
            
        value = round(value,9)

        return (int(value * 10**count) / 10**count)   


    async def info_message(self, market, thread_id, coin, cp_trade_info, order_id):
           
        bot = telegram.Bot(token=self.settings.telegram)
        chat_id = '6380176264'
        
        buy_order_id = cp_trade_info.buy_id
        buy_price = self.cutFloat(cp_trade_info.buy_price,2)        
        buy_amount = cp_trade_info.buy_amount
        bought_amount = self.cutFloat(cp_trade_info.bought_amount,8)
        buy_remaining_amount = cp_trade_info.buy_remaining_amount
        
        sell_price = self.cutFloat(cp_trade_info.sell_price,2)
        sold_amount = self.cutFloat(cp_trade_info.sold_amount,8)
        sell_remaining_amount = self.cutFloat(cp_trade_info.sell_remaining_amount,8)

        fee = self.cutFloat(sell_price * self.settings.bit_fee,5) + self.cutFloat(buy_price * self.settings.up_fee,5)
        diff = self.cutFloat(sell_price - buy_price,3)
        money = self.cutFloat(diff - fee,3)
        # 진입시의 예상 차익이니까 coin.sell_price
        estimated_diff = coin.sell_price - buy_price
        # 대기 메시지가 왔을 때 넣은 차익. 이게 원래 차익이어야 하는데, 판매하면서 가격이 떨어지면 diff가 낮아짐.
        sub_diff = coin.sell_last_price - coin.buy_price
        got_money = self.cutFloat(money*sold_amount,2)

        bit_coin = coin['bit']['coin_amount']
        bit_krw = coin['bit']['krw_price']
        up_coin = coin['up']['coin_amount']
        up_krw = coin['up']['krw_price']


        self.updateTodayKrw(got_money)
        log_str = f"[{thread_id}]차익발생,{market},수익:{got_money},차액:{money}({diff})매수:{bought_amount},매도:{sold_amount},수수료:{fee}, 매도량:[{sold_amount}/{bought_amount}],총 수익:{self.coinSet.total_today}, bit_coin_amount:{coin['bit']['coin_amount']},bit_coin_amount:{coin['bit']['coin_amount']},total_kwr:{int(bit_krw+up_krw)}, bit:{int(bit_krw)}, up:{int(up_krw)}, mode:{coin.isChange}"
        self.insertLog(log_str,thread_id,"차익발생")

        
        direction = "업비트->빗썸" if market=='up' else "빗썸->업비트"
        sell_exchange = "빗썸" if market=='up' else "업빗"
        buy_exchange = "업빗" if market=='up' else "빗썸"

        text = f"{self.coin}({direction}) 수익:{got_money:9.2f}원\n"
        text += f"실차액:{money:3.3f}원, 수수료:{fee:3.3f}원\n"
        text += f"매도:{sold_amount:6.2f}개, 차액:{diff:3.3f}원({sub_diff:3.3f}원){estimated_diff:3.3f}원\n"
        text += f"매수:{bought_amount:6.2f}개, 신청{buy_amount}개(남음:{buy_remaining_amount:6.2f}개)\n"
        text += f"{sell_exchange}매도:{sell_price:9.2f}원\[{coin.estimated_sell_price:9.2f}원]\n"
        text += f"{buy_exchange}매수:{buy_price:9.2f}원\n"

        text += f"\[빗썸] 코인:{bit_coin:8.2f} 현금:{bit_krw:9.2f}원\n"
        text += f"\[업빗] 코인:{up_coin:8.2f} 현금:{up_krw:9.2f}원\n"
        text += f"\[총합] 코인:{bit_coin + up_coin:8.2f} 현금:{bit_krw + up_krw:9.2f}원\n"
        text += f"오늘 수익 : {self.coinSet.total_today:8.2f}\n"
        
        if coin.isChange == 0 :
            text = text + "일반모드"
        elif coin.isChange == 1 :    
            text = text + "리스크모드"
        else :
            text = text + "퀵모드"
        
        text = text + f"\[" + coin.success_time.strftime("%H:%M:%S.%f")[:-3] + "]"
        text = text + "[{:5d}]\n".format(thread_id)
        text = text + f"매수:{order_id}\n"
        text = text + f"매도:{buy_order_id}" 

        # 매수 신청한 만큼 다 매도 된 경우 코인정보 삭제.
        if sell_remaining_amount < 0.0000001 :
            del self.trad_match[order_id]

        await bot.send_message(chat_id, text, parse_mode="Markdown")
    
    async def error_message(self, error_id, coin, err_log_str=""):

        bot = telegram.Bot(token=self.settings.telegram)
        chat_id = '6380176264'
        
        if error_id == 0:
            text = f"[시스템 종료] {self.coin}\n"
            text = text + err_log_str + f"\n"
        elif error_id == 1:
            text = f"[코인 오버] {self.coin}"
            text = text + f"총량:{(coin['bit']['coin_amount']+coin['up']['coin_amount']):8.2f}\n"
            #text = text + f"매도중 물량:{(self.get_total_bought()):8.2f}\n"

        text += f"[빗썸] 코인:{coin['bit']['coin_amount']:8.2f} 현금:{coin['bit']['krw_price']:9.2f}원\n"
        text += f"[업빗] 코인:{coin['up']['coin_amount']:8.2f} 현금:{coin['up']['krw_price']:9.2f}원\n"
        text += f"[총합] 코인:{coin['bit']['coin_amount'] + coin['up']['coin_amount']:8.2f} 현금:{coin['bit']['krw_price'] + coin['up']['krw_price']:9.2f}원\n"
        text = text + f"\[" + datetime.now().strftime("%H:%M:%S.%f")[:-3] + "]"

        await bot.send_message(chat_id, text, parse_mode="Markdown")