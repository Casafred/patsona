@echo off
echo ========================================
echo Patsona 专利分类系统启动脚本
echo ========================================
echo.

cd /d "%~dp0"

:: 检查Python虚拟环境
if not exist "..\\.venv\\Scripts\\activate.bat" (
    echo [警告] 未找到Python虚拟环境，请先创建虚拟环境
    echo 运行: python -m venv .venv
    echo 然后运行: .venv\\Scripts\\activate && pip install -r requirements.txt
    pause
    exit /b 1
)

:: 检查Node.js
where npm >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [错误] 未找到Node.js，请先安装Node.js
    pause
    exit /b 1
)

:: 检查前端依赖
if not exist "frontend\\node_modules" (
    echo [安装] 正在安装前端依赖...
    cd frontend
    call npm install
    cd ..
)

:: 启动后端服务
echo [启动] 正在启动后端服务 (端口: 8000)...
start "Patsona Backend" cmd /k "cd /d "%~dp0backend" && call ..\\..\\.venv\\Scripts\\activate.bat && uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

:: 等待后端启动
timeout /t 3 /nobreak >nul

:: 启动前端服务
echo [启动] 正在启动前端服务 (端口: 3000)...
start "Patsona Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"

echo.
echo ========================================
echo 服务已启动!
echo 后端地址: http://localhost:8000
echo 前端地址: http://localhost:3000
echo API文档:  http://localhost:8000/docs
echo ========================================
echo.
echo 按任意键打开前端页面...
pause >nul

:: 打开浏览器
start http://localhost:3000

echo.
echo 提示: 关闭此窗口不会停止服务
echo 要停止服务请关闭后端和前端的命令行窗口
pause