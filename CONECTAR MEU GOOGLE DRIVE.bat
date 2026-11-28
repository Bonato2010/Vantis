@echo off
title Conectar Google Drive 5 TB
echo =====================================================================
echo    CONECTANDO O SEU GOOGLE DRIVE DE 5 TB A CENTRAL SHORTS
echo =====================================================================
echo.
cd /d "%~dp0"
echo Diretorio atual: %CD%
echo.
echo Iniciando autenticacao...
python auth_drive.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERRO] Ocorreu um problema ao executar o script.
    echo Verifique a mensagem acima.
) else (
    echo.
    echo [SUCESSO] Conexao concluida com sucesso!
)
echo.
echo Pressione qualquer tecla para fechar.
pause > nul
