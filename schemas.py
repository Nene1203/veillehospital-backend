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


# ─── Campagne ─────────────────────────────────────────────────
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


# ─── Patient ──────────────────────────────────────────────────
class PatientBase(BaseModel):
    nom: Optional[str] = None
    prenom: Optional[str] = None
    age: Optional[int] = Field(None, ge=0, le=130)
    chambre: Optional[str] = None
    pathologie: Optional[str] = None
    operation_subie: Optional[str] = None
    date_entree: Optional[date] = None
    date_sortie: Optional[date] = None
    attente_avant_op_jours: int = 0
    temps_apres_op_jours: int = 0
    mode_entree: str = "Urgences"
    statut: str = "Hospitalisé"
    destination_sortie: Optional[str] = None
    rehospitalisation: bool = False

class PatientCreate(PatientBase):
    pass

class PatientOut(PatientBase):
    id: UUID
    veille_id: UUID
    duree_sejour: Optional[int] = None
    created_at: datetime
    model_config = {"from_attributes": True}


# ─── Veille ───────────────────────────────────────────────────
class VeilleBase(BaseModel):
    campagne_id: UUID
    etablissement_id: UUID
    nb_lits_disponibles: int = 0
    nb_lits_occupes: int = 0
    commentaires: Optional[str] = None

class VeilleCreate(VeilleBase):
    patients: List[PatientCreate] = []

class VeilleUpdate(BaseModel):
    statut: Optional[str] = None
    nb_lits_disponibles: Optional[int] = None
    nb_lits_occupes: Optional[int] = None
    commentaires: Optional[str] = None
    patients: Optional[List[PatientCreate]] = None

class VeilleOut(VeilleBase):
    id: UUID
    statut: str
    date_saisie: date
    responsable_id: Optional[UUID]
    patients: List[PatientOut] = []
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


# ─── Dashboard ────────────────────────────────────────────────
class KpiOut(BaseModel):
    total_hospitalisations: int
    duree_moyenne_sejour: Optional[float]
    attente_moyenne_avant_op: Optional[float]
    taux_remplissage_moyen: Optional[float]
    total_sortis: int
    total_transferts: int
    total_rehospitalisations: int
    total_presents: int

class EtabStatsOut(BaseModel):
    etablissement_id: UUID
    etablissement_nom: str
    hospitalisations: int
    duree_moyenne: Optional[float]
    attente_moyenne: Optional[float]
    taux_remplissage: Optional[float]
    sortis: int
    transferts: int
    rehospitalisations: int
    statut_veille: str

class PathoStatOut(BaseModel):
    pathologie: str
    count: int
    pourcentage: float

class DashboardOut(BaseModel):
    kpis: KpiOut
    par_etablissement: List[EtabStatsOut]
    par_pathologie: List[PathoStatOut]
