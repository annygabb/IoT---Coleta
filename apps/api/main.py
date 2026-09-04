import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from apps.api.app.api.v1.endpoints import router as api_router, get_engine
from apps.api.app.api.v1.ws import ws_router, manager

# Background worker para avançar o motor de simulação discretamente
async def simulation_ticker_worker():
    engine = get_engine()
    last_time = asyncio.get_event_loop().time()
    while True:
        now = asyncio.get_event_loop().time()
        delta_wall_seconds = min(0.2, now - last_time)
        last_time = now

        # Executa passo determinístico no motor
        engine.step(delta_wall_seconds)

        await asyncio.sleep(0.1) # 10 ticks/segundo de parede

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicialização
    ticker_task = asyncio.create_task(simulation_ticker_worker())
    yield
    # Finalização graciosa
    ticker_task.cancel()

app = FastAPI(
    title="SmartWaste DF — Backend de Simulação IoT",
    description="Digital Twin e Laboratório Open Source para Coleta Inteligente de Resíduos Urbanos no DF.",
    version="2.6.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Registra rotas da API e WebSockets
app.include_router(api_router)
app.include_router(ws_router)

# Servir static files da interface caso existam
base_dir = Path(__file__).resolve().parent.parent.parent
if (base_dir / "index.html").exists():
    # Rota raiz opcional para testar diretamente pelo backend
    from fastapi.responses import FileResponse
    @app.get("/")
    def serve_index():
        return FileResponse(base_dir / "index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("apps.api.main:app", host="0.0.0.0", port=8000, reload=True)
