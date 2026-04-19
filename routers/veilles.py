from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from datetime import date
from database import get_db
import models, schemas

router = APIRouter(prefix="/veilles", tags=["Veilles"])


@router.get("/", response_model=List[schemas.VeilleOut])
def list_veilles(
    campagne_id: str = None,
    etablissement_id: str = None,
    db: Session = Depends(get_db)
):
    q = db.query(models.Veille)
    if campagne_id:
        q = q.filter(models.Veille.campagne_id == campagne_id)
    if etablissement_id:
        q = q.filter(models.Veille.etablissement_id == etablissement_id)
    return q.order_by(models.Veille.created_at.desc()).all()


@router.post("/", response_model=schemas.VeilleOut, status_code=201)
def create_veille(data: schemas.VeilleCreate, db: Session = Depends(get_db)):
    # Vérifie l'unicité campagne + établissement
    existing = db.query(models.Veille).filter(
        models.Veille.campagne_id == data.campagne_id,
        models.Veille.etablissement_id == data.etablissement_id
    ).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail="Une veille existe déjà pour cet établissement dans cette campagne"
        )

    # Crée la veille
    patients_data = data.patients
    veille_data = data.model_dump(exclude={"patients"})
    veille = models.Veille(**veille_data)
    db.add(veille)
    db.flush()  # récupère l'id avant commit

    # Crée les patients associés
    for p in patients_data:
        patient = models.Patient(**p.model_dump(), veille_id=veille.id)
        db.add(patient)

    db.commit()
    db.refresh(veille)
    return veille


@router.get("/{veille_id}", response_model=schemas.VeilleOut)
def get_veille(veille_id: str, db: Session = Depends(get_db)):
    v = db.query(models.Veille).filter(models.Veille.id == veille_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Veille introuvable")
    return v


@router.put("/{veille_id}", response_model=schemas.VeilleOut)
def update_veille(veille_id: str, data: schemas.VeilleUpdate, db: Session = Depends(get_db)):
    v = db.query(models.Veille).filter(models.Veille.id == veille_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Veille introuvable")

    # Met à jour les champs scalaires
    update_fields = data.model_dump(exclude={"patients"}, exclude_none=True)
    for field, value in update_fields.items():
        setattr(v, field, value)

    # Remplace les patients si fournis
    if data.patients is not None:
        for p in v.patients:
            db.delete(p)
        db.flush()
        for p in data.patients:
            patient = models.Patient(**p.model_dump(), veille_id=v.id)
            db.add(patient)

    db.commit()
    db.refresh(v)
    return v


@router.patch("/{veille_id}/soumettre")
def soumettre_veille(veille_id: str, db: Session = Depends(get_db)):
    v = db.query(models.Veille).filter(models.Veille.id == veille_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Veille introuvable")
    v.statut = "soumis"
    db.commit()
    return {"message": "Veille soumise avec succès"}


@router.delete("/{veille_id}", status_code=204)
def delete_veille(veille_id: str, db: Session = Depends(get_db)):
    v = db.query(models.Veille).filter(models.Veille.id == veille_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Veille introuvable")
    db.delete(v)
    db.commit()
