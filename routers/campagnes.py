from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from auth import get_current_user, require_can_saisir, get_etablissement_ids_for_user
import models, schemas

router = APIRouter(prefix="/campagnes", tags=["Campagnes"])


@router.get("/", response_model=List[schemas.CampagneOut])
def list_campagnes(
    db: Session = Depends(get_db),
    current_user: models.Utilisateur = Depends(get_current_user)
):
    return db.query(models.Campagne).order_by(models.Campagne.date_debut.desc()).all()


@router.post("/", response_model=schemas.CampagneOut, status_code=201)
def create_campagne(
    data: schemas.CampagneCreate,
    db: Session = Depends(get_db),
    current_user: models.Utilisateur = Depends(require_can_saisir)
):
    campagne = models.Campagne(**data.model_dump(), created_by=current_user.id)
    db.add(campagne)
    db.commit()
    db.refresh(campagne)
    return campagne


@router.get("/{campagne_id}", response_model=schemas.CampagneOut)
def get_campagne(
    campagne_id: str,
    db: Session = Depends(get_db),
    current_user: models.Utilisateur = Depends(get_current_user)
):
    c = db.query(models.Campagne).filter(models.Campagne.id == campagne_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Campagne introuvable")
    return c


@router.patch("/{campagne_id}/cloturer")
def cloturer_campagne(
    campagne_id: str,
    db: Session = Depends(get_db),
    current_user: models.Utilisateur = Depends(require_can_saisir)
):
    c = db.query(models.Campagne).filter(models.Campagne.id == campagne_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Campagne introuvable")
    c.statut = "cloturee"
    db.commit()
    return {"message": "Campagne clôturée"}
