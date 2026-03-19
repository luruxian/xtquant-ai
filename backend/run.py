#!/usr/bin/env python3
"""启动脚本"""
import uvicorn
import os
import sys

if __name__ == "__main__":
    # 添加当前目录到Python路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, current_dir)

    # 确保可以导入应用
    try:
        from main import app
        print("✅ 应用导入成功")
    except ImportError as e:
        print(f"❌ 应用导入失败: {e}")
        sys.exit(1)

    # 启动服务器
    print("🚀 启动服务器...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # 临时关闭reload以查看标准日志
        log_level="info"
    )