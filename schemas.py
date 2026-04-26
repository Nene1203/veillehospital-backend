from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import date, datetime
from uuid import UUID


# ─── Établissement ───────────────────────────────────────────
class EtablissementBase(BaseModel):
    nom: str
    adresse: Optional[str] = None
    telephone: Optional[str] = None
    nb_lits: int = 0

class EtablissementCreate(EtablissementBase):
    pass

class EtablissementOut(EtablissementBase):
    id: UUID
    actif: bool
    created_at: datetime
    model_config = {"from_attributes": True}


# ─── Campagne ────────────────────────────────────────────────
class CampagneBase(BaseModel):
    titre: str
    type: str = "hebdomadaire"
    date_debut: date
    date_fin: date

class CampagneCreate(CampagneBase):
    pass

class CampagneOut(CampagneBase):
    id: UUID
    statut: str
    created_at: datetime
    model_config = {"from_attributes": True}


# ─── Hospitalisation ─────────────────────────────────────────
class HospitalisationBase(BaseModel):
    date_hosp:      Optional[date]  = None
    num_resident:   Optional[str]   = None
    age:            Optional[int]   = Field(None, ge=55, le=115)
    genre:          Optional[str]   = None   # Femme / Homme
    classe_plaisir: Optional[int]   = Field(None, ge=1, le=12)
    jour_hosp:      Optional[str]   = None   # Lundi au Vendredi / Week-end / Jour Férié
    heure_hosp:     Optional[str]   = None   # Jour (8h-20h) / Nuit (20h-8h)
    type_hosp:      Optional[str]   = None   # Planifiée / Urgence
    demandeur:      Optional[str]   = None
    lieu_hosp:      Optional[str]   = None   # Somatique / Psychiatrie / Les Deux
    duree_hosp:     Optional[str]   = None   # <24H ou 1–50
    motif:          Optional[str]   = None
    issue:          Optional[str]   = None
    remarques:      Optional[str]   = None

class HospitalisationCreate(HospitalisationBase):
    pass

class HospitalisationOut(HospitalisationBase):
    id: UUID
    veille_id: UUID
    created_at: datetime
    model_config = {"from_attributes": True}


# ─── Veille ──────────────────────────────────────────────────
class VeilleBase(BaseModel):
    campagne_id:      UUID
    etablissement_id: UUID
    nb_lits:          int = 0
    nb_deces:         int = 0
    reseau_sante:     Optional[str] = None
    commentaires:     Optional[str] = None

class VeilleCreate(VeilleBase):
    hospitalisations: List[HospitalisationCreate] = []

class VeilleUpdate(BaseModel):
    statut:           Optional[str] = None
    nb_lits:          Optional[int] = None
    nb_deces:         Optional[int] = None
    reseau_sante:     Optional[str] = None
    commentaires:     Optional[str] = None
    hospitalisations: Optional[List[HospitalisationCreate]] = None

class VeilleOut(VeilleBase):
    id:              UUID
    statut:          str
    date_saisie:     date
    responsable_id:  Optional[UUID] = None
    hospitalisations: List[HospitalisationOut] = []
    created_at:      datetime
    updated_at:      datetime
    model_config = {"from_attributes": True}


# ─── Dashboard ───────────────────────────────────────────────
class KpiOut(BaseModel):
    total_hospitalisations:  int
    repartition_urgences:    Optional[float] = None  # % urgences
    repartition_planifiees:  Optional[float] = None  # % planifiées
    duree_moyenne_sejour:    Optional[float] = None  # durée moyenne en jours
    taux_nuit:               Optional[float] = None  # % hospitalisations de nuit
    taux_weekend:            Optional[float] = None  # % week-end + jours fériés
    top_motif:               Optional[str]   = None
    taux_retour_ems:         Optional[float] = None
    taux_deces:              Optional[float] = None

class EtabStatsOut(BaseModel):
    etablissement_id:   UUID
    etablissement_nom:  str
    hospitalisations:   int
    urgences:           int = 0
    planifiees:         int = 0
    duree_moyenne:      Optional[float] = None
    taux_nuit:          Optional[float] = None
    retour_ems:         int = 0
    deces:              int = 0
    transferts:         int = 0
    nb_lits:            Optional[int]   = None
    nb_deces:           Optional[int]   = None
    statut_veille:      str

class PathoStatOut(BaseModel):
    pathologie:   str
    count:        int
    pourcentage:  float

class DashboardOut(BaseModel):
    kpis:              KpiOut
    par_etablissement: List[EtabStatsOut]
    par_pathologie:    List[PathoStatOut]
