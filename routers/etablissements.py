from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
import models, schemas

router = APIRouter(prefix="/etablissements", tags=["Établissements"])

@router.get("/", response_model=List[schemas.EtablissementOut])
def list_etablissements(db: Session = Depends(get_db)):
    return db.query(models.Etablissement).filter(models.Etablissement.actif == True).all()

@router.post("/", response_model=schemas.EtablissementOut, status_code=201)
def create_etablissement(data: schemas.EtablissementCreate, db: Session = Depends(get_db)):
    etab = models.Etablissement(**data.model_dump())
    db.add(etab)
    db.commit()
    db.refresh(etab)
    return etab

@router.get("/{etab_id}", response_model=schemas.EtablissementOut)
def get_etablissement(etab_id: str, db: Session = Depends(get_db)):
    etab = db.query(models.Etablissement).filter(models.Etablissement.id == etab_id).first()
    if not etab:
        raise HTTPException(status_code=404, detail="Établissement introuvable")
    return etab
