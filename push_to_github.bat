@echo off
echo 🚀 推送项目到GitHub...
echo.

echo 📡 添加远程仓库...
git remote add origin https://github.com/swllljjz/python-OCR-date.git

echo 📤 推送代码到GitHub...
git branch -M main
git push -u origin main

echo.
echo ✅ 推送完成！
echo 🌐 仓库地址: https://github.com/swllljjz/python-OCR-date
echo.
pause
