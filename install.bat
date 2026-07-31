@echo off
chcp 65001 >nul
title Chinese Thesis Workbench - 安装程序
echo.
echo ========================================
echo   Chinese Thesis Workbench 安装程序
echo ========================================
echo.

REM 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到Python，请先安装Python 3.8或更高版本
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/5] 检测到Python:
python --version
echo.

REM 安装依赖
echo [2/5] 正在安装依赖包...
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
if errorlevel 1 (
    echo [错误] 依赖安装失败
    pause
    exit /b 1
)
echo [完成] 依赖安装成功
echo.

REM 检测浏览器
echo [3/5] 检测本地浏览器...
python scripts\check_environment.py
if errorlevel 1 (
    echo.
    echo [警告] 未检测到本地浏览器
    echo 正在尝试下载Chromium（约100MB）...
    playwright install chromium
    if errorlevel 1 (
        echo [错误] Chromium下载失败，请检查网络连接
        pause
        exit /b 1
    )
)
echo.

REM 初始化工作空间
echo [4/5] 初始化工作空间...
python scripts\workspace\init_thesis_workspace.py
if errorlevel 1 (
    echo [错误] 工作空间初始化失败
    pause
    exit /b 1
)
echo [完成] 工作空间初始化成功
echo.

REM 功能测试
echo [5/5] 运行功能测试...
python scripts\literature\test_browser_detection.py
if errorlevel 1 (
    echo [警告] 浏览器检测未通过，但可能仍可正常使用
)
echo.

echo ========================================
echo   安装完成！
echo ========================================
echo.
echo 使用步骤:
echo 1. 配置学校规范: thesis-ai-standard\templates\standard-profile.yaml
echo 2. 配置论文信息: thesis-ai-standard\templates\thesis-ai-spec.yaml
echo 3. 运行CNKI检索: python scripts\literature\build_cnki_pool.py
echo 4. 生成论文: python scripts\docx\build_complete_thesis.py
echo.
pause
