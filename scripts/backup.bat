@echo off
setlocal EnableDelayedExpansion

set BACKUP_DIR=backups

REM Create backup dir if missing
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

REM Get safe timestamp using WMIC (NO spaces, NO slashes)
for /f "tokens=2 delims==." %%a in ('wmic os get localdatetime /value') do set TS=%%a

REM Extract clean values: YYYYMMDDHHMMSS
set YYYY=%TS:~0,4%
set MM=%TS:~4,2%
set DD=%TS:~6,2%
set HH=%TS:~8,2%
set MIN=%TS:~10,2%
set SEC=%TS:~12,2%

set TIMESTAMP=%YYYY%%MM%%DD%_%HH%%MIN%%SEC%

echo Backing up database...

if exist db.sqlite3 (
    copy db.sqlite3 "%BACKUP_DIR%\db_%TIMESTAMP%.sqlite3"
) else (
    echo ERROR: db.sqlite3 not found!
)

echo Backing up media...

if exist media (
    powershell -Command "Compress-Archive -Path 'media' -DestinationPath '%BACKUP_DIR%\media_%TIMESTAMP%.zip' -Force"
) else (
    echo ERROR: media folder not found!
)

echo Backup completed.
pause