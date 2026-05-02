import csv
import io
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional
from datetime import datetime, date

from database import get_db
from auth import require_admin
from audit_models import AuditLog, ErrorLog

router = APIRouter(prefix="/audit", tags=["Audit"])


# ─── Audit Logs ───────────────────────────────────────────────
@router.get("/logs")
def get_audit_logs(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    action: Optional[str] = Query(None),
    user_email: Optional[str] = Query(None),
    date_debut: Optional[date] = Query(None),
    date_fin: Optional[date] = Query(None),
    statut: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(require_admin)
):
    q = db.query(AuditLog).order_by(desc(AuditLog.timestamp))

    if action:
        q = q.filter(AuditLog.action == action)
    if user_email:
        q = q.filter(AuditLog.user_email.ilike(f"%{user_email}%"))
    if date_debut:
        q = q.filter(AuditLog.timestamp >= datetime.combine(date_debut, datetime.min.time()))
    if date_fin:
        q = q.filter(AuditLog.timestamp <= datetime.combine(date_fin, datetime.max.time()))
    if statut:
        q = q.filter(AuditLog.statut == statut)

    total = q.count()
    logs = q.offset((page - 1) * limit).limit(limit).all()

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit,
        "logs": [
            {
                "id": str(l.id),
                "timestamp": l.timestamp.isoformat() if l.timestamp else None,
                "user_email": l.user_email,
                "user_role": l.user_role,
                "action": l.action,
                "resource": l.resource,
                "resource_id": l.resource_id,
                "details": l.details,
                "ip_address": l.ip_address,
                "statut": l.statut,
            }
            for l in logs
        ]
    }


@router.get("/logs/export-csv")
def export_audit_csv(
    date_debut: Optional[date] = Query(None),
    date_fin: Optional[date] = Query(None),
    action: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(require_admin)
):
    """Exporte les logs d'audit en CSV."""
    q = db.query(AuditLog).order_by(desc(AuditLog.timestamp))
    if date_debut:
        q = q.filter(AuditLog.timestamp >= datetime.combine(date_debut, datetime.min.time()))
    if date_fin:
        q = q.filter(AuditLog.timestamp <= datetime.combine(date_fin, datetime.max.time()))
    if action:
        q = q.filter(AuditLog.action == action)

    logs = q.all()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(["Date/Heure", "Utilisateur", "Rôle", "Action", "Ressource", "ID Ressource", "Détails", "IP", "Statut"])
    for l in logs:
        writer.writerow([
            l.timestamp.strftime("%d/%m/%Y %H:%M:%S") if l.timestamp else "",
            l.user_email or "",
            l.user_role or "",
            l.action or "",
            l.resource or "",
            l.resource_id or "",
            str(l.details) if l.details else "",
            l.ip_address or "",
            l.statut or "",
        ])

    output.seek(0)
    filename = f"audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ─── Error Logs ───────────────────────────────────────────────
@router.get("/errors")
def get_error_logs(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    error_code: Optional[int] = Query(None),
    date_debut: Optional[date] = Query(None),
    date_fin: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(require_admin)
):
    q = db.query(ErrorLog).order_by(desc(ErrorLog.timestamp))

    if error_code:
        q = q.filter(ErrorLog.error_code == error_code)
    if date_debut:
        q = q.filter(ErrorLog.timestamp >= datetime.combine(date_debut, datetime.min.time()))
    if date_fin:
        q = q.filter(ErrorLog.timestamp <= datetime.combine(date_fin, datetime.max.time()))

    total = q.count()
    errors = q.offset((page - 1) * limit).limit(limit).all()

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit,
        "errors": [
            {
                "id": str(e.id),
                "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                "user_email": e.user_email,
                "error_code": e.error_code,
                "error_type": e.error_type,
                "error_message": e.error_message,
                "endpoint": e.endpoint,
                "method": e.method,
                "ip_address": e.ip_address,
            }
            for e in errors
        ]
    }


@router.get("/errors/export-csv")
def export_errors_csv(
    date_debut: Optional[date] = Query(None),
    date_fin: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(require_admin)
):
    """Exporte les erreurs en CSV."""
    q = db.query(ErrorLog).order_by(desc(ErrorLog.timestamp))
    if date_debut:
        q = q.filter(ErrorLog.timestamp >= datetime.combine(date_debut, datetime.min.time()))
    if date_fin:
        q = q.filter(ErrorLog.timestamp <= datetime.combine(date_fin, datetime.max.time()))

    errors = q.all()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(["Date/Heure", "Utilisateur", "Code Erreur", "Type", "Message", "Endpoint", "Méthode", "IP"])
    for e in errors:
        writer.writerow([
            e.timestamp.strftime("%d/%m/%Y %H:%M:%S") if e.timestamp else "",
            e.user_email or "",
            e.error_code or "",
            e.error_type or "",
            e.error_message or "",
            e.endpoint or "",
            e.method or "",
            e.ip_address or "",
        ])

    output.seek(0)
    filename = f"errors_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ─── Statistiques ─────────────────────────────────────────────
@router.get("/stats")
def get_audit_stats(
    db: Session = Depends(get_db),
    _=Depends(require_admin)
):
    """Statistiques globales pour le tableau de bord audit."""
    from sqlalchemy import func

    total_logs = db.query(AuditLog).count()
    total_errors = db.query(ErrorLog).count()
    logins_today = db.query(AuditLog).filter(
        AuditLog.action == "login_success",
        func.date(AuditLog.timestamp) == date.today()
    ).count()
    failed_logins = db.query(AuditLog).filter(
        AuditLog.action == "login_failed"
    ).count()
    errors_500 = db.query(ErrorLog).filter(ErrorLog.error_code >= 500).count()

    # Actions les plus fréquentes
    top_actions = db.query(
        AuditLog.action, func.count(AuditLog.action).label("count")
    ).group_by(AuditLog.action).order_by(desc("count")).limit(5).all()

    return {
        "total_logs": total_logs,
        "total_errors": total_errors,
        "logins_today": logins_today,
        "failed_logins": failed_logins,
        "errors_500": errors_500,
        "top_actions": [{"action": a, "count": c} for a, c in top_actions],
    }
