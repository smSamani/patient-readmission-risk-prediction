from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import clinical, health, interventions, patients, risk, shap, summary, ai
from app.utils.errors import register_error_handlers

app = FastAPI(
    title="Diabetes Readmission Intelligence API",
    version="0.1.0",
    description="Backend API for the precomputed diabetes readmission dashboard demo.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_error_handlers(app)

for router in [health.router, patients.router, risk.router, shap.router, clinical.router, interventions.router, summary.router, ai.router]:
    app.include_router(router, prefix="/api")
