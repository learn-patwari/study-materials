@echo off
set QTWEBENGINE_DISABLE_SANDBOX=1
set QTWEBENGINE_CHROMIUM_FLAGS=--disable-gpu --in-process-gpu --use-gl=swiftshader-webgl
python main.py 2>nul
