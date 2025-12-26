from fastapi import FastAPI
from api.routes.indexar import router as indexar_router

app = FastAPI(title="NEO RAG API")

app.include_router(indexar_router)
