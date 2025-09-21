@echo off
setlocal DisableDelayedExpansion

set "ROOT=%CD%"
set "IMAGE=ffmpeg-opus"
set "DOCKERFILE=Dockerfile.opus"
set "OUTPUT_DIR=opus-output"
set "SCRIPT=%~dp0tools\convert_opus.ps1"

if exist "%ROOT%\%DOCKERFILE%" (
  echo Building %IMAGE% image from %DOCKERFILE%...
  docker build -f "%DOCKERFILE%" -t %IMAGE% .
  if errorlevel 1 (
    echo Docker build failed. Aborting.
    exit /b 1
  )
) else (
  echo %DOCKERFILE% not found at %ROOT%. Aborting.
  exit /b 1
)

echo ========================================
echo MP3 -^> Opus Batch Converter
echo ========================================
echo.

if not exist "%SCRIPT%" (
  echo PowerShell helper script not found: %SCRIPT%
  exit /b 1
)

echo Converting files...
if "%~1"=="" (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT%" -Root "%ROOT%" -Image "%IMAGE%" -OutputDir "%OUTPUT_DIR%"
) else (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT%" -Root "%ROOT%" -Image "%IMAGE%" -OutputDir "%OUTPUT_DIR%" -Inputs %*
)
if errorlevel 1 (
  echo Conversion failed.
  pause
  exit /b 1
)

echo.
echo ========================================
echo Conversion complete. Check the "%OUTPUT_DIR%" folder.
echo ========================================
pause
exit /b 0
