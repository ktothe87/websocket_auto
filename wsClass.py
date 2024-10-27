import websocket  # websocket-client
import threading
from datetime import datetime


class wsClass(threading.Thread):  

    def __init__(self, coin,mode, revc_func):
        threading.Thread.__init__(self)
        self.ws = None
        self.coin = coin
        self.mode = mode
        if self.mode == "up":
            self.ws_url = "wss://api.upbit.com/websocket/v1";
        else:
            self.ws_url = "wss://ws-api.bithumb.com/websocket/v1";    
        self.new_on_message = revc_func;
        self.running = True
        self.reconnect_needed = False
        self.event_occurred = False
        self.log_str = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}]wsClass,init,{self.coin},{self.mode}"
        print(self.log_str)

    def on_open(self, ws):
        log_str = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}]wsClass,connected,{self.coin},{self.mode}"
        print(log_str)
        #if self.mode == 'up':
        # 업빗, 빗썸 동일
        ws_msg = '[{{"ticket": "test"}},{{"type": "orderbook","codes": ["KRW-{}.5"]}},{{"format": "DEFAULT"}}]'.format(self.coin)
        self.ws.send(ws_msg)

        ws_msg = "PING"
        self.ws.send(ws_msg)

    def on_message(self, ws,message):
        self.new_on_message(ws,message,self.mode)


    def on_error(self,ws,err):
        self.reconnect_needed = True
        log_str = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}]wsClass,error1,{self.coin},{self.mode},{err}"
        print(log_str)

    

    def on_close(self,ws, status_code, msg):
        self.reconnect_needed = True
        log_str = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}]wsClass,close,{self.coin},{self.mode},status_code:{status_code},msg:{msg}"
        print(log_str)

    def run(self):
        while self.running:
            try:
                self.reconnect_needed = False
                self.ws = websocket.WebSocketApp(self.ws_url,
                                                 on_message=self.on_message,
                                                 on_error=self.on_error,
                                                 on_close=self.on_close,
                                                 on_open=self.on_open)
                self.ws.run_forever()
            except Exception as e:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] {self.coin},{self.mode} Unexpected exception in WebSocket connection: {e}")
                self.reconnect_needed = True
            
            if self.running and self.reconnect_needed:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] {self.coin},{self.mode} Reconnecting to {self.ws_url} ...")
                #time.sleep(5)

    def stop(self):
        self.running = False
        if self.ws:
            self.ws.close()
        
