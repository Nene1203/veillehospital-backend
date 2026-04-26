import uuid
from datetime import date, datetime
from sqlalchemy import (
    Column, String, Integer, Boolean, Date, Text,
    ForeignKey, DateTime, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database import Base


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
    utilisateurs = relationship("Utilisateur", back_populates="etablissement")


class Utilisateur(Base):
    __tablename__ = "utilisateurs"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nom              = Column(String(100), nullable=False)
    prenom           = Column(String(100), nullable=False)
    email            = Column(String(200), unique=True, nullable=False)
    mot_de_passe     = Column(String(200), nullable=False)
    role             = Column(String(20), default="responsable")
    etablissement_id = Column(UUID(as_uuid=True), ForeignKey("etablissements.id"))
    actif            = Column(Boolean, default=True)
    created_at       = Column(DateTime(timezone=True), default=datetime.utcnow)

    etablissement = relationship("Etablissement", back_populates="utilisateurs")
    veilles       = relationship("Veille", back_populates="responsable")


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
    # Anciens champs conservés pour compatibilité
    nb_lits_disponibles = Column(Integer, default=0)
    nb_lits_occupes     = Column(Integer, default=0)
    # Nouveaux champs EMS 2026
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
    """Table principale de saisie — conforme au formulaire Excel EMS 2026."""
    __tablename__ = "hospitalisations"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    veille_id       = Column(UUID(as_uuid=True), ForeignKey("veilles.id", ondelete="CASCADE"), nullable=False)

    # Information Résident
    date_hosp       = Column(Date)
    num_resident    = Column(String(50))
    age             = Column(Integer)
    genre           = Column(String(10))       # Femme / Homme
    classe_plaisir  = Column(Integer)          # 1–12

    # Dates / Heures
    jour_hosp       = Column(String(30))       # Lundi au Vendredi / Week-end / Jour Férié
    heure_hosp      = Column(String(20))       # Jour (8h-20h) / Nuit (20h-8h)

    # Hospitalisation
    type_hosp       = Column(String(20))       # Planifiée / Urgence
    demandeur       = Column(String(60))       # Médecin Responsable, Traitant…
    lieu_hosp       = Column(String(20))       # Somatique / Psychiatrie / Les Deux
    duree_hosp      = Column(String(10))       # <24H ou nombre de jours

    # Motif
    motif           = Column(String(100))

    # Post-hospitalisation
    issue           = Column(String(50))       # Retour EMS / Décès / Transfert…

    # Remarques
    remarques       = Column(Text)

    created_at      = Column(DateTime(timezone=True), default=datetime.utcnow)

    veille = relationship("Veille", back_populates="hospitalisations")
