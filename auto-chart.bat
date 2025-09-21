@echo off
setlocal ENABLEDELAYEDEXPANSION

set "ROOT=%CD%"
set "IMAGE=midi-ch-batch"
set "INPUT_DIR=out"
set "OUTPUT_DIR=charts"
set "DOCKERFILE=Dockerfile.midi-ch"

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

if "%~1"=="" goto after_args

:parse_args
if "%~1"=="" goto after_args
if /I "%~1"=="--help" goto show_help
if /I "%~1"=="/h" goto show_help
if /I "%~1"=="-h" goto show_help
if /I "%~1"=="--input" (
  shift
  if "%~1"=="" (
    echo Missing value for --input
    exit /b 1
  )
  set "INPUT_DIR=%~1"
  shift
  goto parse_args
)
if /I "%~1"=="--output" (
  shift
  if "%~1"=="" (
    echo Missing value for --output
    exit /b 1
  )
  set "OUTPUT_DIR=%~1"
  shift
  goto parse_args
)
if /I "%~1"=="--image" (
  shift
  if "%~1"=="" (
    echo Missing value for --image
    exit /b 1
  )
  set "IMAGE=%~1"
  shift
  goto parse_args
)
if /I "%~1"=="--" (
  shift
  goto passthrough
)

echo Unknown option: %~1
exit /b 1

:passthrough
set "EXTRA_ARGS=%*"
goto after_args

:show_help
echo Usage: auto-chart.bat [--input DIR] [--output DIR] [--image IMAGE]
echo.
echo Options:
echo   --input DIR   Relative path (from repo root) to search for merged.mid files ^(default: out^)
echo   --output DIR  Relative path to place generated charts ^(default: charts^)
echo   --image IMAGE Docker image name to run ^(default: midi-ch-batch^)
echo   --help        Show this help message
echo.
echo Example:
echo   auto-chart.bat --input out --output charts
exit /b 0

:after_args
call :resolve_path "%INPUT_DIR%" INPUT_REL INPUT_ABS || exit /b 1
call :resolve_path "%OUTPUT_DIR%" OUTPUT_REL OUTPUT_ABS || exit /b 1

if not exist "!INPUT_ABS!" (
  echo Input directory not found: !INPUT_ABS!
  exit /b 1
)

if not exist "!OUTPUT_ABS!" (
  echo Creating output directory: !OUTPUT_ABS!
  mkdir "!OUTPUT_ABS!" >nul 2>&1
)

echo Running MIDI-CH auto-chart...
echo   Image : %IMAGE%
echo   Input : !INPUT_ABS!

echo   Output: !OUTPUT_ABS!

docker run --rm -v "%ROOT%":/work %IMAGE% --input "/work/!INPUT_REL!" --output "/work/!OUTPUT_REL!" %EXTRA_ARGS%
exit /b %ERRORLEVEL%

:resolve_path
setlocal ENABLEDELAYEDEXPANSION
set "TARGET=%~1"
if not defined TARGET (
  echo Missing path value.
  exit /b 1
)
for %%I in ("%TARGET%") do set "ABS=%%~fI"
set "REL=!ABS:%ROOT%\=!"
if "!REL!"=="!ABS!" (
  echo Path "!ABS!" is outside the project root.
  exit /b 1
)
if "!REL:~0,1!"=="\" set "REL=!REL:~1!"
set "REL=!REL:\=/!"
if "!REL!"=="" set "REL=."
endlocal & set "%2=%REL%" & set "%3=%ABS%"
exit /b 0
