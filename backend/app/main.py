from fastapi import FastAPI
import asyncio
from app.services.es_client import init_ilm
from app.api.dark_web import router
from app.database.database import engine, Base  # For DB init

app = FastAPI()

# Include routers
app.include_router(router, prefix="/dark_web")

@app.on_event("startup")
async def startup():
    # Init DB if needed
    Base.metadata.create_all(bind=engine)
    # Init ES ILM
    asyncio.create_task(init_ilm())

@app.get("/health")
async def health():
    return {"status": "ok"}