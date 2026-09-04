# Guia de Troubleshooting — SmartWaste DF

## 1. Porta 5173 ou 8000 já em uso
Se ao iniciar o laboratório ocorrer um erro de `Address already in use`:
* **Windows (PowerShell):**
  ```powershell
  Get-NetTCPConnection -LocalPort 5173, 8000 | Select-Object OwningProcess
  Stop-Process -Id <PID> -Force
  ```
* Alternativamente, inicie o servidor em outra porta especificando a porta no comando:
  ```powershell
  python -m uvicorn apps.api.main:app --port 8001
  ```

## 2. Docker / Podman não encontrado na máquina
O projeto foi explicitamente projetado para **funcionar sem dependência obrigatória de containers**. O modo laboratório em Python nativo executa todas as regras, contratos, WebSocket e endpoints REST diretamente no ambiente local.

## 3. Modo Offline / Falha de Conexão à Internet
O SmartWaste DF é **offline-first**:
* Os dados geográficos das Regiões Administrativas e malha viária estão embutidos localmente no repositório (`apps/api/app/domain/geo/brasilia_network.py` e `data/geo/`).
* A interface possui modo autônomo PWA que executa a simulação completa localmente caso o backend não esteja ativo.
