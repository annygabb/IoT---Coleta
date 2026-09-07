import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse

from apps.api.app.api.v1.endpoints import router as api_router, get_engine
from apps.api.app.api.v1.ws import ws_router, manager


# Background worker para avançar o motor de simulação discretamente.
async def simulation_ticker_worker():
    engine = get_engine()
    last_time = asyncio.get_event_loop().time()
    while True:
        now = asyncio.get_event_loop().time()
        delta_wall_seconds = min(0.2, now - last_time)
        last_time = now

        # Executa passo determinístico no motor.
        engine.step(delta_wall_seconds)

        await asyncio.sleep(0.1)  # 10 ticks/segundo de parede


@asynccontextmanager
async def lifespan(app: FastAPI):
    ticker_task = asyncio.create_task(simulation_ticker_worker())
    yield
    ticker_task.cancel()


app = FastAPI(
    title="SmartWaste DF — Backend de Simulação IoT",
    description="Digital Twin e Laboratório Open Source para Coleta Inteligente de Resíduos Urbanos no DF.",
    version="2.7.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
app.include_router(ws_router)

base_dir = Path(__file__).resolve().parent.parent.parent
enhancement_script = base_dir / "apps" / "web" / "routing-docs-enhancements.js"


@app.get("/smartwaste-routing-docs.js", include_in_schema=False)
def serve_routing_docs_enhancement():
    """Entrega o patch de alinhamento das estratégias e do relatório PDF."""
    return FileResponse(enhancement_script, media_type="application/javascript")


if (base_dir / "index.html").exists():
    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    def serve_index():
        """
        Serve a interface integrada e injeta o módulo de documentação de rotas.

        O index.html continua utilizável como demo estática; no modo laboratório
        (porta 8000) o patch mantém frontend/backend alinhados e enriquece o PDF.
        """
        html = (base_dir / "index.html").read_text(encoding="utf-8")
        script_tag = '<script src="/smartwaste-routing-docs.js"></script>'
        if enhancement_script.exists() and script_tag not in html:
            html = html.replace("</body>", f"  {script_tag}\n</body>")
        return HTMLResponse(html)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("apps.api.main:app", host="0.0.0.0", port=8000, reload=True)
