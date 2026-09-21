@echo off
title KEIBA AI PRO - Firewall Unblock
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [Admin elevation...]
    powershell -NoProfile -Command "Start-Process '%~0' -Verb RunAs"
    exit /b
)

echo ============================================================
echo   KEIBA AI PRO: Port 8080 Firewall Unblock
echo ============================================================
netsh advfirewall firewall delete rule name="KEIBA_AI_PRO_8080" >nul 2>&1
netsh advfirewall firewall add rule name="KEIBA_AI_PRO_8080" dir=in action=allow protocol=TCP localport=8080 profile=any >nul

echo.
echo [SUCCESS] Windows Firewall block for Port 8080 has been REMOVED!
echo iPhone can now connect freely to this PC.
echo.
pause
