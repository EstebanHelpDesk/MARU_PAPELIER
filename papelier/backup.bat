@echo off
setlocal enabledelayedexpansion

:: Obtener la fecha actual en formato YYYYMMDD
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value ^| find "="') do set datetime=%%I
set fecha=!datetime:~0,4!!datetime:~4,2!!datetime:~6,2!

:: Definir rutas
set ORIGEN=C:\FTP\PAPELIER\MARU_PAPELIER\papelier
set DESTINO=C:\FTP\PAPELIER\backup
set TEMPORAL=%TEMP%\backup_papelier
set ARCHIVO_ZIP=BACKUP_!fecha!.zip

:: Crear carpeta temporal
if exist "!TEMPORAL!" rd /s /q "!TEMPORAL!"
mkdir "!TEMPORAL!"

:: Copiar archivos, incluyendo los que están en uso
robocopy "!ORIGEN!" "!TEMPORAL!" /E /COPY:DAT /R:0 /W:0

:: Verificar si la carpeta de destino existe, si no, crearla
if not exist "!DESTINO!" mkdir "!DESTINO!"

:: Comprimir la carpeta temporal
powershell -command "Compress-Archive -Path '!TEMPORAL!\*' -DestinationPath '!DESTINO!\!ARCHIVO_ZIP!' -Force" >>backup.log

:: Eliminar carpeta temporal
rd /s /q "!TEMPORAL!"

echo Backup completado: !DESTINO!\!ARCHIVO_ZIP!
exit /b
