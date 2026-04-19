from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

from database import engine, Base
from routers import etablissements, campagnes, veilles, dashboard
from auth import router as auth_router, get_current_user

load_dotenv()

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="VeilleHospital API",
    description="API de suivi des veilles hospitalières",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth (public)
app.include_router(auth_router)

# Routes protégées par JWT
app.include_router(etablissements.router, dependencies=[Depends(get_current_user)])
app.include_router(campagnes.router, dependencies=[Depends(get_current_user)])
app.include_router(veilles.router, dependencies=[Depends(get_current_user)])
app.include_router(dashboard.router, dependencies=[Depends(get_current_user)])


@app.get("/")
def root():
    return {"message": "VeilleHospital API v2", "docs": "/docs"}

@app.get("/health")
def health():
    return {"status": "ok"}
