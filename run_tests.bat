@echo off
REM Run CircularX backend test suite on Windows

setlocal enabledelayedexpansion

set BASE_URL=%1
if "!BASE_URL!"=="" set BASE_URL=http://127.0.0.1:8000

set VERBOSE=%2
if "!VERBOSE!"=="" set VERBOSE=-v

echo Starting CircularX Backend Test Suite...
echo Base URL: !BASE_URL!
echo.

python test_suite.py --base-url "!BASE_URL!" !VERBOSE!

exit /b %ERRORLEVEL%
