@echo off
setlocal ENABLEDELAYEDEXPANSION

set "ROOT=%CD%"

echo ========================================
echo Clone Hero Audio -^> MIDI Batch Processor
echo ========================================
echo.

set "IMAGE=ch-midi"
set "LEAD=vocals"
set "DRUMS=skip"
set "OUT_ROOT=out"
set "SEPARATED_ROOT=separated"

echo Resetting previous outputs...
if exist "%ROOT%\%OUT_ROOT%" (
  echo   Clearing "%OUT_ROOT%"...
  rd /s /q "%ROOT%\%OUT_ROOT%"
)
if exist "%ROOT%\%SEPARATED_ROOT%" (
  echo   Clearing "%SEPARATED_ROOT%"...
  rd /s /q "%ROOT%\%SEPARATED_ROOT%"
)
mkdir "%ROOT%\%OUT_ROOT%" >nul 2>&1
mkdir "%ROOT%\%SEPARATED_ROOT%" >nul 2>&1

echo.

if "%~1"=="" goto process_all

echo Processing provided inputs...
call :process_args %*
goto done

:process_all
if not exist "songs" (
  echo The "songs" folder is missing. Create it and add MP3/WAV files.
  goto done
)

echo No arguments provided. Processing all MP3/WAV in "songs\"...
set "HAS_FILES="
for /f "delims=" %%F in ('dir /b /a:-d "songs\*.mp3" 2^>nul') do call :queue_file "songs\%%F"
for /f "delims=" %%F in ('dir /b /a:-d "songs\*.wav" 2^>nul') do call :queue_file "songs\%%F"
if not defined HAS_FILES echo No MP3 or WAV files found in "songs\".
goto done

:process_args
if "%~1"=="" goto :eof
call :process_one "%~1"
shift
goto process_args

:queue_file
set "HAS_FILES=1"
call :process_one "%~1"
goto :eof

:process_one
if "%~1"=="" goto :eof
set "TARGET_PATH="
if exist "%~1" set "TARGET_PATH=%~1"
if not defined TARGET_PATH if exist "songs\%~1" set "TARGET_PATH=songs\%~1"
if not defined TARGET_PATH goto missing_target

set "REL_WORK=%TARGET_PATH%"
set "DRIVEFLAG=%TARGET_PATH:~1,1%"
if /I "%DRIVEFLAG%"==":" goto absolute_target
if "!REL_WORK:~0,2!"==".\" set "REL_WORK=!REL_WORK:~2!"
goto normalize_rel

:absolute_target
set "REL_WORK=!TARGET_PATH:%ROOT%=!"
if "!REL_WORK!"=="!TARGET_PATH!" goto outside_root
if "!REL_WORK:~0,1!"=="\" set "REL_WORK=!REL_WORK:~1!"

:normalize_rel
set "REL_FWD=!REL_WORK:\=/!"
if "!REL_FWD:~0,1!"=="/" set "REL_FWD=!REL_FWD:~1!"
set "DISPLAY=%~nx1"

echo.
echo --- Processing "!DISPLAY!" ---

docker run --rm -v "%ROOT%":/work %IMAGE% "!REL_FWD!" --out "%OUT_ROOT%" --lead %LEAD% --drums %DRUMS%
goto :eof

:missing_target
echo Skipping "%~1" (not found).
goto :eof

:outside_root
echo Skipping "%~1" (outside project root).
goto :eof

:done
echo.
echo ========================================
echo Processing completed! Check the "%OUT_ROOT%" folder.
echo ========================================
pause
goto :eof
