# encoding: UTF-8

"""
一个ATR-RSI指标结合的交易策略，适合用在股指的1分钟和5分钟线上。

注意事项：
1. 作者不对交易盈利做任何保证，策略代码仅供参考
2. 本策略需要用到talib，没有安装的用户请先参考www.vnpy.org上的教程安装
3. 将IF0000_1min.csv用ctaHistoryData.py导入MongoDB后，直接运行本文件即可回测策略

"""

from ctaBase import *
from ctaTemplate import CtaTemplate

import talib
import numpy as np


########################################################################
class Bolling(CtaTemplate):
    """结合ATR和RSI指标的一个分钟线交易策略"""
    className = 'Bolling'
    author = u'Vista'
    #mysql参数
    host = 'localhost'
    user = 'root'
    passwd = 'root'
    db = 'tradelog'
    port = 3306
    tablename = 'okcoin_ltc'
    # 策略参数
    bollingLength = 30
    atrFactor = 6
    atrLength = 15  # 计算ATR指标的窗口数
    maLength = 20  # 计算A均线的窗口数
    trailingPercent = 0.2  # 百分比移动止损
    initDays = 50  # 初始化数据所用的天数

    # 策略变量
    bar = None  # K线对象
    barMinute = EMPTY_STRING  # K线当前的分钟
    datacount = 0
    bufferSize = 30  # 需要缓存的数据的大小
    bufferCount = 0  # 目前已经缓存了的数据的计数
    atrCount = 0
    highArray = np.zeros(bufferSize)  # K线最高价的数组
    lowArray = np.zeros(bufferSize)  # K线最低价的数组
    closeArray = np.zeros(bufferSize)  # K线收盘价的数组
    typpArray = np.zeros(bufferSize)  # K线均价数组
    typp = 0
    upLineArray = np.zeros(bufferSize)
    upLine = 0
    lowLineArray = np.zeros(bufferSize)
    lowLine = 0
    midLineArray = np.zeros(bufferSize)
    midLine = 0
    atrArray = np.zeros(bufferSize)
    atrValue = 0
    trendMa = 0
    lasttrendMa = 0
    trendMaArray = np.zeros(bufferSize)

    entryPrice = 0
    signal = 0
    intraTradeHigh = 0.1  # 移动止损用的持仓期内最高价
    intraTradeLow = 9999.99999  # 移动止损用的持仓期内最低价
    longStop = 0  # 多单止损价
    shortStop = 10000  # 空单止损价
    orderList = []  # 保存委托代码的列表
    lasttradetype = 0
    lastpos = 0
    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol',
                 'bollingLength',
                 'atrLength',
                 'atrFactor',
                 ]

    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'signal',
               'pos',
               'entryPrice',
               'upLine',
               'lowLine',
               'longStop',
               'shortStop',
               'intraTradeHigh',
               'intraTradeLow'
               ]

    # ----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(Bolling, self).__init__(ctaEngine, setting)

        # 注意策略类中的可变对象属性（通常是list和dict等），在策略初始化时需要重新创建，
        # 否则会出现多个策略实例之间数据共享的情况，有可能导致潜在的策略逻辑错误风险，
        # 策略类中的这些可变对象属性可以选择不写，全都放在__init__下面，写主要是为了阅读
        # 策略时方便（更多是个编程习惯的选择）

    # ----------------------------------------------------------------------
    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略初始化' % self.name)


        # 载入历史数据，并采用回放计算的方式初始化策略数值
        initData = self.loadbitressdata(self.initDays)

        lasttradedata = self.readtradelog2mysql()
        if lasttradedata:
            self.lasttradetype = lasttradedata[0][6]
            self.lastpos = lasttradedata[0][7]
            print 'lasttradetype is :',self.lasttradetype
            if self.lasttradetype == None:
                print 'this no trade before'
                self.lasttradetype = 0
                self.intraTradeHigh = 0
                self.intraTradeLow = 9999999.9999
            elif self.lasttradetype == 1:
                if self.lastpos == 0:

                    self.intraTradeHigh = lasttradedata[0][3]
                    print 'last trade is long,and intratradehigh = ',self.intraTradeHigh
                elif self.lastpos == 1:
                    self.intraTradeHigh = float(self.getperioddata(lasttradedata[0][5],'high'))
                    self.pos = 1
                    self.entryPrice = lasttradedata[0][2]
                    print 'last trade is long and not closed yet'

            elif self.lasttradetype == -1:
                if self.lastpos == 0:
                    self.intraTradeLow = lasttradedata[0][4]
                    print 'last trade is short,and intratradelow = ', self.intraTradeLow
                elif self.lastpos == -1:
                    self.intraTradeLow = float(self.getperioddata(lasttradedata[0][5],'low'))
                    self.pos = -1
                    self.entryPrice = lasttradedata[0][2]
                    print 'last trade is short and not closed yet,intratradelow = ',self.intraTradeLow
        else:
            self.lasttradetype =0
            self.pos = 0
            self.lastpos = 0
            self.intraTradeLow = 9999.99999
            self.intraTradeHigh = 0
        for bar in initData:
            self.onBar(bar)
        print self.intraTradeHigh,self.intraTradeLow
        self.log("初始化")
        self.putEvent()

    # ----------------------------------------------------------------------
    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略启动' % self.name)
        self.putEvent()
        self.log("策略启动")

    # ----------------------------------------------------------------------
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略停止' % self.name)
        self.putEvent()
        self.log("策略停止")

    # ----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        # 计算K线
        tickMinute = tick.datetime.minute
        #print tickMinute , self.barMinute

        # 当推送来的tick数据分钟数不等于指定周期时，生成新的K线
        #if tickMinute != self.barMinute:    #一分钟
        if ((tickMinute != self.barMinute and tickMinute % 5 == 0) or not self.bar):  #五分钟
            if self.bar:
                self.onBar(self.bar)

            bar = CtaBarData()
            bar.vtSymbol = tick.vtSymbol
            bar.symbol = tick.symbol
            bar.exchange = tick.exchange

            bar.open = tick.lastPrice
            bar.high = tick.lastPrice
            bar.low = tick.lastPrice
            bar.close = tick.lastPrice

            bar.date = tick.date
            bar.time = tick.time
            bar.datetime = tick.datetime  # K线的时间设为第一个Tick的时间

            self.bar = bar  # 这种写法为了减少一层访问，加快速度
            self.barMinute = tickMinute  # 更新当前的分钟
            print 'K线已更新，最近K线时间：',self.barMinute,self.bar
        else:  # 否则继续累加新的K线
            bar = self.bar  # 写法同样为了加快速度
            bar.high = max(bar.high, tick.lastPrice)
            bar.low = min(bar.low, tick.lastPrice)
            bar.close = tick.lastPrice

        # 判断是否开仓
        if self.pos == 0 and self.signal == 1 and bar.close > self.upLineArray[-1]:
            self.pos = 1
            self.entryPrice = bar.close
            self.shortStop = 0
            self.intraTradeHigh = bar.close
            self.intraTradeHigh = max(self.intraTradeHigh, bar.high)
            self.lasttradetype = 1
            value = ['buyopen',bar.close,0,0,bar.datetime,self.lasttradetype,self.pos]
            self.writetradelog2mysql(value)
        if self.pos == 0 and self.signal == -1 and bar.close < self.lowLineArray[-1]:
            self.pos = -1
            self.entryPrice = bar.close
            self.longStop = 0
            self.intraTradeLow = bar.close
            self.intraTradeLow = min(self.intraTradeLow, bar.low)
            self.lasttradetype = -1
            value = ['sellopen',bar.close,0,0,bar.datetime,self.lasttradetype,self.pos]
            self.writetradelog2mysql(value)

        #持仓状态下判断出场
        if self.pos == 1:
            self.intraTradeHigh = max(self.intraTradeHigh, bar.high)
            self.longStop = self.intraTradeHigh - self.atrArray[-1]*self.atrFactor
            if bar.close < self.longStop:
                self.pos = 0
                self.entryPrice = 0
                self.lasttradetype = 1
                value = ['sellcover', bar.close, self.intraTradeHigh, 0, bar.datetime, self.lasttradetype,self.pos]
                self.writetradelog2mysql(value)
        if self.pos == -1:
            self.intraTradeLow = min(self.intraTradeLow, bar.low)

            self.shortStop = self.intraTradeLow + self.atrArray[-1]*self.atrFactor
            if bar.close > self.shortStop:
                self.pos = 0
                self.entryPrice = 0
                self.lasttradetype = -1
                value = ['buycover', bar.close,0, self.intraTradeLow, bar.datetime, self.lasttradetype,self.pos]
                self.writetradelog2mysql(value)

    # ----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        # 撤销之前发出的尚未成交的委托（包括限价单和停止单）
        for orderID in self.orderList:
            self.cancelOrder(orderID)
        self.orderList = []

        # 保存K线数据
        self.closeArray[0:self.bufferSize - 1] = self.closeArray[1:self.bufferSize]
        self.highArray[0:self.bufferSize - 1] = self.highArray[1:self.bufferSize]
        self.lowArray[0:self.bufferSize - 1] = self.lowArray[1:self.bufferSize]

        self.closeArray[-1] = bar.close
        self.highArray[-1] = bar.high
        self.lowArray[-1] = bar.low
        self.typpArray =(self.closeArray+self.highArray+self.lowArray)/3
        self.typp = (bar.close+bar.high+bar.low)/3
        self.bufferCount += 1
        if self.bufferCount < self.bufferSize:
            print self.bufferCount, self.bufferSize
            return

        # 计算指标数值
        self.atrValue = talib.ATR(self.highArray,
                                  self.lowArray,
                                  self.closeArray,
                                  self.atrLength)[-1]

        self.atrArray[0:self.bufferSize - 1] = self.atrArray[1:self.bufferSize]
        self.atrArray[-1] = self.atrValue
        self.trendMaArray = talib.MA(self.typpArray,self.maLength)
        self.trendMa = self.trendMaArray[-1]
        self.lasttrendMa = self.trendMaArray[-2]
        bbtemp = talib.BBANDS(self.closeArray,self.bollingLength)
        self.upLine = bbtemp[0][-1]
        self.lowLine = bbtemp[2][-1]
        self.midLine = bbtemp[1][-1]

        self.upLineArray[0:self.bufferSize-1] = self.upLineArray[1:self.bufferSize]
        self.upLineArray[-1] = self.upLine

        self.lowLineArray[0:self.bufferSize-1] = self.lowLineArray[1:self.bufferSize]
        self.lowLineArray[-1] = self.lowLine

        self.midLineArray[0:self.bufferSize-1] = self.midLineArray[1:self.bufferSize]
        self.midLineArray[-1] = self.midLine

        self.atrCount += 1
        #print self.upLineArray[-2],self.atrCount

        if self.atrCount < 3:
            return
        #print bar.datetime
        # 判断是否要进行交易
        print self.intraTradeLow , self.atrArray[-1] * self.atrFactor
        print type(self.intraTradeLow), type(self.atrArray[-1]*self.atrFactor),self.pos
        # 当前无仓位
        if self.pos == 0:

            # 均线上穿，轨道在均线上/下，轨道突破前持仓高/低，发出信号
            if self.lasttradetype == 0:
                if self.trendMaArray[-1] > self.trendMaArray[-2] and self.upLineArray[
                    -1] > self.trendMaArray[-1] :
                    # 前一单空单的情况下，发出多单信号
                    self.signal = 1
                elif self.trendMaArray[-1] < self.trendMaArray[-2] and self.lowLineArray[
                    -1] < self.trendMaArray[-1]:
                    # 前一单多单情况下，发出空单信号
                    self.signal = -1
                else:
                    self.signal = 0
            elif self.lasttradetype == 1 :
                if self.trendMaArray[-1] > self.trendMaArray[-2] and self.upLineArray[
                    -1] > self.trendMaArray[-1] and self.upLineArray[-1] > self.intraTradeHigh :
                    # 前一单多单的情况下，发出多单信号
                    self.signal = 1
                elif self.trendMaArray[-1] < self.trendMaArray[-2] and self.lowLineArray[
                    -1] < self.trendMaArray[-1] :
                    #前一单多单情况下，发出空单信号
                    self.signal = -1
                else:
                    self.signal = 0

            elif self.lasttradetype == -1:
                if self.trendMaArray[-1] > self.trendMaArray[-2] and self.upLineArray[
                    -1] > self.trendMaArray[-1] :
                    # 前一单空单的情况下，发出多单信号
                    self.signal = 1
                elif self.trendMaArray[-1] < self.trendMaArray[-2] and self.lowLineArray[
                    -1] < self.trendMaArray[-1] and self.lowLineArray[-1] < self.intraTradeLow :
                    # 前一单空单情况下，发出空单信号
                    self.signal = -1
                else:
                    self.signal = 0


        # 发出状态更新事件
        self.putEvent()

    # ----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        pass

    # ----------------------------------------------------------------------
    def onTrade(self, trade):
        pass


if __name__ == '__main__':
    # 提供直接双击回测的功能
    # 导入PyQt4的包是为了保证matplotlib使用PyQt4而不是PySide，防止初始化出错
    from ctaBacktesting import *
    from PyQt4 import QtCore, QtGui

    # 创建回测引擎
    engine = BacktestingEngine()

    # 设置引擎的回测模式为K线
    engine.setBacktestingMode(engine.BAR_MODE)

    # 设置回测用的数据起始日期
    engine.setStartDate('20120101')

    # 设置产品相关参数
    engine.setSlippage(0.2)  # 股指1跳
    engine.setRate(0.3 / 10000)  # 万0.3
    engine.setSize(300)  # 股指合约大小

    # 设置使用的历史数据库
    engine.setDatabase(MINUTE_DB_NAME, 'IF0000')

    # 在引擎中创建策略对象
    d = {'atrLength': 11}
    engine.initStrategy(Bolling, d)

    # 开始跑回测
    engine.runBacktesting()

    # 显示回测结果
    engine.showBacktestingResult()

    ## 跑优化
    # setting = OptimizationSetting()                 # 新建一个优化任务设置对象
    # setting.setOptimizeTarget('capital')            # 设置优化排序的目标是策略净盈利
    # setting.addParameter('atrLength', 11, 12, 1)    # 增加第一个优化参数atrLength，起始11，结束12，步进1
    # setting.addParameter('atrMa', 20, 30, 5)        # 增加第二个优化参数atrMa，起始20，结束30，步进1
    # engine.runOptimization(AtrRsiStrategy, setting) # 运行优化函数，自动输出结果

