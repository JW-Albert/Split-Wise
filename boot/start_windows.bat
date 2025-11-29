@echo off
REM Split-Wise Windows 開機自動啟動腳本
REM 將此腳本加入 Windows 啟動資料夾即可實現開機自動啟動

cd /d "%~dp0\.."

REM 啟動虛擬環境並執行應用程式
call venv\Scripts\activate.bat
python src\app.py

pause

