#!/usr/bin/env python3
"""
AI提示词智能拆分工具 - 启动脚本
快速启动Web界面
"""

import os
import sys
import subprocess
from pathlib import Path


def check_dependencies():
    """检查依赖是否安装"""
    try:
        import streamlit
        print("✅ Streamlit 已安装")
    except ImportError:
        print("❌ Streamlit 未安装，正在安装...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "streamlit>=1.28.0"])
        print("✅ Streamlit 安装完成")


def start_app():
    """启动应用"""
    current_dir = Path(__file__).parent
    ui_file = current_dir / "ui_streamlit.py"
    
    if not ui_file.exists():
        print(f"❌ 找不到界面文件: {ui_file}")
        return
    
    print("🚀 启动AI提示词智能拆分工具...")
    print("🌐 Web界面将在浏览器中打开")
    print("🔑 首次使用请配置您的API Key")
    print("📋 使用 Ctrl+C 停止应用")
    print("-" * 50)
    
    try:
        # 启动Streamlit应用
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", str(ui_file),
            "--server.port", "8501",
            "--server.address", "localhost",
            "--browser.gatherUsageStats", "false"
        ])
    except KeyboardInterrupt:
        print("\n👋 应用已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")


if __name__ == "__main__":
    print("🤖 AI提示词智能拆分工具")
    print("=" * 50)
    
    # 检查并安装依赖
    check_dependencies()
    
    # 启动应用
    start_app() 