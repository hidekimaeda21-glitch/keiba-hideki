@echo off
title KEIBA AI PRO - GitHub Pages Upload
echo ============================================================
echo   KEIBA AI PRO: GitHub アップロード画面を開いています...
echo ============================================================
echo.
echo ブラウザで「ファイル追加画面」を直接開きます...
start https://github.com/hidekimaeda21-glitch/keiba-hideki/upload/main
echo.
echo アップロード対象の「keiba-hideki」フォルダを開いています...
explorer.exe "%~dp0keiba-hideki"
echo.
echo ============================================================
echo   【超簡単！2ステップで完了】
echo.
echo   ステップ 1:
echo     ブラウザ画面の大きな点線枠の中に、
echo     開いたフォルダ内の全ファイル（index.html等）を
echo     まとめてドラッグ＆ドロップしてください。
echo     アップロード完了後、緑色の「Commit changes」を押します。
echo.
echo   ステップ 2:
echo     その後、下のリンク（Pages設定画面）を開き、
echo     Branch を「main」にして「Save」を押してください。
echo     https://github.com/hidekimaeda21-glitch/keiba-hideki/settings/pages
echo.
echo   ==> これで完了！パソコンの電源を切ってもiPhoneで永久に動きます！
echo ============================================================
pause
