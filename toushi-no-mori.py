# coding: UTF-8
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import chromedriver_binary
import time
import requests
import json
import hmac
import hashlib
from datetime import datetime

#ログファイルのファイル名
logFile = 'log_' + datetime.now().strftime('%Y-%m-%d') + '.txt'

#トレンド初期化
trend = 'NEUTRAL'

#取引する通貨と取引ごとの数量を入力
symbol = "BTC_JPY"
amount = 0.01

#GMOコインのAPIのキーを入れる
apiKey    = 'YOUR API KEY'
secretKey = 'YOUR SECRET KEY'

def fWrite(fileName, a, b, c, d):
    f = open(fileName, 'w')
    f.write(a + '\n')
    f.write(b + '\n')
    f.write(c + '\n')
    f.write(d + '\n')
    f.close()

def logWrite(fileName, content):
    log = open(fileName, 'a')
    log.write(datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ' ' + content + '\n')
    log.close()

def printt(content):
    print(datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ' ' + content)

def logPrintt(fileName, content):
    logWrite(fileName,content)
    printt(content)

def getData():
    global lastTrend
    global trend
    global price
    global gmoPrice

    lastTrend = trend

    #GMOにおける価格を取得
    res = requests.get('https://api.coin.z.com/public/v1/ticker?symbol=BTC')
    jsonData = res.json()
    gmoPrice = jsonData["data"][0]["last"]

#投資の森からスクレイピング
    driver.get("https://nikkeiyosoku.com/crypto/bitcoin/")
    time.sleep(8)
    html = driver.page_source.encode('utf-8')
    soup = BeautifulSoup(html, "html.parser")
#価格を取得
    priceData = soup.find('div', class_ = 'stock-txt')
    price = priceData.text[0:priceData.text.find('.')].replace(',', '')
#トレンドを取得
    trendData = soup.find('div', class_ = 'm-t10')
    BUY = '買' in trendData.text
    SELL = '売' in trendData.text
    NEUTRAL = '中' in trendData.text
    if BUY == 1:
        trend = 'BUY'
    elif SELL == 1:
        trend = 'SELL'
    else:
        trend = 'NEUTRAL'

    logPrintt(logFile ,'[data] 現在値 ' + price + '  トレンド ' + trend)

def getSummary():
    global positionRate
    global positionProfit
    global positionSide
    global positionQuantity
    timestamp = '{0}000'.format(int(time.mktime(datetime.now().timetuple())))
    method    = 'GET'
    endPoint  = 'https://api.coin.z.com/private'
    path      = '/v1/positionSummary'

    text = timestamp + method + path
    sign = hmac.new(bytes(secretKey.encode('ascii')), bytes(text.encode('ascii')), hashlib.sha256).hexdigest()
    parameters = {
        "symbol": symbol
        }

    headers = {
        "API-KEY": apiKey,
        "API-TIMESTAMP": timestamp,
        "API-SIGN": sign
        }

    res = requests.get(endPoint + path, headers=headers, params=parameters)
    jsonData = res.json()

    if len(jsonData["data"]["list"]) == 0:
        positionRate = "None"
        positionProfit = "None"
        positionSide = "None"
        positionQuantity = "None"
        fWrite("position.txt", "None", "None", "None", "None")
        logPrintt(logFile, '[info] 建玉はありません')

    else:
        positionRate = jsonData["data"]["list"][0]["averagePositionRate"]
        positionProfit = jsonData["data"]["list"][0]["positionLossGain"]
        positionSide = jsonData["data"]["list"][0]["side"]
        positionQuantity = jsonData["data"]["list"][0]["sumPositionQuantity"]
        message = '[summary] ポジション:' + positionSide + ' 建玉レート:' + positionRate + ' 数量:' + positionQuantity + ' 評価損益:' + positionProfit
        fWrite("position.txt", positionRate, positionProfit, positionSide, positionQuantity)
        logPrintt(logFile, message)

def order(amount, side):
    if positionSide != 'None':
        logPrintt(logFile, '[error]既に建玉があります')
        return

    timestamp = '{0}000'.format(int(time.mktime(datetime.now().timetuple())))
    method    = 'POST'
    endPoint  = 'https://api.coin.z.com/private'
    path      = '/v1/order'
    reqBody = {
        "symbol": symbol,
        "side": side,
        "executionType": "MARKET",
        "size": amount
    }

    text = timestamp + method + path + json.dumps(reqBody)
    sign = hmac.new(bytes(secretKey.encode('ascii')), bytes(text.encode('ascii')), hashlib.sha256).hexdigest()

    headers = {
        "API-KEY": apiKey,
        "API-TIMESTAMP": timestamp,
        "API-SIGN": sign
    }

    res = requests.post(endPoint + path, headers=headers, data=json.dumps(reqBody))
    jsonData = res.json()
    if jsonData["status"] == 0:
        logPrintt(logFile, '[success] 新規建玉を注文しました')
    else:
        logPrintt(json.dumps(res.json(), indent=2))
        logPrintt(logFile, '[error] 建玉注文エラー')

#決済したい建玉のサイドを渡す
def closeOrder(amount,side):
    if side == 'BUY':
        aside = 'SELL'
    elif side == 'SELL':
        aside = 'BUY'
    else:
        logPrintt(logFile, '[error] 決済できる建玉がありません')
        return

    timestamp = '{0}000'.format(int(time.mktime(datetime.now().timetuple())))
    method    = 'POST'
    endPoint  = 'https://api.coin.z.com/private'
    path      = '/v1/closeBulkOrder'
    reqBody = {
        "symbol": symbol,
        "side": aside,
        "executionType": "MARKET",
        "size": amount
    }
    text = timestamp + method + path + json.dumps(reqBody)
    sign = hmac.new(bytes(secretKey.encode('ascii')), bytes(text.encode('ascii')), hashlib.sha256).hexdigest()
    headers = {
        "API-KEY": apiKey,
        "API-TIMESTAMP": timestamp,
        "API-SIGN": sign
    }

    res = requests.post(endPoint + path, headers=headers, data=json.dumps(reqBody))
    jsonData = res.json()
    if jsonData["status"] == 0:
        logPrintt(logFile, '[success] 建玉を決済しました')
    else:
        logPrintt(logFile, json.dumps(res.json(), indent=2))
        logPrintt(logFile, '[error] 建玉決済エラー')

def getResult():
    timestamp = '{0}000'.format(int(time.mktime(datetime.now().timetuple())))
    method    = 'GET'
    endPoint  = 'https://api.coin.z.com/private'
    path      = '/v1/latestExecutions'

    text = timestamp + method + path
    sign = hmac.new(bytes(secretKey.encode('ascii')), bytes(text.encode('ascii')), hashlib.sha256).hexdigest()
    parameters = {
        "symbol": symbol,
        "page": 1,
        "count": 1
        }

    headers = {
        "API-KEY": apiKey,
        "API-TIMESTAMP": timestamp,
        "API-SIGN": sign
        }

    res = requests.get(endPoint + path, headers=headers, params=parameters)
    jsonData = res.json()
    if jsonData["status"] == 0 and len(jsonData["data"]) != 0:
        logPrintt('LossGain.txt', ',決済損益,' + jsonData["data"]["list"][0]["lossGain"])
    else:
        logPrintt('LossGain.txt', '決済損益を取得できませんでした')

def main():
#情報取得
    getData()
    getSummary()
#トレ転時の処理
    if lastTrend != trend:
        logPrintt(logFile, '[info] トレ転しました')
        if positionQuantity != 'None':
            logPrintt(logFile, '[info] 建玉を決済します')
            closeOrder(positionQuantity, positionSide)
            time.sleep(5)
            getSummary()
            getResult()
        if trend != 'NEUTRAL':
            if abs(int(gmoPrice) - int(price)) > 12000:
                logPrintt(logFile, '[error] 取引所価格が現在価格から乖離しています')
            else:
                logPrintt(logFile, '[info] 新規建玉を注文します')
                order(amount, trend)
                time.sleep(5)
                getSummary()

#建玉の判定
    if positionSide != trend and positionSide != 'None':
        logPrintt(logFile, '[info] 建玉がトレンドと違います')
        closeOrder(positionQuantity, positionSide)
        time.sleep(5)
        getSummary()
        getResult()

#ここから本体
print('ビットコイン自動売買システム Ver1.0.1\n')

#ポジション初期化
f = open('position.txt', 'r')
datalist = f.readlines()
positionRate = datalist[0]
positionProfit = datalist[1]
positionSide = datalist[2]
positionQuantity = datalist[3]
f.close()

# ブラウザのオプションを格納する変数をもらってきます。
options = Options()
options.headless = True
# ブラウザを起動する
driver = webdriver.Chrome(options=options)
logPrintt(logFile, '[info] ブラウザ起動成功')
time.sleep(2)
#初期データ読み込み
getData()
getSummary()
logPrintt(logFile, '[info] 初期データ読み込み完了')

MAX_retry = 20

while True:
    for i in range(MAX_retry + 1):
        try:
            main()
        except Exception as e:
            print("Failed!. retry={}/{}".format(i, MAX_retry))
            logPrintt(logFile, '[error] ブラウザを再起動します')

            driver.quit()
            driver = webdriver.Chrome(options=options)
            logPrintt(logFile, '[info] ブラウザ起動成功')
            time.sleep(10)
        else:
            break
    else:
        logPrintt(logFile, '[error]致命的エラーが発生しました')

    time.sleep(100)
    for num in range(2):
        getSummary()
        time.sleep(100)
