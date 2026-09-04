"""
Script de Inicialização de 1 Comando do SmartWaste DF (DoD-01).
Inicia o backend modular FastAPI na porta 8000 com WebSocket, MQTT broker virtual e interface integrada.
"""
import sys
import webbrowser
import uvicorn

def main():
    print("==================================================================")
    print("       SMARTWASTE DF — DIGITAL TWIN & LABORATÓRIO IOT            ")
    print("==================================================================")
    print("[1/2] Iniciando Backend FastAPI com WebSocket e Broker MQTT...")
    print("      URL da Aplicação: http://localhost:8000")
    print("      Swagger OpenAPI:  http://localhost:8000/docs")
    print("==================================================================")
    
    # Abre o navegador automaticamente
    try:
        webbrowser.open("http://localhost:8000")
    except Exception:
        pass

    # Executa o servidor uvicorn
    uvicorn.run("apps.api.main:app", host="0.0.0.0", port=8000, log_level="info")

if __name__ == "__main__":
    main()
