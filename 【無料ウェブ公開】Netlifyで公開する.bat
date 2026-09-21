@echo off
title KEIBA AI PRO - Free Web Deploy
echo ============================================================
echo   KEIBA AI PRO: Free Web Hosting (Netlify Drop)
echo ============================================================
echo.
echo Opening Netlify Drop in your browser...
start https://app.netlify.com/drop
echo.
echo Opening folder with keiba-app.zip...
explorer.exe /select,"%~dp0keiba-app.zip"
echo.
echo ============================================================
echo   HOW TO DEPLOY IN 3 SECONDS:
echo   1. Drag and drop 'keiba-app.zip' into the browser window.
echo   2. You will instantly get a permanent free HTTPS URL!
echo   3. Open that URL on your iPhone 17 and Add to Home Screen!
echo ============================================================
pause
