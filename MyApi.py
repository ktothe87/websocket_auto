import sys
import time
from datetime import datetime
import telegram
import psycopg2
from dataclasses import dataclass, field
from typing import Dict, Any
from decimal import Decimal, ROUND_DOWN, InvalidOperation


class MyApi:
    @dataclass
    class CoinSet:
        thread_id: str = ""
        # bit = {
        #     'buy': [0.0] * 5,
        #     'sell': [0.0] * 5,
        #     'buy_amount': [0.0] * 5,
        #     'sell_amount': [0.0] * 5,
        #     'coin_amount': 0.0,
        #     'krw_price': 0.0,
        #     'ori_buy': ""
        # }
        # up = {
        #     'buy': [0.0] * 5,
        #     'sell': [0.0] * 5,
        #     'buy_amount': [0.0] * 5,
        #     'sell_amount': [0.0] * 5,
        #     'coin_amount': 0.0,
        #     'krw_price': 0.0,
        #     'ori_buy': ""
        # }

        bit = {
            'buy': [Decimal('0.0')] * 5,
            'sell': [Decimal('0.0')] * 5,
            'buy_amount': [Decimal('0.0')] * 5,
            'sell_amount': [Decimal('0.0')] * 5,
            'coin_amount': Decimal('0.0'),
            'krw_price': Decimal('0.0'),
            'ori_buy': ""
        }
        up = {
            'buy': [Decimal('0.0')] * 5,
            'sell': [Decimal('0.0')] * 5,
            'buy_amount': [Decimal('0.0')] * 5,
            'sell_amount': [Decimal('0.0')] * 5,
            'coin_amount': Decimal('0.0'),
            'krw_price': Decimal('0.0'),
            'ori_buy': ""
        }
        # bit: Dict[str, Any] = field(default_factory=lambda: {
        # 'buy': [0.0] * 5,
        # 'sell': [0.0] * 1,
        # 'buy_amount': [0.0] * 5,
        # 'sell_amount': [0.0] * 1,
        # 'coin_amount': 0.0,
        # 'krw_price': 0.0
        # })
        # up: Dict[str, Any] = field(default_factory=lambda: {
        #     'buy': [0.0] * 5,
        #     'sell': [0.0] * 1,
        #     'buy_amount': [0.0] * 5,
        #     'sell_amount': [0.0] * 1,
        #     'coin_amount': 0.0,
        #     'krw_price': 0.0
        # })
        ori_buy: str = ""
        UpToBit_fee: Decimal = Decimal('0.0')
        BitToUp_fee: Decimal = Decimal('0.0')

        BitToUp_diff: Decimal = Decimal('0.0')
        UpToBit_diff: Decimal = Decimal('0.0')

        BitToUp_diff2: Decimal = Decimal('0.0')
        UpToBit_diff2: Decimal = Decimal('0.0')    

        def __getitem__(self, key):
            if key not in ['bit', 'up']:
                raise KeyError(f"Invalid key: {key}. Use 'bit' or 'up'.")
            return self.bit if key == 'bit' else self.up

    @dataclass
    class Settings:
        BitToUp_comp_money_risk_rate: Decimal = Decimal('0.0')
        UpToBit_comp_money_risk_rate: Decimal = Decimal('0.0')
        BitToUp_comp_money: Decimal = Decimal('100.0')
        UpToBit_comp_money: Decimal = Decimal('100.0')
        BitToUp_comp_money_risk: Decimal = Decimal('0.0')
        UpToBit_comp_money_risk: Decimal = Decimal('0.0')
        send_wait_time: float = 0.0  # 7200
        wait_amount: Decimal = Decimal('0.0')
        check_wait_time: float = 0.0
        once_units: Decimal = Decimal('0.0')
        max_coin_amount: Decimal = Decimal('0.0')
        set_interval: float = 0.0  # 1.8초 유지 시에 만
        minimum: Decimal = Decimal('100.0')
        highRiskScope: Decimal = Decimal('0.0')
        isAutoSend: int = 0  # 0: False, 1: 업비트로, 2: 빗썸으로
        send_coin: str = ""  # coin 변수를 사용해야 함
        send_units: Decimal = Decimal('0.0')
        send_ko_name: str = "김동규"
        send_en_name: str = "KIM DONGGYU"
        send_exchange_name: str = "Upbit"
        send_address: str = ""
        send_destination: str = ""
        telegram: str = ""
        highRisk: bool =True
        highRiskValue: Decimal = Decimal('1')
        bit_fee: Decimal = Decimal('0.0004')
        up_fee: Decimal = Decimal('0.0005')
    
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

    def insertTradeInfo(self, market, trade_info, buy_fee, sell_fee):     

        sql = """
            INSERT INTO tradeinfo (
                memid, coin, buy_market, b_price, s_price, 
                b_req_amount, b_amount, b_remaining_amount, 
                s_req_amount, s_amount, s_remaining_amount, 
                thread_id, b_order_id, s_order_id, buy_fee, sell_fee, mode
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

        values = (
            self.userinfo.memid, self.coin, market, 
            trade_info.buy_price, trade_info.sold_price,
            trade_info.buy_amount, trade_info.bought_amount, trade_info.buy_remaining_amount,
            trade_info.sell_amount, trade_info.sold_amount, trade_info.sell_remaining_amount,
            trade_info.thread_id,  
            trade_info.buy_id, trade_info.sell_id, buy_fee, sell_fee, trade_info.isChange
        )

        try :
            self.cur.execute(sql, values)
        except Exception as e:
            log_str =  f"[{trade_info.thread_id}]error insertTradeInfo 오류 발생: {e}, sql:{sql}"
            self.insertLog(log_str)
            print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}]{log_str}")

        while(True):
            sql = f"SELECT memid, coin, SUM(money) AS total_money FROM public.tradeinfo_view WHERE memid = {self.userinfo.memid} AND coin = '{self.coin}' AND DATE(created_at) = CURRENT_DATE GROUP BY memid, coin"

            try :
                self.cur.execute(sql)
            except Exception as e:
                log_str = f"[{trade_info.thread_id}]error insertTradeInfo  View get total_today 오류 발생1: {e}, sql:{sql}"
                self.insertLog(log_str)
                print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}]{log_str}")

            try :
                results = self.cur.fetchone()
                if not results:
                    log_str = f"[{trade_info.thread_id}]error insertTradeInfo  View None : results:{results}, sql:{sql}"
                    self.insertLog(log_str)
                    print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}]{log_str}")
                else:
                    return (float(results[2]))

            except Exception as e:
                log_str = f'[{trade_info.thread_id}]error insertTradeInfo  View get total_today 오류 발생2 results:{results}, sql:{sql}, e:{e}'
                self.insertLog(log_str)
                print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}]{log_str}")    

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
                        self.settings.BitToUp_comp_money_risk_rate = Decimal(str(results[3]))  # btu_money_diff_rate
                        self.settings.UpToBit_comp_money_risk_rate = Decimal(str(results[4]))  # utb_money_diff_rate
                        self.settings.send_wait_time = results[5]  # send_wait_time
                        self.settings.wait_amount = Decimal(str(results[6]))  # wait_amount
                        self.settings.once_units = Decimal(str(results[7]))  # once_units
                        self.settings.max_coin_amount = Decimal(str(results[8]))  # max_coin_amount
                        self.settings.set_interval = results[9]
                        self.settings.check_wait_time = self.settings.send_wait_time
                        self.settings.highRiskScope = Decimal(str(results[10]))  # highRiskScope
                        self.settings.isAutoSend = results[11]  # settings.isAutoSend
                        self.settings.send_units = Decimal(str(results[12]))  # settings.send_units
                        self.settings.send_ko_name = results[13]  # settings.send_ko_name
                        self.settings.send_en_name = results[14]  # settings.send_en_name
                        self.settings.send_exchange_name = results[15] # settings.send_exchange_name
                        self.settings.send_address = results[16]  # send_addres
                        self.settings.send_destination = results[17]  # settings.send_destination
                        self.settings.telegram = results[19] #18은 created_at
                        self.settings.highRisk = results[20] 
                        self.settings.highRiskValue = Decimal(str(results[21]))
                        self.settings.bit_fee = Decimal(str(results[22]))
                        self.settings.up_fee = Decimal(str(results[23]))

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
                        self.userinfo.b_key = results[2]  # memid
                        self.userinfo.b_skey = results[3]  # memid
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



    def changeDecimal(self, value, count):
        try:
            if isinstance(value, str):
                value = Decimal(value)
            elif value is None:
                value = Decimal('0')
            elif isinstance(value, (int, float)):
                value = Decimal(str(value))  # float을 직접 변환하는 대신 문자열로 변환
            elif not isinstance(value, Decimal):
                raise TypeError("Unsupported type for value")

            result = value.quantize(Decimal('1.' + '0' * count), rounding=ROUND_DOWN)
            return result.normalize()
        except (InvalidOperation, ValueError):
            return Decimal('0').quantize(Decimal('1.' + '0' * count))


    async def info_message(self, market, trade_info, order_id, total_today):
           
        bot = telegram.Bot(token=self.settings.telegram)
        if self.userinfo.memid == 1:
            # 내꺼
            chat_id = '6380176264'
        elif self.userinfo.memid ==2:
            # 명규꺼
            chat_id = '5932188889'

        bit_coin = self.coinSet['bit']['coin_amount']
        bit_krw = self.coinSet['bit']['krw_price']
        up_coin = self.coinSet['up']['coin_amount']
        up_krw = self.coinSet['up']['krw_price']
        
        buy_order_id = trade_info.buy_id
        buy_price = self.changeDecimal(trade_info.buy_price,2)        
        buy_amount = trade_info.buy_amount
        bought_amount = self.changeDecimal(trade_info.bought_amount,8)
        buy_remaining_amount = trade_info.buy_remaining_amount
        
        # sell_price는 매수 신청시 예상 판매금액, 실제 판매 된 금액은 sold_price
        sell_price = self.changeDecimal(trade_info.sell_price,2)
        sold_price = self.changeDecimal(trade_info.sold_price,2)
        sold_amount = self.changeDecimal(trade_info.sold_amount,8)
        thread_id = trade_info.thread_id

        if market == 'bit':
            buy_fee = self.settings.bit_fee
            sell_fee = self.settings.up_fee
        else:
            buy_fee = self.settings.up_fee
            sell_fee = self.settings.bit_fee

        fee = self.changeDecimal(sold_price * sell_fee,5) + self.changeDecimal(buy_price * buy_fee,5)
        diff = self.changeDecimal(sold_price - buy_price,3)
        money = self.changeDecimal(diff - fee,3)
        
        # sell_price는 매수 신청시 예상 판매금액, 실제 판매 된 금액은 sold_price
        estimated_diff = sell_price - buy_price

        # 대기 메시지가 왔을 때 넣은 차익. 이게 원래 차익이어야 하는데, 판매하면서 가격이 떨어지면 diff가 낮아짐.
        got_money = self.changeDecimal(money*sold_amount,2)
        
        log_str = f"[{thread_id}]차익발생,{market},수익:{got_money},차액:{money}({diff})매수:{buy_price},매도:{sold_price},수수료:{fee}, 매도량:[{sold_amount}/{bought_amount}],총 수익:{total_today}, bit_coin_amount:{bit_coin},bit_coin_amount:{up_coin},total_kwr:{int(bit_krw+up_krw)}, bit:{int(bit_krw)}, up:{int(up_krw)}, mode:{trade_info.isChange}"
        self.insertLog(log_str,thread_id,"차익발생")

        
        direction = "업비트->빗썸" if market=='up' else "빗썸->업비트"
        sell_exchange = "빗썸" if market=='up' else "업빗"
        buy_exchange = "업빗" if market=='up' else "빗썸"

        text = f"{self.coin}({direction}) 수익:{got_money:9.2f}원\n"
        text += f"실차액:{money:3.3f}원, 수수료:{fee:3.3f}원\n"
        text += f"매도:{sold_amount:6.2f}개, 차액:{diff:3.3f}원({estimated_diff:3.3f}원)\n"
        text += f"매수:{bought_amount:6.2f}개, 신청{buy_amount}개(남음:{buy_remaining_amount:6.2f}개)\n"
        text += f"{sell_exchange}매도:{sold_price:9.2f}원\[{sell_price:9.2f}원]\n"
        text += f"{buy_exchange}매수:{buy_price:9.2f}원\n"

        text += f"\[빗썸] 코인:{bit_coin:8.2f} 현금:{bit_krw:9.2f}원\n"
        text += f"\[업빗] 코인:{up_coin:8.2f} 현금:{up_krw:9.2f}원\n"
        text += f"\[총합] 코인:{bit_coin + up_coin:8.2f} 현금:{bit_krw + up_krw:9.2f}원\n"
        text += f"오늘 수익 : {total_today:8.2f}\n"
        
        if trade_info.isChange == 0 :
            text = text + "일반모드"
        elif trade_info.isChange == 1 :    
            text = text + "리스크모드"
        else :
            text = text + "퀵모드"
        
        text = text + f"\[" + trade_info.success_time.strftime("%H:%M:%S.%f")[:-3] + "]"
        text = text + "[{:5d}]\n".format(thread_id)
        text = text + f"매수:{order_id}\n"
        text = text + f"매도:{buy_order_id}" 
        await bot.send_message(chat_id, text, parse_mode="Markdown")
    
    async def error_message(self, error_id, coin, err_log_str=""):

        bot = telegram.Bot(token=self.settings.telegram)
        # telgegram주소 바꿔도 밑에 ID가 안 맞으면 안되는 듯, 나한테 날라왔었음.
        if self.userinfo.memid == 1:
            # 내꺼
            chat_id = '6380176264'
        elif self.userinfo.memid ==2:
            # 명규꺼
            chat_id = '5932188889'

        
        
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
