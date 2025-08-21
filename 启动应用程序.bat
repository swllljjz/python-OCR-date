@echo off
chcp 65001 >nul
title 商品包装生产日期识别系统 V1.0

echo ========================================
echo 商品包装生产日期识别系统 V1.0
echo ========================================
echo.

echo 正在启动应用程序...
echo.

python run_app.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo 启动失败！请检查：
    echo 1. Python是否已正确安装
    echo 2. 所需的依赖包是否已安装
    echo 3. 运行 pip install -r requirements.txt 安装依赖
    echo.
    pause
)
