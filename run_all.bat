@echo off
setlocal ENABLEDELAYEDEXPANSION

echo ========================================
echo Full Autocharter Workflow
echo ========================================
echo.

call ./process_songs.bat
if errorlevel 1 goto :failed

echo.
echo --- Converting audio to Opus ---
call ./convert_opus.bat
if errorlevel 1 goto :failed

echo.
echo --- Running MIDI-CH Auto-Chart ---
call ./auto-chart.bat
if errorlevel 1 goto :failed

:success
echo.
echo ========================================
echo Workflow completed successfully.
echo ========================================
exit /b 0

:failed
echo.
echo ========================================
echo Workflow aborted due to errors.
echo ========================================
exit /b 1
