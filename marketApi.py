import jwt
import hashlib
import os
import requests
import uuid
import time
from urllib.parse import urlencode, unquote
from datetime import datetime
from dataclasses import dataclass
from requests.exceptions import RequestException

@dataclass
class Res:
    success: bool
    data: any = None
    error: str = None

class marketApiClass:
  access_key = '';
  secret_key = '';
  

  def __init__(self, coin, market, access_key, secret_key):
    self.coin = coin
    self.market = market
    if market == 'up':
      self.server_url = 'https://api.upbit.com';
    else:
      self.server_url = 'https://api.bithumb.com';
    
    self.access_key = access_key;
    self.secret_key = secret_key;
    self.req = {'get': requests.get,'post': requests.post,'delete': requests.delete}
  
  def getBalance(self):
          
    payload = {
        'access_key': self.access_key,
        'nonce': str(uuid.uuid4())
    }

    if self.market == 'bit':
      payload['timestamp'] = round(time.time() * 1000)

    jwt_token = jwt.encode(payload, self.secret_key)
    authorization = 'Bearer {}'.format(jwt_token)
    headers = {
      'Authorization': authorization,
    }

    try :
      result = requests.get(self.server_url + '/v1/accounts', headers=headers)

      return Res(success=True, data=result)
    
    except RequestException as e:
      print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}]Request getBalance failed: {e}")
      return Res(success=False, error=str(e))

    
  
  def sendApi(self,method, params,addr):
    
    query_string = unquote(urlencode(params, doseq=True)).encode("utf-8")

    m = hashlib.sha512()
    m.update(query_string)
    query_hash = m.hexdigest()

    payload = {
        'access_key': self.access_key,
        'nonce': str(uuid.uuid4()),
        'query_hash': query_hash,
        'query_hash_alg': 'SHA512',
    }

    if self.market == 'bit':
      payload['timestamp'] = round(time.time() * 1000)  

    jwt_token = jwt.encode(payload, self.secret_key)
    authorization = 'Bearer {}'.format(jwt_token)
    headers = {
      'Authorization': authorization,
    }
   
    url = self.server_url + f'/v1/{addr}'


    #print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}][{url}][{method}][{params}][{headers}]")
    try :
      if method == 'post':
        result =  self.req[method](url, json=params, headers=headers)
      else:
        result = self.req[method](url, params=params, headers=headers)

      return Res(success=True, data=result)
    
    except RequestException as e:
      print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}]Request sendApi failed: {e}")
      return Res(success=False, error=str(e))
            
  def send_coinlist(self,coin, state):
    params = {
      'currency': coin,
      'state': state
    }

    # 최대 100개, 기본 100개이고, 페이지를 지정할 수 있는데. 페이지에는 100개씩 들어있겠지
    # 페이지를 변경해가면서 읽어와서 오늘날짜나, 이번달까지인거를 찾아서 그때꺼까지 수량을 카운트 해야겠지.
    
    return self.sendApi('get', params, 'withdraws')
  
  def sell(self,thread_id,units):
    params = {
      'market': self.coin,
      'side': 'ask',
      'ord_type': 'market', #limit은 지정가, market 시장가. 대신 price 값을 null로 해야함.
      'volume': str(units)
    }

    print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}][{thread_id}]{self.market}매도직전 ")
    result = self.sendApi('post', params, 'orders')
    print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}][{thread_id}]{self.market}매도직후2 result:{result.data.json()} ")

    return result
  
  def sell_limit(self,units, price):
    params = {
      'market': self.coin,
      'price' : str(price),
      'side': 'ask',
      'ord_type': 'limit', #limit은 지정가, market 시장가. 대신 price 값을 null로 해야함.
      'volume': str(units)
    }
    
    return self.sendApi('post', params, 'orders')
  
  def buy(self, sell_value, units):
    
    params = {
      'market': self.coin,
      'side': 'bid',
      'ord_type': 'limit', #limit은 지정가, price 시장가. 대신 price 값을 null로 해야함.
      'price': str(sell_value),
      'volume': str(units)
    }

    
    return self.sendApi('post', params, 'orders')

  def check(self,order_id):
    params = {
      'uuid': order_id
    }
    
    return self.sendApi('get', params, 'order')
  
  def cancel(self,order_id):
    params = {
      'uuid': order_id
    }
    
    return self.sendApi('delete', params, 'order')


  def sendCoin(self,params):

    query_string = unquote(urlencode(params, doseq=True)).encode("utf-8")

    m = hashlib.sha512()
    m.update(query_string)
    query_hash = m.hexdigest()

    payload = {
        'access_key': self.access_key,
        'nonce': str(uuid.uuid4()),
        'query_hash': query_hash,
        'query_hash_alg': 'SHA512',
    }

    jwt_token = jwt.encode(payload, self.secret_key)
    authorize_token = 'Bearer {}'.format(jwt_token)
    headers = {
      'Authorization': authorize_token,
    }

    try:
      result = requests.post(self.server_url + '/v1/withdraws/coin', json=params, headers=headers)
      return Res(success=True, data=result)
    
    except RequestException as e:
      print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}]Request sendCoin failed: {e}")
      return Res(success=False, error=str(e))
    #print(res)
    #print(res.json())
    return res

