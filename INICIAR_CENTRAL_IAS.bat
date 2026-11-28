@echo off
title Central Inteligente de Shorts - IAS / VIAGEM
color 0A
chcp 65001 > nul

echo =====================================================================
echo    CENTRAL INTELIGENTE DE YOUTUBE SHORTS (20 CANAIS & DRIVE 5TB)     
echo =====================================================================
echo.
echo [1/3] Verificando ambiente Python...
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERRO] Python nao encontrado no PATH do sistema.
    pause
    exit /b 1
)

echo [2/3] Abrindo interface no navegador padrao...
start http://127.0.0.1:8000

echo [3/3] Inicializando servidor FastAPI e Central Operacional...
echo ---------------------------------------------------------------------
echo  Painel de Controle : http://127.0.0.1:8000
echo  Documentacao Swagger: http://127.0.0.1:8000/docs
echo  Pressione Ctrl+C para encerrar o servidor a qualquer momento.
echo ---------------------------------------------------------------------
echo.

python run_dashboard.py

pause
