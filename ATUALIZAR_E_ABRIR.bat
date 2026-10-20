@echo off
chcp 65001 >nul
cd /d "%~dp0"
py -3.12 --version >nul 2>&1
if errorlevel 1 (
  echo Instale o Python 3.12 com: py install 3.12
  pause
  exit /b 1
)
if not exist ".venv312\Scripts\python.exe" py -3.12 -m venv .venv312
".venv312\Scripts\python.exe" -m pip install -r requirements-distributed.txt
if errorlevel 1 (
  echo A instalacao apresentou erro. Copie a mensagem para analise.
  pause
  exit /b 1
)
if not exist "SmartWaste_Conexao_Privada.json" (
  echo Copie SmartWaste_Conexao_Privada.json para esta pasta antes de iniciar.
  pause
  exit /b 1
)
".venv312\Scripts\python.exe" run_distributed.py --cloud-config SmartWaste_Conexao_Privada.json
pause
