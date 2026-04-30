from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from auth import get_current_user, require_admin, get_etablissement_ids_for_user
import models, schemas

router = APIRouter(prefix="/etablissements", tags=["Établissements"])


@router.get("/", response_model=List[schemas.EtablissementOut])
def list_etablissements(
    db: Session = Depends(get_db),
    current_user: models.Utilisateur = Depends(get_current_user)
):
    etab_ids = get_etablissement_ids_for_user(current_user)
    q = db.query(models.Etablissement).filter(models.Etablissement.actif == True)

    # dir-eta et contrib : seulement leurs établissements
    if etab_ids is not None:
        q = q.filter(models.Etablissement.id.in_(etab_ids))

    return q.all()


@router.post("/", response_model=schemas.EtablissementOut, status_code=201)
def create_etablissement(
    data: schemas.EtablissementCreate,
    db: Session = Depends(get_db),
    current_user: models.Utilisateur = Depends(require_admin)
):
    etab = models.Etablissement(**data.model_dump())
    db.add(etab)
    db.commit()
    db.refresh(etab)
    return etab


@router.get("/{etab_id}", response_model=schemas.EtablissementOut)
def get_etablissement(
    etab_id: str,
    db: Session = Depends(get_db),
    current_user: models.Utilisateur = Depends(get_current_user)
):
    etab_ids = get_etablissement_ids_for_user(current_user)

    etab = db.query(models.Etablissement).filter(models.Etablissement.id == etab_id).first()
    if not etab:
        raise HTTPException(status_code=404, detail="Établissement introuvable")

    # Vérifier l'accès pour dir-eta et contrib
    if etab_ids is not None and etab_id not in etab_ids:
        raise HTTPException(status_code=403, detail="Accès non autorisé à cet établissement")

    return etab
