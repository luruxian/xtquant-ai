# XtQuant API 文档

## 版本信息更新历史

- **2024-06-27** - 添加外部成交导入接口 `sync_transaction_from_external`
- **2024-05-24** - 添加通用数据导出接口 `export_data`、通用数据查询接口 `query_data`
- **2024-04-25** - 数据结构添加 `stock_code1` 字段以适配长代码
- **2024-02-29** - 添加期货持仓统计查询接口 `query_position_statistics`
- **2024-01-02** - 委托类型增加 ETF 申赎
- **2023-11-03** - 添加券源行情查询接口 `smt_query_quoter`、库存券约券申请接口 `smt_negotiate_order`、约券合约查询接口 `smt_query_compact`
- **2023-10-20** - 委托结构 `XtOrder`、成交结构 `XtTrade`、持仓结构 `XtPosition` 新增多空字段 `direction`、交易操作字段 `offset_flag`
- **2023-10-16** - 添加期货市价的报价类型
- **2023-08-11** - 添加划拨业务查询普通柜台资金接口 `query_com_fund`、查询普通柜台持仓接口 `query_com_position`
- **2023-07-26** - 添加资金划拨接口 `fund_transfer`
- **2023-07-17** - 持仓结构 `XtPosition` 成本价字段调整：`open_price` - 开仓价，`avg_price` - 成本价
- **2022-11-28** - 为主动请求接口的返回增加专用线程以及相关控制，以支持在 `on_stock_order` 等推送接口中调用同步请求 `XtQuantTrader.set_relaxed_response_order_enabled`
- **2022-11-17** - 交易数据字典格式调整
- **2022-11-15** - 修复 `XtQuantTrader.unsubscribe` 的实现
- **2022-06-27** - 委托查询支持仅查询可撤委托，添加新股申购相关接口 `query_new_purchase_limit`、`query_ipo_data`、`query_account_infos`
- **2022-01-19** - 添加账号状态主推接口、账号状态数据结构说明、账号状态枚举值
- **2021-07-20** - 修改回调/主推函数实现机制，提升报撤单回报的速度，降低穿透延时波动；`XtQuantTrader.run_forever()` 修改实现，支持 Ctrl+C 跳出
- **2020-11-19** - 添加异步下单回报推送、异步撤单回报推送接口说明
- **2020-11-13** - 添加信用交易相关类型定义说明、接口说明、异步撤单委托反馈结构说明、下单失败和撤单失败主推结构说明
- **2020-10-21** - 添加信用交易相关委托类型（order_type）枚举调整
- **2020-10-14** - 持仓结构添加字段投资备注相关修正
- **2020-09-01** - 初稿

---

## 快速入门

### 创建策略

```python
#coding=utf-8
from xtquant.xttrader import XtQuantTrader, XtQuantTraderCallback
from xtquant.xttype import StockAccount
from xtquant import xtconstant


class MyXtQuantTraderCallback(XtQuantTraderCallback):
    def on_disconnected(self):
        """
        连接断开
        :return:
        """
        print("connection lost")
    
    def on_stock_order(self, order):
        """
        委托回报推送
        :param order: XtOrder对象
        :return:
        """
        print("on order callback:")
        print(order.stock_code, order.order_status, order.order_sysid)
    
    def on_stock_trade(self, trade):
        """
        成交变动推送
        :param trade: XtTrade对象
        :return:
        """
        print("on trade callback")
        print(trade.account_id, trade.stock_code, trade.order_id)
    
    def on_order_error(self, order_error):
        """
        委托失败推送
        :param order_error:XtOrderError 对象
        :return:
        """
        print("on order_error callback")
        print(order_error.order_id, order_error.error_id, order_error.error_msg)
    
    def on_cancel_error(self, cancel_error):
        """
        撤单失败推送
        :param cancel_error: XtCancelError 对象
        :return:
        """
        print("on cancel_error callback")
        print(cancel_error.order_id, cancel_error.error_id, cancel_error.error_msg)
    
    def on_order_stock_async_response(self, response):
        """
        异步下单回报推送
        :param response: XtOrderResponse 对象
        :return:
        """
        print("on_order_stock_async_response")
        print(response.account_id, response.order_id, response.seq)
    
    def on_account_status(self, status):
        """
        :param response: XtAccountStatus 对象
        :return:
        """
        print("on_account_status")
        print(status.account_id, status.account_type, status.status)


if __name__ == "__main__":
    print("demo test")
    # path为mini qmt客户端安装目录下userdata_mini路径
    path = 'D:\\迅投极速交易终端 睿智融科版\\userdata_mini'
    # session_id为会话编号，策略使用方对于不同的Python策略需要使用不同的会话编号
    session_id = 123456
    xt_trader = XtQuantTrader(path, session_id)
    
    # 创建资金账号为1000000365的证券账号对象
    acc = StockAccount('1000000365')
    # StockAccount可以用第二个参数指定账号类型，如沪港通传'HUGANGTONG'，深港通传'SHENGANGTONG'
    # acc = StockAccount('1000000365','STOCK')
    
    # 创建交易回调类对象，并声明接收回调
    callback = MyXtQuantTraderCallback()
    xt_trader.register_callback(callback)
    
    # 启动交易线程
    xt_trader.start()
    
    # 建立交易连接，返回0表示连接成功
    connect_result = xt_trader.connect()
    print(connect_result)
    
    # 对交易回调进行订阅，订阅后可以收到交易主推，返回0表示订阅成功
    subscribe_result = xt_trader.subscribe(acc)
    print(subscribe_result)
    
    stock_code = '600000.SH'
    
    # 使用指定价下单，接口返回订单编号，后续可以用于撤单操作以及查询委托状态
    print("order using the fix price:")
    fix_result_order_id = xt_trader.order_stock(acc, stock_code, xtconstant.STOCK_BUY, 200, xtconstant.FIX_PRICE, 10.5, 'strategy_name', 'remark')
    print(fix_result_order_id)
    
    # 使用订单编号撤单
    print("cancel order:")
    cancel_order_result = xt_trader.cancel_order_stock(acc, fix_result_order_id)
    print(cancel_order_result)
    
    # 使用异步下单接口，接口返回下单请求序号seq，seq可以和on_order_stock_async_response的委托反馈response对应起来
    print("order using async api:")
    async_seq = xt_trader.order_stock_async(acc, stock_code, xtconstant.STOCK_BUY, 200, xtconstant.FIX_PRICE, 10.5, 'strategy_name', 'remark')
    print(async_seq)
    
    # 查询证券资产
    print("query asset:")
    asset = xt_trader.query_stock_asset(acc)
    if asset:
        print("asset:")
        print("cash {0}".format(asset.cash))
    
    # 根据订单编号查询委托
    print("query order:")
    order = xt_trader.query_stock_order(acc, fix_result_order_id)
    if order:
        print("order:")
        print("order {0}".format(order.order_id))
    
    # 查询当日所有的委托
    print("query orders:")
    orders = xt_trader.query_stock_orders(acc)
    print("orders:", len(orders))
    if len(orders) != 0:
        print("last order:")
        print("{0} {1} {2}".format(orders[-1].stock_code, orders[-1].order_volume, orders[-1].price))
    
    # 查询当日所有的成交
    print("query trade:")
    trades = xt_trader.query_stock_trades(acc)
    print("trades:", len(trades))
    if len(trades) != 0:
        print("last trade:")
        print("{0} {1} {2}".format(trades[-1].stock_code, trades[-1].traded_volume, trades[-1].traded_price))
    
    # 查询当日所有的持仓
    print("query positions:")
    positions = xt_trader.query_stock_positions(acc)
    print("positions:", len(positions))
    if len(positions) != 0:
        print("last position:")
        print("{0} {1} {2}".format(positions[-1].account_id, positions[-1].stock_code, positions[-1].volume))
    
    # 根据股票代码查询对应持仓
    print("query position:")
    position = xt_trader.query_stock_position(acc, stock_code)
    if position:
        print("position:")
        print("{0} {1} {2}".format(position.account_id, position.stock_code, position.volume))
    
    # 阻塞线程，接收交易推送
    xt_trader.run_forever()
```

---

## XtQuant 运行逻辑

XtQuant 封装了策略交易所需要的 Python API 接口，可以和 MiniQMT 客户端交互进行报单、撤单、查询资产、查询委托、查询成交、查询持仓以及收到资金、委托、成交和持仓等变动的主推消息。

---

## XtQuant 数据字典

### 交易市场 (market)

| 市场 | 枚举值 |
|------|--------|
| 上交所 | `xtconstant.SH_MARKET` |
| 深交所 | `xtconstant.SZ_MARKET` |
| 北交所 | `xtconstant.MARKET_ENUM_BEIJING` |
| 沪港通 | `xtconstant.MARKET_ENUM_SHANGHAI_HONGKONG_STOCK` |
| 深港通 | `xtconstant.MARKET_ENUM_SHENZHEN_HONGKONG_STOCK` |
| 上期所 | `xtconstant.MARKET_ENUM_SHANGHAI_FUTURE` |
| 大商所 | `xtconstant.MARKET_ENUM_DALIANG_FUTURE` |
| 郑商所 | `xtconstant.MARKET_ENUM_ZHENGZHOU_FUTURE` |
| 中金所 | `xtconstant.MARKET_ENUM_INDEX_FUTURE` |
| 能源中心 | `xtconstant.MARKET_ENUM_INTL_ENERGY_FUTURE` |
| 广期所 | `xtconstant.MARKET_ENUM_GUANGZHOU_FUTURE` |
| 上海期权 | `xtconstant.MARKET_ENUM_SHANGHAI_STOCK_OPTION` |
| 深证期权 | `xtconstant.MARKET_ENUM_SHENZHEN_STOCK_OPTION` |

### 账号类型 (account_type)

| 账号类型 | 枚举值 |
|---------|--------|
| 期货 | `xtconstant.FUTURE_ACCOUNT` |
| 股票 | `xtconstant.SECURITY_ACCOUNT` |
| 信用 | `xtconstant.CREDIT_ACCOUNT` |
| 期货期权 | `xtconstant.FUTURE_OPTION_ACCOUNT` |
| 股票期权 | `xtconstant.STOCK_OPTION_ACCOUNT` |
| 沪港通 | `xtconstant.HUGANGTONG_ACCOUNT` |
| 深港通 | `xtconstant.SHENGANGTONG_ACCOUNT` |

### 委托类型 (order_type)

#### 股票委托类型

| 类型 | 枚举值 |
|------|--------|
| 股票买入 | `xtconstant.STOCK_BUY` |
| 卖出 | `xtconstant.STOCK_SELL` |

#### 信用交易委托类型

| 类型 | 枚举值 |
|------|--------|
| 信用担保品买入 | `xtconstant.CREDIT_BUY` |
| 担保品卖出 | `xtconstant.CREDIT_SELL` |
| 融资买入 | `xtconstant.CREDIT_FIN_BUY` |
| 融券卖出 | `xtconstant.CREDIT_SLO_SELL` |
| 买券还券 | `xtconstant.CREDIT_BUY_SECU_REPAY` |
| 直接还券 | `xtconstant.CREDIT_DIRECT_SECU_REPAY` |
| 卖券还款 | `xtconstant.CREDIT_SELL_SECU_REPAY` |
| 直接还款 | `xtconstant.CREDIT_DIRECT_CASH_REPAY` |
| 专项融资买入 | `xtconstant.CREDIT_FIN_BUY_SPECIAL` |
| 专项融券卖出 | `xtconstant.CREDIT_SLO_SELL_SPECIAL` |
| 专项买券还券 | `xtconstant.CREDIT_BUY_SECU_REPAY_SPECIAL` |
| 专项直接还券 | `xtconstant.CREDIT_DIRECT_SECU_REPAY_SPECIAL` |
| 专项卖券还款 | `xtconstant.CREDIT_SELL_SECU_REPAY_SPECIAL` |
| 专项直接还款 | `xtconstant.CREDIT_DIRECT_CASH_REPAY_SPECIAL` |

#### 期货委托类型

| 类型 | 枚举值 |
|------|--------|
| 六键风格 - 开多 | `xtconstant.FUTURE_OPEN_LONG` |
| 六键风格 - 平昨多 | `xtconstant.FUTURE_CLOSE_LONG_HISTORY` |
| 六键风格 - 平今多 | `xtconstant.FUTURE_CLOSE_LONG_TODAY` |
| 六键风格 - 开空 | `xtconstant.FUTURE_OPEN_SHORT` |
| 六键风格 - 平昨空 | `xtconstant.FUTURE_CLOSE_SHORT_HISTORY` |
| 六键风格 - 平今空 | `xtconstant.FUTURE_CLOSE_SHORT_TODAY` |
| 四键风格 - 平多，优先平今 | `xtconstant.FUTURE_CLOSE_LONG_TODAY_FIRST` |
| 四键风格 - 平多，优先平昨 | `xtconstant.FUTURE_CLOSE_LONG_HISTORY_FIRST` |
| 四键风格 - 平空，优先平今 | `xtconstant.FUTURE_CLOSE_SHORT_TODAY_FIRST` |
| 四键风格 - 平空，优先平昨 | `xtconstant.FUTURE_CLOSE_SHORT_HISTORY_FIRST` |
| 两键风格 - 卖出，如有多仓，优先平仓，优先平今，如有余量，再开空 | `xtconstant.FUTURE_CLOSE_LONG_TODAY_HISTORY_THEN_OPEN_SHORT` |
| 两键风格 - 卖出，如有多仓，优先平仓，优先平昨，如有余量，再开空 | `xtconstant.FUTURE_CLOSE_LONG_HISTORY_TODAY_THEN_OPEN_SHORT` |
| 两键风格 - 买入，如有空仓，优先平仓，优先平今，如有余量，再开多 | `xtconstant.FUTURE_CLOSE_SHORT_TODAY_HISTORY_THEN_OPEN_LONG` |
| 两键风格 - 买入，如有空仓，优先平仓，优先平昨，如有余量，再开多 | `xtconstant.FUTURE_CLOSE_SHORT_HISTORY_TODAY_THEN_OPEN_LONG` |
| 两键风格 - 买入，不优先平仓 | `xtconstant.FUTURE_OPEN` |
| 两键风格 - 卖出，不优先平仓 | `xtconstant.FUTURE_CLOSE` |
| 期货 - 跨商品套利开仓 | `xtconstant.FUTURE_ARBITRAGE_OPEN` |
| 期货 - 平, 优先平昨 | `xtconstant.FUTURE_ARBITRAGE_CLOSE_HISTORY_FIRST` |
| 期货 - 平, 优先平今 | `xtconstant.FUTURE_ARBITRAGE_CLOSE_TODAY_FIRST` |
| 期货展期 - 看多, 优先平昨 | `xtconstant.FUTURE_RENEW_LONG_CLOSE_HISTORY_FIRST` |
| 期货展期 - 看多，优先平今 | `xtconstant.FUTURE_RENEW_LONG_CLOSE_TODAY_FIRST` |
| 期货展期 - 看空，优先平昨 | `xtconstant.FUTURE_RENEW_SHORT_CLOSE_HISTORY_FIRST` |
| 期货展期 - 看空，优先平今 | `xtconstant.FUTURE_RENEW_SHORT_CLOSE_TODAY_FIRST` |

#### 股票期权委托类型

| 类型 | 枚举值 |
|------|--------|
| 买入开仓 | `xtconstant.STOCK_OPTION_BUY_OPEN` |
| 卖出平仓 | `xtconstant.STOCK_OPTION_SELL_CLOSE` |
| 卖出开仓 | `xtconstant.STOCK_OPTION_SELL_OPEN` |
| 买入平仓 | `xtconstant.STOCK_OPTION_BUY_CLOSE` |
| 备兑开仓 | `xtconstant.STOCK_OPTION_COVERED_OPEN` |
| 备兑平仓 | `xtconstant.STOCK_OPTION_COVERED_CLOSE` |
| 认购行权 | `xtconstant.STOCK_OPTION_CALL_EXERCISE` |
| 认沽行权 | `xtconstant.STOCK_OPTION_PUT_EXERCISE` |
| 证券锁定 | `xtconstant.STOCK_OPTION_SECU_LOCK` |
| 证券解锁 | `xtconstant.STOCK_OPTION_SECU_UNLOCK` |

#### ETF 申赎

| 类型 | 枚举值 |
|------|--------|
| 申购 | `xtconstant.ETF_PURCHASE` |
| 赎回 | `xtconstant.ETF_REDEMPTION` |

### 报价类型 (price_type)

| 类型 | 枚举值 | 说明 |
|------|--------|------|
| 最新价 | `xtconstant.LATEST_PRICE` | - |
| 指定价 | `xtconstant.FIX_PRICE` | - |
| 郑商所期货 - 市价最优价 | `xtconstant.MARKET_BEST` | 郑商所 |
| 大商所期货 - 市价即成剩撤 | `xtconstant.MARKET_CANCEL` | 大商所 |
| 大商所期货 - 市价全额成交或撤 | `xtconstant.MARKET_CANCEL_ALL` | 大商所 |
| 中金所期货 - 市价最优一档即成剩撤 | `xtconstant.MARKET_CANCEL_1` | 中金所 |
| 中金所期货 - 市价最优五档即成剩撤 | `xtconstant.MARKET_CANCEL_5` | 中金所 |
| 中金所期货 - 市价最优一档即成剩转 | `xtconstant.MARKET_CONVERT_1` | 中金所 |
| 中金所期货 - 市价最优五档即成剩转 | `xtconstant.MARKET_CONVERT_5` | 中金所 |
| 上交所/北交所股票 - 最优五档即时成交剩余撤销 | `xtconstant.MARKET_SH_CONVERT_5_CANCEL` | 上交所/北交所 |
| 上交所/北交所股票 - 最优五档即时成交剩转限价 | `xtconstant.MARKET_SH_CONVERT_5_LIMIT` | 上交所/北交所 |
| 上交所/北交所股票 - 对手方最优价格委托 | `xtconstant.MARKET_PEER_PRICE_FIRST` | 上交所/北交所 |
| 上交所/北交所股票 - 本方最优价格委托 | `xtconstant.MARKET_MINE_PRICE_FIRST` | 上交所/北交所 |
| 深交所股票/期权 - 对手方最优价格委托 | `xtconstant.MARKET_PEER_PRICE_FIRST` | 深交所/期权 |
| 深交所股票/期权 - 本方最优价格委托 | `xtconstant.MARKET_MINE_PRICE_FIRST` | 深交所/期权 |
| 深交所股票/期权 - 即时成交剩余撤销委托 | `xtconstant.MARKET_SZ_INSTBUSI_RESTCANCEL` | 深交所/期权 |
| 深交所股票/期权 - 最优五档即时成交剩余撤销 | `xtconstant.MARKET_SZ_CONVERT_5_CANCEL` | 深交所/期权 |
| 深交所股票/期权 - 全额成交或撤销委托 | `xtconstant.MARKET_SZ_FULL_OR_CANCEL` | 深交所/期权 |

**注意**: 提示市价类型只在实盘环境中生效，模拟环境不支持市价方式报单。

### 委托状态 (order_status)

| 枚举变量名 | 值 | 含义 |
|-----------|-----|------|
| `xtconstant.ORDER_UNREPORTED` | 48 | 未报 |
| `xtconstant.ORDER_WAIT_REPORTING` | 49 | 待报 |
| `xtconstant.ORDER_REPORTED` | 50 | 已报 |
| `xtconstant.ORDER_REPORTED_CANCEL` | 51 | 已报待撤 |
| `xtconstant.ORDER_PARTSUCC_CANCEL` | 52 | 部成待撤 |
| `xtconstant.ORDER_PART_CANCEL` | 53 | 部撤（已经有一部分成交，剩下的已经撤单） |
| `xtconstant.ORDER_CANCELED` | 54 | 已撤 |
| `xtconstant.ORDER_PART_SUCC` | 55 | 部成（已经有一部分成交，剩下的待成交） |
| `xtconstant.ORDER_SUCCEEDED` | 56 | 已成 |
| `xtconstant.ORDER_JUNK` | 57 | 废单 |
| `xtconstant.ORDER_UNKNOWN` | 255 | 未知 |

### 账号状态 (account_status)

| 枚举变量名 | 值 | 含义 |
|-----------|-----|------|
| `xtconstant.ACCOUNT_STATUS_INVALID` | -1 | 无效 |
| `xtconstant.ACCOUNT_STATUS_OK` | 0 | 正常 |
| `xtconstant.ACCOUNT_STATUS_WAITING_LOGIN` | 1 | 连接中 |
| `xtconstant.ACCOUNT_STATUSING` | 2 | 登陆中 |
| `xtconstant.ACCOUNT_STATUS_FAIL` | 3 | 失败 |
| `xtconstant.ACCOUNT_STATUS_INITING` | 4 | 初始化中 |
| `xtconstant.ACCOUNT_STATUS_CORRECTING` | 5 | 数据刷新校正中 |
| `xtconstant.ACCOUNT_STATUS_CLOSED` | 6 | 收盘后 |
| `xtconstant.ACCOUNT_STATUS_ASSIS_FAIL` | 7 | 穿透副链接断开 |
| `xtconstant.ACCOUNT_STATUS_DISABLEBYSYS` | 8 | 系统停用（总线使用-密码错误超限） |
| `xtconstant.ACCOUNT_STATUS_DISABLEBYUSER` | 9 | 用户停用（总线使用） |

### 划拨方向 (transfer_direction)

| 枚举变量名 | 值 | 含义 |
|-----------|-----|------|
| `xtconstant.FUNDS_TRANSFER_NORMAL_TO_SPEED` | 510 | 资金划拨-普通柜台到极速柜台 |
| `xtconstant.FUNDS_TRANSFER_SPEED_TO_NORMAL` | 511 | 资金划拨-极速柜台到普通柜台 |
| `xtconstant.NODE_FUNDS_TRANSFER_SH_TO_SZ` | 512 | 节点资金划拨-上海节点到深圳节点 |
| `xtconstant.NODE_FUNDS_TRANSFER_SZ_TO_SH` | 513 | 节点资金划拨-深圳节点到上海节点 |

### 多空方向 (direction)

| 枚举变量名 | 值 | 含义 |
|-----------|-----|------|
| `xtconstant.DIRECTION_FLAG_LONG` | 48 | 多 |
| `xtconstant.DIRECTION_FLAG_SHORT` | 49 | 空 |

### 交易操作 (offset_flag)

| 枚举变量名 | 值 | 含义 |
|-----------|-----|------|
| `xtconstant.OFFSET_FLAG_OPEN` | 48 | 买入，开仓 |
| `xtconstant.OFFSET_FLAG_CLOSE` | 49 | 卖出，平仓 |
| `xtconstant.OFFSET_FLAG_FORCECLOSE` | 50 | 强平 |
| `xtconstant.OFFSET_FLAG_CLOSETODAY` | 51 | 平今 |
| `xtconstant.OFFSET_FLAG_ClOSEYESTERDAY` | 52 | 平昨 |
| `xtconstant.OFFSET_FLAG_FORCEOFF` | 53 | 强减 |
| `xtconstant.OFFSET_FLAG_LOCALFORCECLOSE` | 54 | 本地强平 |

---

## XtQuant 数据结构说明

### 资产 (XtAsset)

| 属性 | 类型 | 注释 |
|------|------|------|
| account_type | int | 账号类型，参见数据字典 |
| account_id | str | 资金账号 |
| cash | float | 可用金额 |
| frozen_cash | float | 冻结金额 |
| market_value | float | 持仓市值 |
| total_asset | float | 总资产 |

### 委托 (XtOrder)

| 属性 | 类型 | 注释 |
|------|------|------|
| account_type | int | 账号类型，参见数据字典 |
| account_id | str | 资金账号 |
| stock_code | str | 证券代码，例如 "600000.SH" |
| order_id | int | 订单编号 |
| order_sysid | str | 柜台合同编号 |
| order_time | int | 报单时间 |
| order_type | int | 委托类型，参见数据字典 |
| order_volume | int | 委托数量 |
| price_type | int | 报价类型，该字段在返回时为柜台返回类型，不等价于下单传入的 price_type，枚举值不一样但功能一样，参见数据字典 |
| price | float | 委托价格 |
| traded_volume | int | 成交数量 |
| traded_price | float | 成交均价 |
| order_status | int | 委托状态，参见数据字典 |
| status_msg | str | 委托状态描述，如废单原因 |
| strategy_name | str | 策略名称 |
| order_remark | str | 委托备注，最大 24 个英文字符 |
| direction | int | 多空方向，股票不适用；参见数据字典 |
| offset_flag | int | 交易操作，用此字段区分股票买卖，期货开、平仓，期权买卖等；参见数据字典 |

### 成交 (XtTrade)

| 属性 | 类型 | 注释 |
|------|------|------|
| account_type | int | 账号类型，参见数据字典 |
| account_id | str | 资金账号 |
| stock_code | str | 证券代码 |
| order_type | int | 委托类型，参见数据字典 |
| traded_id | str | 成交编号 |
| traded_time | int | 成交时间 |
| traded_price | float | 成交均价 |
| traded_volume | int | 成交数量 |
| traded_amount | float | 成交金额 |
| order_id | int | 订单编号 |
| order_sysid | str | 柜台合同编号 |
| strategy_name | str | 策略名称 |
| order_remark | str | 委托备注，最大 24 个英文字符 |
| direction | int | 多空方向，股票不适用；参见数据字典 |
| offset_flag | int | 交易操作，用此字段区分股票买卖，期货开、平仓，期权买卖等；参见数据字典 |

### 持仓 (XtPosition)

| 属性 | 类型 | 注释 |
|------|------|------|
| account_type | int | 账号类型，参见数据字典 |
| account_id | str | 资金账号 |
| stock_code | str | 证券代码 |
| volume | int | 持仓数量 |
| can_use_volume | int | 可用数量 |
| open_price | float | 开仓价（返回与成本价一致） |
| market_value | float | 市值 |
| frozen_volume | int | 冻结数量 |
| on_road_volume | int | 在途股份 |
| yesterday_volume | int | 昨夜拥股 |
| avg_price | float | 成本价 |
| direction | int | 多空方向，股票不适用；参见数据字典 |

### 期货持仓统计 (XtPositionStatistics)

| 属性 | 类型 | 注释 |
|------|------|------|
| account_id | string | 账户 |
| exchange_id | string | 市场代码 |
| exchange_name | string | 市场名称 |
| product_id | string | 品种代码 |
| instrument_id | string | 合约代码 |
| instrument_name | string | 合约名称 |
| direction | int | 多空方向，股票不适用；参见数据字典 |
| hedge_flag | int | 投保类型；参见投保类型 |
| position | int | 持仓数量 |
| yesterday_position | int | 昨仓数量 |
| today_position | int | 今仓数量 |
| can_close_vol | int | 可平数量 |
| position_cost | float | 持仓成本 |
| avg_price | float | 持仓均价 |
| position_profit | float | 持仓盈亏 |
| float_profit | float | 浮动盈亏 |
| open_price | float | 开仓均价 |
| open_cost | float | 开仓成本 |
| used_margin | float | 已使用保证金 |
| used_commission | float | 已使用的手续费 |
| frozen_margin | float | 冻结保证金 |
| frozen_commission | float | 冻结手续费 |
| instrument_value | float | 市值，合约价值 |
| cancel_times | int | 撤单次数（中间平仓不减） |
| last_price | float | 最新价 |
| rise_ratio | float | 当日涨幅 |
| product_name | string | 产品名称 |
| royalty | float | 权利金市值 |
| expire_date | string | 到期日 |

---

## XtQuant 接口说明

### 系统设置接口

#### XtQuantTrader.__init__(path, session_id)

创建 XtQuantTrader 实例

**参数：**
- `path` (str): mini qmt客户端安装目录下 userdata_mini 路径
- `session_id` (int): 会话编号，策略使用方对于不同的 Python 策略需要使用不同的会话编号

#### register_callback(callback)

注册回调类对象

**参数：**
- `callback` (XtQuantTraderCallback): 回调类对象

#### start()

启动交易线程

#### connect()

建立交易连接

**返回值：** 0 表示连接成功

#### subscribe(account)

对交易回调进行订阅，订阅后可以收到交易主推

**参数：**
- `account` (StockAccount): 账号对象

**返回值：** 0 表示订阅成功

#### unsubscribe(account)

取消订阅

**参数：**
- `account` (StockAccount): 账号对象

#### run_forever()

阻塞线程，接收交易推送。支持 Ctrl+C 跳出

#### set_relaxed_response_order_enabled(enabled)

为主动请求接口的返回增加专用线程以及相关控制，以支持在 `on_stock_order` 等推送接口中调用同步请求

**参数：**
- `enabled` (bool): 是否启用

### 操作接口

#### order_stock(account, stock_code, order_type, volume, price_type, price, strategy_name='', remark='')

使用指定价下单

**参数：**
- `account` (StockAccount): 账号对象
- `stock_code` (str): 证券代码
- `order_type` (int): 委托类型
- `volume` (int): 委托数量
- `price_type` (int): 报价类型
- `price` (float): 委托价格
- `strategy_name` (str): 策略名称，默认为空
- `remark` (str): 备注，默认为空

**返回值：** 订单编号

#### order_stock_async(account, stock_code, order_type, volume, price_type, price, strategy_name='', remark='')

使用异步下单接口

**参数：**
- `account` (StockAccount): 账号对象
- `stock_code` (str): 证券代码
- `order_type` (int): 委托类型
- `volume` (int): 委托数量
- `price_type` (int): 报价类型
- `price` (float): 委托价格
- `strategy_name` (str): 策略名称，默认为空
- `remark` (str): 备注，默认为空

**返回值：** 下单请求序号 seq

#### cancel_order_stock(account, order_id)

使用订单编号撤单（同步撤单）

**参数：**
- `account` (StockAccount): 账号对象
- `order_id` (int): 订单编号

**返回值：** 撤单结果

#### cancel_order_stock_async(account, order_id)

使用订单编号撤单（异步撤单）

**参数：**
- `account` (StockAccount): 账号对象
- `order_id` (int): 订单编号

**返回值：** 撤单请求序号

#### fund_transfer(account, direction, amount)

资金划拨

**参数：**
- `account` (StockAccount): 账号对象
- `direction` (int): 划拨方向
- `amount` (float): 划拨金额

**返回值：** 划拨结果

### 查询接口

#### query_stock_asset(account)

查询证券资产

**参数：**
- `account` (StockAccount): 账号对象

**返回值：** XtAsset 对象

#### query_stock_order(account, order_id)

根据订单编号查询委托

**参数：**
- `account` (StockAccount): 账号对象
- `order_id` (int): 订单编号

**返回值：** XtOrder 对象

#### query_stock_orders(account, order_type=None)

查询当日所有的委托

**参数：**
- `account` (StockAccount): 账号对象
- `order_type` (int): 委托类型，可选，仅查询指定类型的委托

**返回值：** XtOrder 对象列表

#### query_stock_trades(account)

查询当日所有的成交

**参数：**
- `account` (StockAccount): 账号对象

**返回值：** XtTrade 对象列表

#### query_stock_positions(account)

查询当日所有的持仓

**参数：**
- `account` (StockAccount): 账号对象

**返回值：** XtPosition 对象列表

#### query_stock_position(account, stock_code)

根据股票代码查询对应持仓

**参数：**
- `account` (StockAccount): 账号对象
- `stock_code` (str): 证券代码

**返回值：** XtPosition 对象

#### query_new_purchase_limit(account)

查询新股申购额度

**参数：**
- `account` (StockAccount): 账号对象

**返回值：** 新股申购额度信息

#### query_ipo_data(account)

查询新股信息

**参数：**
- `account` (StockAccount): 账号对象

**返回值：** 新股信息列表

#### query_account_infos()

查询账号信息

**返回值：** 账号信息列表

#### query_com_fund(account)

查询普通柜台资金

**参数：**
- `account` (StockAccount): 账号对象

**返回值：** 资金信息

#### query_com_position(account)

查询普通柜台持仓

**参数：**
- `account` (StockAccount): 账号对象

**返回值：** 持仓信息

#### query_position_statistics(account, exchange_id, product_id, direction)

查询期货持仓统计

**参数：**
- `account` (StockAccount): 账号对象
- `exchange_id` (str): 市场代码
- `product_id` (str): 品种代码
- `direction` (int): 多空方向

**返回值：** XtPositionStatistics 对象

#### smt_query_quoter(account)

查询券源行情

**参数：**
- `account` (StockAccount): 账号对象

**返回值：** 券源行情信息

#### smt_negotiate_order(account, stock_code, volume)

库存券约券申请

**参数：**
- `account` (StockAccount): 账号对象
- `stock_code` (str): 证券代码
- `volume` (int): 申请数量

**返回值：** 约券申请结果

#### smt_query_compact(account, stock_code)

约券合约查询

**参数：**
- `account` (StockAccount): 账号对象
- `stock_code` (str): 证券代码

**返回值：** 约券合约信息

#### export_data(data_type, start_time, end_time, output_file)

通用数据导出

**参数：**
- `data_type` (str): 数据类型
- `start_time` (int): 开始时间
- `end_time` (int): 结束时间
- `output_file` (str): 输出文件路径

**返回值：** 导出结果

#### query_data(data_type, start_time, end_time, **kwargs)

通用数据查询

**参数：**
- `data_type` (str): 数据类型
- `start_time` (int): 开始时间
- `end_time` (int): 结束时间
- `kwargs`: 其他查询参数

**返回值：** 查询结果

#### sync_transaction_from_external(transactions)

外部成交导入

**参数：**
- `transactions`: 外部成交数据列表

**返回值：** 导入结果

### 回调类

#### XtQuantTraderCallback

回调类需要继承此类并实现以下回调函数：

##### on_disconnected()

连接断开回调

##### on_stock_order(order)

委托回报推送回调

**参数：**
- `order` (XtOrder): 委托对象

##### on_stock_trade(trade)

成交变动推送回调

**参数：**
- `trade` (XtTrade): 成交对象

##### on_order_error(order_error)

委托失败推送回调

**参数：**
- `order_error` (XtOrderError): 委托失败对象

##### on_cancel_error(cancel_error)

撤单失败推送回调

**参数：**
- `cancel_error` (XtCancelError): 撤单失败对象

##### on_order_stock_async_response(response)

异步下单回报推送回调

**参数：**
- `response` (XtOrderResponse): 下单响应对象

##### on_account_status(status)

账号状态主推回调

**参数：**
- `status` (XtAccountStatus): 账号状态对象

---

## 版本兼容性说明

XtQuant 支持多个版本的迅投极速交易终端（MiniQMT），请确保使用与客户端版本兼容的 XtQuant 版本。

---

## 注意事项

1. 市价类型只在实盘环境中生效，模拟环境不支持市价方式报单
2. session_id 需要对不同的 Python 策略使用不同的会话编号
3. path 参数应指向 mini qmt 客户端安装目录下的 userdata_mini 路径
4. 在回调函数中调用同步请求时，需要启用 `set_relaxed_response_order_enabled(True)`
