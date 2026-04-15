@echo off
echo === DEPLOYING TELEGRAM BOT ===

REM Check if Docker is installed
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Docker is not installed. Please install Docker Desktop first.
    pause
    exit /b 1
)

REM Build and run with Docker Compose
echo Building Docker image...
docker-compose build

echo Starting bot container...
docker-compose up -d

echo Checking status...
docker-compose ps

echo === BOT DEPLOYED SUCCESSFULLY ===
echo View logs: docker-compose logs -f bot
echo Stop bot: docker-compose down
pause
