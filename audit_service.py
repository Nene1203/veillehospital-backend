"""
Service d'audit — fonctions utilitaires pour logger les événements.
"""
from datetime import datetime
from typing import Optional, Any, Dict
from sqlalchemy.orm import Session
from audit_models import AuditLog, ErrorLog


# ─── Actions disponibles ──────────────────────────────────────
class AuditAction:
    # Auth
    LOGIN_SUCCESS      = "login_success"
    LOGIN_FAILED       = "login_failed"
    LOGOUT             = "logout"
    TOKEN_EXPIRED      = "token_expired"

    # Utilisateurs
    USER_CREATED       = "user_created"
    USER_UPDATED       = "user_updated"
    USER_DEACTIVATED   = "user_deactivated"
    USER_REACTIVATED   = "user_reactivated"

    # Veilles
    VEILLE_CREATED     = "veille_created"
    VEILLE_UPDATED     = "veille_updated"
    VEILLE_SUBMITTED   = "veille_submitted"
    VEILLE_DELETED     = "veille_deleted"

    # Campagnes
    CAMPAGNE_CREATED   = "campagne_created"
    CAMPAGNE_CLOSED    = "campagne_closed"

    # Établissements
    ETAB_CREATED       = "etablissement_created"

    # Accès
    ACCESS_DENIED      = "access_denied"
    UNAUTHORIZED       = "unauthorized_access"

    # Exports
    EXPORT_CSV         = "export_csv"
    EXPORT_PDF         = "export_pdf"


def log_action(
    db: Session,
    action: str,
    user_id: Optional[str] = None,
    user_email: Optional[str] = None,
    user_role: Optional[str] = None,
    resource: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    endpoint: Optional[str] = None,
    method: Optional[str] = None,
    statut: str = "success",
):
    """Enregistre une action dans audit_logs."""
    try:
        log = AuditLog(
            user_id=user_id,
            user_email=user_email,
            user_role=user_role,
            action=action,
            resource=resource,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
            endpoint=endpoint,
            method=method,
            statut=statut,
        )
        db.add(log)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[AUDIT ERROR] Failed to log action {action}: {e}")


def log_error(
    db: Session,
    error_code: int,
    error_type: Optional[str] = None,
    error_message: Optional[str] = None,
    user_id: Optional[str] = None,
    user_email: Optional[str] = None,
    endpoint: Optional[str] = None,
    method: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
):
    """Enregistre une erreur dans error_logs."""
    try:
        log = ErrorLog(
            error_code=error_code,
            error_type=error_type,
            error_message=error_message,
            user_id=user_id,
            user_email=user_email,
            endpoint=endpoint,
            method=method,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details,
        )
        db.add(log)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[AUDIT ERROR] Failed to log error {error_code}: {e}")


def get_client_ip(request) -> str:
    """Récupère l'IP réelle du client."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
