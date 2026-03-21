"""FastAPI application for the ETL producer service."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from etl.api.auth import router as auth_router
from etl.api.config_routes import router as config_router
from etl.api.folders_routes import router as folders_router
from etl.api.sync_routes import router as sync_router
from etl.api.notion_routes import router as notion_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(title="ETL Producer API", version="1.0.0")

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(config_router)
app.include_router(folders_router)
app.include_router(sync_router)
app.include_router(notion_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
