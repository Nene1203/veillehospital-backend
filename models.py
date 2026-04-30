import uuid
from datetime import date, datetime
from sqlalchemy import (
    Column, String, Integer, Boolean, Date, Text,
    ForeignKey, DateTime, UniqueConstraint, Table
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database import Base


# ─── Table de liaison Utilisateur <-> Etablissement ──────────
utilisateur_etablissement = Table(
    "utilisateur_etablissement",
    Base.metadata,
    Column("utilisateur_id", UUID(as_uuid=True), ForeignKey("utilisateurs.id", ondelete="CASCADE"), primary_key=True),
    Column("etablissement_id", UUID(as_uuid=True), ForeignKey("etablissements.id", ondelete="CASCADE"), primary_key=True),
)

# Rôles valides
ROLES_VALIDES = ["admin", "dir-hev", "dir-eta", "contrib"]


class Etablissement(Base):
    __tablename__ = "etablissements"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nom        = Column(String(200), nullable=False)
    adresse    = Column(Text)
    telephone  = Column(String(20))
    nb_lits    = Column(Integer, default=0)
    actif      = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    veilles      = relationship("Veille", back_populates="etablissement")
    utilisateurs = relationship("Utilisateur", secondary=utilisateur_etablissement, back_populates="etablissements")


class Utilisateur(Base):
    __tablename__ = "utilisateurs"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nom              = Column(String(100), nullable=False)
    prenom           = Column(String(100), nullable=False)
    email            = Column(String(200), unique=True, nullable=False)
    mot_de_passe     = Column(String(200), nullable=False)
    role             = Column(String(20), default="contrib")
    # Conservé pour compatibilité avec l'ancien code
    etablissement_id = Column(UUID(as_uuid=True), ForeignKey("etablissements.id"), nullable=True)
    actif            = Column(Boolean, default=True)
    created_at       = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Nouvelle relation many-to-many
    etablissements = relationship("Etablissement", secondary=utilisateur_etablissement, back_populates="utilisateurs")
    veilles        = relationship("Veille", back_populates="responsable")


class Campagne(Base):
    __tablename__ = "campagnes"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    titre      = Column(String(200), nullable=False)
    type       = Column(String(20), default="hebdomadaire")
    date_debut = Column(Date, nullable=False)
    date_fin   = Column(Date, nullable=False)
    statut     = Column(String(20), default="ouverte")
    created_by = Column(UUID(as_uuid=True), ForeignKey("utilisateurs.id"))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    veilles = relationship("Veille", back_populates="campagne")


class Veille(Base):
    __tablename__ = "veilles"
    __table_args__ = (UniqueConstraint("campagne_id", "etablissement_id"),)

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campagne_id      = Column(UUID(as_uuid=True), ForeignKey("campagnes.id", ondelete="CASCADE"), nullable=False)
    etablissement_id = Column(UUID(as_uuid=True), ForeignKey("etablissements.id", ondelete="CASCADE"), nullable=False)
    responsable_id   = Column(UUID(as_uuid=True), ForeignKey("utilisateurs.id"))
    statut           = Column(String(20), default="brouillon")
    date_saisie      = Column(Date, default=date.today)
    nb_lits_disponibles = Column(Integer, default=0)
    nb_lits_occupes     = Column(Integer, default=0)
    nb_lits      = Column(Integer, default=0)
    nb_deces     = Column(Integer, default=0)
    reseau_sante = Column(String(100))
    commentaires = Column(Text)
    created_at   = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at   = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    campagne          = relationship("Campagne", back_populates="veilles")
    etablissement     = relationship("Etablissement", back_populates="veilles")
    responsable       = relationship("Utilisateur", back_populates="veilles")
    hospitalisations  = relationship("Hospitalisation", back_populates="veille", cascade="all, delete-orphan")


class Hospitalisation(Base):
    __tablename__ = "hospitalisations"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    veille_id       = Column(UUID(as_uuid=True), ForeignKey("veilles.id", ondelete="CASCADE"), nullable=False)

    date_hosp       = Column(Date)
    num_resident    = Column(String(50))
    age             = Column(Integer)
    genre           = Column(String(10))
    classe_plaisir  = Column(Integer)

    jour_hosp       = Column(String(30))
    heure_hosp      = Column(String(20))

    type_hosp       = Column(String(20))
    demandeur       = Column(String(60))
    lieu_hosp       = Column(String(20))
    duree_hosp      = Column(String(10))

    motif           = Column(String(100))
    issue           = Column(String(50))
    remarques       = Column(Text)

    created_at      = Column(DateTime(timezone=True), default=datetime.utcnow)

    veille = relationship("Veille", back_populates="hospitalisations")
