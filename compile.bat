@echo off
title Compiler

echo ========================================
echo Looking for MinGW compiler...
echo ========================================

:: مسیر پیش‌فرض برای mingw32
set "GCC_PATH=.\mingw32\bin"

if exist "%GCC_PATH%\g++.exe" (
    echo [OK] Found g++ at %GCC_PATH%
    set PATH=%GCC_PATH%;%PATH%
) else (
    echo [ERROR] g++.exe not found in mingw32\bin!
    echo.
    echo لطفاً پوشه mingw32 خود را باز کنید و ببینید فایل g++.exe دقیقاً کجاست.
    echo سپس مسیر را در این فایل bat اصلاح کنید.
    echo.
    echo فعلاً این پوشه‌ها را بررسی کنید:
    dir .\mingw32 /s /b | find "g++.exe"
    echo.
    pause
    exit /b 1
)

echo.
echo Compiling FirewallBlocker.cpp ...
echo ========================================

g++ -static -mwindows -o FirewallBlocker.exe FirewallBlocker.cpp -lcomctl32 -lshell32 -lshlwapi -lgdi32 -luser32 -lole32

if %errorlevel% equ 0 (
    echo.
    echo ==========================================================
    echo [SUCCESS] FirewallBlocker.exe created successfully!
    echo ==========================================================
    dir FirewallBlocker.exe
) else (
    echo.
    echo ==========================================================
    echo [FAILED] Compilation error!
    echo ==========================================================
    echo.
    echo Compiler error.
)

echo.
pause