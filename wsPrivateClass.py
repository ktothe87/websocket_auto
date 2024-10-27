import websocket  # websocket-client
import threading
from datetime import datetime
import jwt
import uuid
import time
import json

#websocket.enableTrace(True)

class wsPrivateClass(threading.Thread):  

    def __init__(self, coin,mode, revc_func,access_key="", secret_key=""):
        threading.Thread.__init__(self)
        self.ws = None
        self.coin = coin
        self.mode = mode
        if self.mode == "bit":
            self.ws_url = "wss://ws-api.bithumb.com/websocket/v1/private"
        else:
            self.ws_url = "wss://api.upbit.com/websocket/v1/private"
        self.access_key = access_key;
        self.secret_key = secret_key;    
        self.new_on_message = revc_func;
        self.running = True
        self.reconnect_needed = False
        self.event_occurred = False
        self.log_str = "" #f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}]wsPrivateClass,init,{self.coin},{self.mode},{self.ws_url}"
        #print(self.log_str)
  
    
    def makeAuthHeader(self):

        payload = {
            'access_key': self.access_key,
            'nonce': str(uuid.uuid4()),
            'timestamp': round(time.time() * 1000)
        }

        jwt_token = jwt.encode(payload, self.secret_key)
        authorization = 'Bearer {}'.format(jwt_token)
        header = {
        'Authorization': authorization,
        }
        #print(authorization)
        return header

    def on_open(self,ws):
        log_str = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}]wsPrivateClass,connected,{self.coin},{self.mode}"
        print(log_str)
        ws_data = [
            {"ticket": str(uuid.uuid4())},
            {"type": "myOrder", "codes": [f"KRW-{self.coin}"]},
            {"type": "myAsset"}
        ]

        ws_msg = json.dumps(ws_data)
        self.ws.send(ws_msg)
        ws_msg = "PING"
        self.ws.send(ws_msg)


    def on_error(self,ws,err):
        self.reconnect_needed = True
        log_str = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}]wsPrivateClass,error1,{self.coin},{self.mode},{err}"
        print(log_str)

    def on_message(self, ws,message):
        self.new_on_message(ws,message, self.mode)
    

    def on_close(self,ws,status_code, msg):
        #self.reconnect_needed = True
        log_str = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}]wsPrivateClass,close,{self.coin},{self.mode}status_code:{status_code},msg:{msg}"
        print(log_str)

    def run(self):
        while self.running:
            try:    
                header = self.makeAuthHeader()
                self.reconnect_needed = False
                self.ws = websocket.WebSocketApp(self.ws_url,
                                                 header=header,
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
