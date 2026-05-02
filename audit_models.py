import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from database import Base


class AuditLog(Base):
    """Table d'audit — enregistre toutes les actions métier."""
    __tablename__ = "audit_logs"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp    = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)

    # Qui
    user_id      = Column(UUID(as_uuid=True), nullable=True)
    user_email   = Column(String(200), nullable=True)
    user_role    = Column(String(20), nullable=True)

    # Quoi
    action       = Column(String(100), nullable=False, index=True)
    resource     = Column(String(50), nullable=True)   # user, veille, campagne...
    resource_id  = Column(String(100), nullable=True)

    # Détails avant/après
    details      = Column(JSONB, nullable=True)        # {"avant": {...}, "apres": {...}}

    # Contexte technique
    ip_address   = Column(String(50), nullable=True)
    user_agent   = Column(String(500), nullable=True)
    endpoint     = Column(String(200), nullable=True)
    method       = Column(String(10), nullable=True)
    statut       = Column(String(20), default="success")  # success / error


class ErrorLog(Base):
    """Table des erreurs — répertorie toutes les erreurs de la plateforme."""
    __tablename__ = "error_logs"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp     = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)

    # Qui
    user_id       = Column(UUID(as_uuid=True), nullable=True)
    user_email    = Column(String(200), nullable=True)

    # Erreur
    error_code    = Column(Integer, nullable=False, index=True)  # 401, 403, 404, 500...
    error_type    = Column(String(100), nullable=True)           # access_denied, not_found...
    error_message = Column(Text, nullable=True)

    # Contexte
    endpoint      = Column(String(200), nullable=True)
    method        = Column(String(10), nullable=True)
    ip_address    = Column(String(50), nullable=True)
    user_agent    = Column(String(500), nullable=True)
    details       = Column(JSONB, nullable=True)                 # Stack trace, params...
