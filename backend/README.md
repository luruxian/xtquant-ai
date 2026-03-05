# MiniQMT AI Backend

基于 FastAPI 的 MiniQMT 交易后端服务

## 项目结构

```
backend/
├── main.py                 # 主应用入口
├── requirements.txt        # 依赖包列表
├── .env                   # 环境变量配置
├── .env.example           # 环境变量示例
├── routes/                # API 路由模块
│   ├── __init__.py
│   ├── asset.py          # 资产查询路由
│   ├── order.py          # 订单管理路由
│   ├── position.py       # 持仓查询路由
│   └── trade.py          # 成交查询路由
├── schemas/               # Pydantic 数据模型
│   ├── __init__.py
│   └── asset.py
├── services/              # 业务逻辑服务层
│   ├── __init__.py
│   └── qmt_service.py
└── utils/                 # 工具函数
    ├── __init__.py
    └── config.py
```

## 安装步骤

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 配置环境变量：
复制 `.env.example` 为 `.env`，并修改 QMT_PATH 为您的 QMT 客户端实际路径

3. 运行服务：
```bash
uvicorn main:app --reload
```

4. 访问 API 文档：
```
http://localhost:8000/docs
```

## API 接口

### 资产查询
- `GET /api/v1/asset` - 查询单个账户资产
- `GET /api/v1/asset/batch` - 批量查询账户资产

### 订单管理
- `POST /api/v1/order` - 创建订单（下单）
- `DELETE /api/v1/order` - 取消订单（撤单）
- `GET /api/v1/order/{order_id}` - 查询订单
- `GET /api/v1/order` - 查询当日所有订单

### 持仓查询
- `GET /api/v1/position/{stock_code}` - 根据股票代码查询持仓
- `GET /api/v1/position` - 查询当日所有持仓

### 成交查询
- `GET /api/v1/trade` - 查询当日所有成交

## 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| QMT_PATH | QMT 客户端 userdata_mini 路径 | D:\迅投极速交易终端 睿智融科版\userdata_mini |
| SESSION_ID | 会话编号 | 123456 |

## 注意事项

1. 请确保 QMT 客户端已启动并登录
2. 不同策略需要使用不同的 session_id
3. 市价类型只在实盘环境中生效，模拟环境不支持市价方式报单
