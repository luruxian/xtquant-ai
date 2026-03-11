# 股票同步报单API文档

## 概述

本文档描述了新创建的股票同步报单API，该API实现了`order_stock`方法，用于对股票进行同步下单操作。

## API端点

### 股票同步报单

**POST** `/api/v1/order/stock`

对股票进行下单操作。

#### 请求参数

| 参数名 | 类型 | 必填 | 描述 | 示例 |
|--------|------|------|------|------|
| account | string | 是 | 资金账号 | "1000000365" |
| stock_code | string | 是 | 证券代码 | "600000.SH" |
| order_type | int | 是 | 委托类型 | 23 (买入) |
| order_volume | int | 是 | 委托数量，股票以'股'为单位 | 1000 |
| price_type | int | 是 | 报价类型 | 0 (限价) |
| price | float | 是 | 委托价格 | 10.5 |
| strategy_name | string | 是 | 策略名称 | "test_strategy" |
| order_remark | string | 是 | 委托备注 | "order_test" |

#### 响应格式

```json
{
  "order_id": 12345,
  "message": "委托成功"
}
```

#### 响应说明

- `order_id`: 系统生成的订单编号
  - 成功委托后的订单编号为大于0的正整数
  - 如果为-1表示委托失败
- `message`: 委托结果消息

#### 示例请求

```bash
curl -X POST "http://localhost:8000/api/v1/order/stock" \
  -H "Content-Type: application/json" \
  -d '{
    "account": "1000000365",
    "stock_code": "600000.SH",
    "order_type": 23,
    "order_volume": 1000,
    "price_type": 0,
    "price": 10.5,
    "strategy_name": "test_strategy",
    "order_remark": "order_test"
  }'
```

#### 示例响应

成功响应：
```json
{
  "order_id": 12345,
  "message": "委托成功"
}
```

失败响应：
```json
{
  "order_id": -1,
  "message": "委托失败"
}
```

## 错误处理

API可能返回以下HTTP状态码：

- `200 OK`: 请求成功处理
- `404 Not Found`: QMT客户端路径不存在
- `500 Internal Server Error`: 服务器内部错误

错误响应格式：
```json
{
  "error": "ERROR_CODE",
  "message": "错误描述"
}
```

## 常量定义

为了确保参数正确，建议使用 `xtconstant` 模块中的常量：

```python
from xtquant import xtconstant

# 委托类型
STOCK_BUY = xtconstant.STOCK_BUY  # 23 - 买入
STOCK_SELL = xtconstant.STOCK_SELL  # 24 - 卖出

# 报价类型
FIX_PRICE = xtconstant.FIX_PRICE  # 0 - 限价
LATEST_PRICE = xtconstant.LATEST_PRICE  # 1 - 最新价（市价）
```

## 使用示例

### Python示例（使用常量）

```python
import requests
import json
from xtquant import xtconstant

def order_stock():
    url = "http://localhost:8000/api/v1/order/stock"

    data = {
        "account": "1000000365",
        "stock_code": "600000.SH",
        "order_type": xtconstant.STOCK_BUY,  # 使用常量
        "order_volume": 1000,
        "price_type": xtconstant.FIX_PRICE,  # 使用常量
        "price": 10.5,
        "strategy_name": "my_strategy",
        "order_remark": "test_order"
    }

    response = requests.post(url, json=data)

    if response.status_code == 200:
        result = response.json()
        if result["order_id"] > 0:
            print(f"下单成功，订单编号: {result['order_id']}")
        else:
            print("下单失败")
    else:
        print(f"请求失败: {response.text}")

if __name__ == "__main__":
    order_stock()
```

### Python示例（市价下单）

```python
import requests
import json
from xtquant import xtconstant

def order_stock_market():
    url = "http://localhost:8000/api/v1/order/stock"

    data = {
        "account": "1000000365",
        "stock_code": "600000.SH",
        "order_type": xtconstant.STOCK_BUY,
        "order_volume": 1000,
        "price_type": xtconstant.LATEST_PRICE,  # 市价
        "price": -1,  # 市价时价格传-1
        "strategy_name": "market_order",
        "order_remark": "market_buy_test"
    }

    response = requests.post(url, json=data)

    if response.status_code == 200:
        result = response.json()
        if result["order_id"] > 0:
            print(f"市价下单成功，订单编号: {result['order_id']}")
        else:
            print("市价下单失败")
    else:
        print(f"请求失败: {response.text}")

if __name__ == "__main__":
    order_stock_market()
```

## 股票同步撤单API

### 端点

**POST** `/api/v1/order/cancel`

根据订单编号对委托进行撤单操作。

#### 请求参数

| 参数名 | 类型 | 必填 | 描述 | 示例 |
|--------|------|------|------|------|
| account | string | 是 | 资金账号 | "1000000365" |
| order_id | int | 是 | 同步下单接口返回的订单编号 | 100 |

#### 响应格式

```json
{
  "result": 0,
  "message": "撤单成功"
}
```

#### 响应说明

- `result`: 撤单结果
  - `0`: 成功发出撤单指令
  - `-1`: 撤单失败
- `message`: 撤单结果消息

#### 示例请求

```bash
curl -X POST "http://localhost:8000/api/v1/order/cancel" \
  -H "Content-Type: application/json" \
  -d '{
    "account": "1000000365",
    "order_id": 100
  }'
```

#### 示例响应

成功响应：
```json
{
  "result": 0,
  "message": "撤单成功"
}
```

失败响应：
```json
{
  "result": -1,
  "message": "撤单失败"
}
```

### Python示例

```python
import requests
import json

def cancel_stock_order():
    url = "http://localhost:8000/api/v1/order/cancel"

    data = {
        "account": "1000000365",
        "order_id": 100  # 从order_stock接口返回的订单编号
    }

    response = requests.post(url, json=data)

    if response.status_code == 200:
        result = response.json()
        if result["result"] == 0:
            print("撤单成功")
        else:
            print(f"撤单失败: {result['message']}")
    else:
        print(f"请求失败: {response.text}")

if __name__ == "__main__":
    cancel_stock_order()
```

### 完整工作流程示例

```python
import requests
import json
from xtquant import xtconstant

def order_and_cancel_workflow():
    """完整的下单和撤单工作流程"""

    # 1. 下单
    order_url = "http://localhost:8000/api/v1/order/stock"
    order_data = {
        "account": "1000000365",
        "stock_code": "600000.SH",
        "order_type": xtconstant.STOCK_BUY,
        "order_volume": 100,
        "price_type": xtconstant.FIX_PRICE,
        "price": 10.5,
        "strategy_name": "workflow_test",
        "order_remark": "test_order"
    }

    order_response = requests.post(order_url, json=order_data)

    if order_response.status_code != 200:
        print(f"下单失败: {order_response.text}")
        return

    order_result = order_response.json()
    order_id = order_result.get("order_id")

    if order_id <= 0:
        print(f"下单失败: {order_result.get('message', '未知错误')}")
        return

    print(f"下单成功，订单编号: {order_id}")

    # 2. 撤单
    cancel_url = "http://localhost:8000/api/v1/order/cancel"
    cancel_data = {
        "account": "1000000365",
        "order_id": order_id
    }

    cancel_response = requests.post(cancel_url, json=cancel_data)

    if cancel_response.status_code != 200:
        print(f"撤单请求失败: {cancel_response.text}")
        return

    cancel_result = cancel_response.json()

    if cancel_result.get("result") == 0:
        print("撤单成功")
    else:
        print(f"撤单失败: {cancel_result.get('message', '未知错误')}")

if __name__ == "__main__":
    order_and_cancel_workflow()
```

## 测试

### 运行测试脚本

项目根目录下提供了测试脚本：

```bash
# 测试股票同步报单
python test_stock_order_fixed.py

# 测试股票同步撤单
python test_stock_cancel.py

# 测试完整的工作流程
python test_stock_cancel.py
```

### 手动测试

1. 启动后端服务：
   ```bash
   cd backend
   python run.py
   ```

2. 访问API文档：
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

3. 在API文档中测试接口：
   - 找到 `/api/v1/order/stock` 接口
   - 点击 "Try it out"
   - 填写请求参数
   - 点击 "Execute"

## 注意事项

1. **参数说明**：
   - `order_type`: 委托类型，需要传入对应的整数值（如23表示买入，24表示卖出）
   - `price_type`: 报价类型，0表示限价，1表示市价等
   - `order_volume`: 委托数量，股票以'股'为单位，债券以'张'为单位

2. **返回值**：
   - 成功时返回大于0的订单编号
   - 失败时返回-1

3. **环境要求**：
   - 需要正确配置QMT客户端路径
   - 需要有效的资金账号
   - 需要在交易时间内使用

## 相关API

- `POST /api/v1/order`: 通用下单接口（返回完整订单信息）
- `POST /api/v1/order/async`: 异步下单接口
- `POST /api/v1/order/cancel`: 股票同步撤单接口（返回0/-1格式）
- `GET /api/v1/order`: 查询订单接口

## 更新日志

- 2026-03-11: 创建股票同步报单API，实现`order_stock`方法