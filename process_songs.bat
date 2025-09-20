@echo off
setlocal ENABLEDELAYEDEXPANSION

echo ========================================
echo Clone Hero Audio -^> MIDI Batch Processor
echo ========================================
echo.

set "IMAGE=ch-midi"
set "LEAD=vocals"
set "DRUMS=skip"
set "OUT_ROOT=out"

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
for /f "delims=" %%F in ('dir /b /a:-d "songs\*.mp3" 2^>nul') do (
  set "HAS_FILES=1"
  call :process_one "songs\%%F"
)
for /f "delims=" %%F in ('dir /b /a:-d "songs\*.wav" 2^>nul') do (
  set "HAS_FILES=1"
  call :process_one "songs\%%F"
)
if not defined HAS_FILES (
  echo No MP3 or WAV files found in "songs\".
)
goto done

:process_args
if "%~1"=="" goto :eof
call :process_one "%~1"
shift
goto process_args

:done
echo.
echo ========================================
echo Processing completed! Check the "%OUT_ROOT%" folder.
echo ========================================
pause
goto :eof

:process_one
if exist "%~1" goto have_file
if exist "songs\%~1" (
  call :process_one "songs\%~1"
  goto :eof
)

echo Skipping "%~1" (not found).
goto :eof

:have_file
set "REL_WIN=%~f1"
set "REL_FWD=%REL_WIN:\=/%"
set "DISPLAY=%~nx1"

echo.
echo --- Processing "!DISPLAY!" ---

docker run --rm -v "%cd%":/work %IMAGE% python /usr/local/bin/pipeline.py "!REL_FWD!" --out "%OUT_ROOT%" --lead %LEAD% --drums %DRUMS%
goto :eof
