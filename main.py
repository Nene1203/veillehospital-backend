from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import os
import time

from database import engine, Base, get_db
from routers import etablissements, campagnes, veilles, dashboard
from auth import router as auth_router, get_current_user
import audit_models
from audit_router import router as audit_router_obj

load_dotenv()

# Créer toutes les tables (y compris audit_logs et error_logs)
Base.metadata.create_all(bind=engine)
audit_models.AuditLog.__table__.create(bind=engine, checkfirst=True)
audit_models.ErrorLog.__table__.create(bind=engine, checkfirst=True)

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


# ─── Middleware d'audit automatique ───────────────────────────
@app.middleware("http")
async def audit_middleware(request: Request, call_next):
    """Capture automatiquement les erreurs 4xx/5xx."""
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    # Logger les erreurs automatiquement
    if response.status_code in [401, 403, 404, 500, 422]:
        from audit_service import log_error, get_client_ip
        from sqlalchemy.orm import Session
        db: Session = next(get_db())
        try:
            error_types = {401: "unauthorized", 403: "access_denied", 404: "not_found", 500: "server_error", 422: "validation_error"}
            log_error(db,
                error_code=response.status_code,
                error_type=error_types.get(response.status_code, "unknown"),
                error_message=f"HTTP {response.status_code}",
                endpoint=str(request.url.path),
                method=request.method,
                ip_address=request.client.host if request.client else "unknown",
                user_agent=request.headers.get("User-Agent", ""),
                details={"duration_ms": round(duration * 1000, 2), "query_params": str(request.query_params)}
            )
        except Exception:
            pass
        finally:
            db.close()

    return response


# ─── Routers ──────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(audit_router_obj, dependencies=[Depends(get_current_user)])
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
