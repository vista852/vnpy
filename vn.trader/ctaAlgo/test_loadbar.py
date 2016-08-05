from __future__ import division
from collections import defaultdict
import numpy as np
import pymysql
import time
import talib
from ctaBase import *
conn = pymysql.connect(host='56533bf41fb88.gz.cdb.myqcloud.com',user='radarwinBitrees',passwd='jDt63iDH72df3',db='bitrees',port=14211)
cur = conn.cursor()
backday = 120
cur.execute('SELECT open,high,low,close,volumn,date FROM okcn_btc_cny_30 ORDER BY date DESC LIMIT 1,%d' % backday)
data = cur.fetchall()
datalength = len(data)
l = []
if cur:
    for d in range(datalength):
        bar = CtaBarData()
        bar.open = data[d][0]
        bar.high = data[d][1]
        bar.low = data[d][2]
        bar.close = data[d][3]
        bar.volume = data[d][4]
        bar.date = data[d][5]
        bar.symbol = 'BTC_CNY_SPOT'
        bar.vtSymbol = 'BTC_CNY_SPOT'
        l.append(bar)
        

        

