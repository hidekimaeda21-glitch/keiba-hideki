@echo off
title KEIBA AI PRO - GitHub Pages (keiba-hideki)
echo ============================================================
echo   KEIBA AI PRO: GitHub Pages デプロイ (keiba-hideki)
echo ============================================================
echo.
echo リポジトリ名「keiba-hideki」の作成画面を開いています...
start https://github.com/new?name=keiba-hideki
echo.
echo アップロード用フォルダ「keiba-hideki」を開いています...
explorer.exe "%~dp0keiba-hideki"
echo.
echo ============================================================
echo   【簡単3ステップ】
echo   1. ブラウザに「keiba-hideki」が自動入力されています。
echo      「Public」にチェックが付いているのを確認し、
echo      一番下の緑色の「Create repository」ボタンを押します。
echo.
echo   2. 表示された画面の「uploading an existing file」を押します。
echo      開いた「keiba-hideki」フォルダの中身をすべてドラッグ＆ドロップし、
echo      「Commit changes」を押します。
echo.
echo   3. 画面上の「Settings」→「Pages」を開き、
echo      Branch で「main」を選んで「Save」を押します。
echo.
echo   ==> これで完了！パソコンの電源を切っても動くURLが発行されます！
echo ============================================================
pause
