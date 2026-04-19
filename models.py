import uuid
from datetime import date, datetime
from sqlalchemy import (
    Column, String, Integer, Boolean, Date, Text,
    ForeignKey, DateTime, CheckConstraint, UniqueConstraint, Computed
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

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    titre       = Column(String(200), nullable=False)
    type        = Column(String(20), default="hebdomadaire")
    date_debut  = Column(Date, nullable=False)
    date_fin    = Column(Date, nullable=False)
    statut      = Column(String(20), default="ouverte")
    created_by  = Column(UUID(as_uuid=True), ForeignKey("utilisateurs.id"))
    created_at  = Column(DateTime(timezone=True), default=datetime.utcnow)

    veilles = relationship("Veille", back_populates="campagne")


class Veille(Base):
    __tablename__ = "veilles"
    __table_args__ = (UniqueConstraint("campagne_id", "etablissement_id"),)

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campagne_id         = Column(UUID(as_uuid=True), ForeignKey("campagnes.id", ondelete="CASCADE"), nullable=False)
    etablissement_id    = Column(UUID(as_uuid=True), ForeignKey("etablissements.id", ondelete="CASCADE"), nullable=False)
    responsable_id      = Column(UUID(as_uuid=True), ForeignKey("utilisateurs.id"))
    statut              = Column(String(20), default="brouillon")
    date_saisie         = Column(Date, default=date.today)
    nb_lits_disponibles = Column(Integer, default=0)
    nb_lits_occupes     = Column(Integer, default=0)
    commentaires        = Column(Text)
    created_at          = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at          = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    campagne      = relationship("Campagne", back_populates="veilles")
    etablissement = relationship("Etablissement", back_populates="veilles")
    responsable   = relationship("Utilisateur", back_populates="veilles")
    patients      = relationship("Patient", back_populates="veille", cascade="all, delete-orphan")


class Patient(Base):
    __tablename__ = "patients"

    id                      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    veille_id               = Column(UUID(as_uuid=True), ForeignKey("veilles.id", ondelete="CASCADE"), nullable=False)
    nom                     = Column(String(100))
    prenom                  = Column(String(100))
    age                     = Column(Integer)
    chambre                 = Column(String(20))
    pathologie              = Column(String(100))
    operation_subie         = Column(String(200))
    date_entree             = Column(Date)
    date_sortie             = Column(Date)
    attente_avant_op_jours  = Column(Integer, default=0)
    temps_apres_op_jours    = Column(Integer, default=0)
    mode_entree             = Column(String(50), default="Urgences")
    statut                  = Column(String(30), default="Hospitalisé")
    destination_sortie      = Column(String(50))
    rehospitalisation       = Column(Boolean, default=False)
    created_at              = Column(DateTime(timezone=True), default=datetime.utcnow)

    veille = relationship("Veille", back_populates="patients")

    @property
    def duree_sejour(self):
        if self.date_entree and self.date_sortie:
            return (self.date_sortie - self.date_entree).days
        return None
