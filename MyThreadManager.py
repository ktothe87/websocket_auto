from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import threading
import traceback
from dataclasses import dataclass

class MyThreadManager:
    @dataclass
    class trade_info:
        thread_id: str = ""
        buy_id: str = ""
        buy_amount: float = 0
        buy_price: float = 0
        bought_amount: float = 0
        buy_remaining_amount: float = 0
        trade_count: int = 0
        sell_id: str = ""
        sell_amount: float = 0
        sell_price: float = 0
        sold_price: float = 0
        sold_amount: float = 0
        sell_remaining_amount: float = 0
        estimated_diff: float = 0
        isChange: int = 1
        success_time: datetime = datetime(1, 1, 1, second=0)
        trash_coin: float = 0

    def __init__(self, max_workers=10):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.futures = {}
        self.stop_events = {}
        self.thread_counter = 0  # 스레드 카운터 초기화
        self.active_thread_count = 0
        self.lock = threading.Lock()  # 스레드 안전성을 위한 락
        self.orderbook_event = threading.Event()
        self.max_threads = max_workers
        self.trade_list = {}
        
        self.program_run = True   

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

    def create_thread(self, task, market, order_id):
        if order_id in self.futures:
            raise ValueError(f"Thread for order_id {order_id} already exists")
        else:
            stop_event = threading.Event()
            self.stop_events[order_id] = stop_event

            with self.lock:
                self.thread_counter += 1
                self.active_thread_count += 1
                thread_id = self.thread_counter
            
            future = self.executor.submit(self._run_task, task, market, thread_id, order_id, stop_event)
            self.futures[order_id] = future
            
            return thread_id
    
    def add_trade(self, buy_id,buy_amount, buy_price, buy_remaining_amount, estimated_diff, mode, trade_count):
        add_trade = self.trade_info()
        add_trade.buy_id = buy_id
        add_trade.buy_amount = self.cutFloat(buy_amount,8)
        add_trade.buy_price = self.cutFloat(buy_price,2)
        add_trade.buy_remaining_amount = self.cutFloat(buy_remaining_amount,8)
        add_trade.estimated_diff = self.cutFloat(estimated_diff,5)
        add_trade.isChange = mode
        add_trade.trade_count = int(trade_count)

        self.trade_list[buy_id] = add_trade

        return add_trade

    def get_trade(self,buy_id):
        if buy_id in self.trade_list:
            res = self.trade_list[buy_id]
        else:
            res = None

        return res
        

    
    def _run_task(self, task, market, thread_id, order_id, stop_event):
        try:
            task(market, thread_id, order_id, stop_event)

            #print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}][{thread_id}][{order_id}] [MyApi]쓰레드 _run_task 완료 stop_event:{stop_event}, ({task.__name__}))")
            
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}][{market}][{thread_id}][{order_id}] [MyApi]쓰레드 에러 발생 ({task.__name__}), {str(e)}\n{traceback.format_exc()}")
    
    def get_total_units(self,market,order_id=-1):
        with self.lock:
            tot_buy_req_amount = 0
            
            # -1 이면 진입전으로 아이디 없고, 다른게 돌고 있다면 그거 다 더해야함.
            #if thread_id != -1:
            # 그냥 돌리면 어차피 -1이란 아이디 없을테니 총합이 될거고.
            # 쓰레드가 없음으면 0을 반환하겠지.
            if self.active_thread_count > 0:
                for key, trade_info in self.trade_list.items() :
                    # 빗썸이면 업빗 오더는 스킵하고, 업빗이면 빗썸물량 스킵.
                    if (market == 'bit' and not key.startswith('C')) or (market == 'up' and key.startswith('C')) :
                        continue    

                    if key == order_id:
                        break
                    # 기본적으로 신청량의 총계를 구하는데, 이미 매수가 되었다면 매수된 양을 더함
                    # 매수가 성사되고 매도까지 길어야 0.몇초이긴한데, 그 사이에도 진입체크는 계속 되니까.
                    # 실제로 이 짧은 타이밍 때문에 코인오버에 걸렸음. 그래서 여기도 처리함.
                    # if current_coin.buy_amount > 0 :
                    #     tot_buy_req_amount += current_coin.buy_amount 
                    # else:    
                    #     tot_buy_req_amount += current_coin.buy_req_amount 
                    tot_buy_req_amount += trade_info.buy_remaining_amount

            return tot_buy_req_amount
    
    def stop_thread(self, order_id, thread_id=-1):
        print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}][MyApi]stop_threads 시작 {order_id}")
        if order_id in self.stop_events:
            self.stop_events[order_id].set()
            self.orderbook_event.set()
            self.futures[order_id].result()  # 스레드 완료 대기
            with self.lock:
                self.active_thread_count -= 1
                del self.stop_events[order_id]
                del self.futures[order_id]
                del self.trade_list[order_id]
            print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}][{thread_id}] 666666666666666 [MyApi]stop_threads 종료 {order_id}")
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}][MyApi]stop_threads {order_id} 못찾음.")

    def stop_all_threads(self):
        print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}][{self.active_thread_count}][MyApi]stop_all_threads 시작")
        self.program_run = False
        # futures의 복사본을 만들어 반복
        futures_copy = list(self.futures.values())
        for future in futures_copy:
            self.orderbook_event.set()
            future.result()  # 모든 스레드 완료 대기
            self.active_thread_count -= 1
            print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}][{self.active_thread_count}][MyApi]stop_all_threads")
        self.futures.clear()
        self.stop_events.clear()
        self.trade_list.clear()
        futures_copy.clear()
        print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}][{self.active_thread_count}][MyApi]stop_all_threads 종료")

    def shutdown(self):
        #self.stop_all_threads()
        self.program_run = False
        self.orderbook_event.set()
        self.executor.shutdown(wait=True)