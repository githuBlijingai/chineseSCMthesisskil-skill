@echo off
chcp 65001 >nul
title Chinese Thesis Workbench
echo.
echo ========================================
echo   Chinese Thesis Workbench
echo ========================================
echo.

REM 检查工作空间是否存在
if not exist "thesis-ai-standard\templates\thesis-ai-spec.yaml" (
    echo [提示] 首次使用，请先运行安装程序
    echo.
    echo 按任意键运行安装...
    pause >nul
    call install.bat
    exit /b
)

:menu
cls
echo.
echo ========================================
echo   Chinese Thesis Workbench - 主菜单
echo ========================================
echo.
echo  1. 环境检查
echo  2. CNKI文献检索
echo  3. 生成论文
echo  4. 打开配置文件夹
echo  5. 打开输出文件夹
echo  0. 退出
echo.
echo ========================================
set /p choice="请选择操作 (0-5): "

if "%choice%"=="1" goto check
if "%choice%"=="2" goto cnki
if "%choice%"=="3" goto generate
if "%choice%"=="4" goto open_config
if "%choice%"=="5" goto open_output
if "%choice%"=="0" goto exit
goto menu

:check
cls
echo.
echo [环境检查]
echo.
python scripts\check_environment.py
python scripts\literature\test_browser_detection.py
echo.
pause
goto menu

:cnki
cls
echo.
echo [CNKI文献检索]
echo.
echo 正在运行CNKI检索...
python scripts\literature\build_cnki_pool.py --spec thesis-ai-standard\templates\thesis-ai-spec.yaml --output paper-context\literature\
echo.
echo [完成] 文献已保存到 paper-context\literature\
echo.
pause
goto menu

:generate
cls
echo.
echo [生成论文]
echo.
echo 请确保已填写: thesis-ai-standard\templates\thesis-ai-spec.yaml
echo.
echo 正在生成论文...
python scripts\docx\build_complete_thesis.py --spec thesis-ai-standard\templates\thesis-ai-spec.yaml --body paper-output\thesis-body.md --output paper-output\
echo.
echo [完成] 论文已保存到 paper-output\
echo.
pause
goto menu

:open_config
explorer thesis-ai-standard\templates
pause
goto menu

:open_output
explorer paper-output
pause
goto menu

:exit
echo.
echo 感谢使用 Chinese Thesis Workbench
echo.
timeout /t 2 >nul
exit /b
