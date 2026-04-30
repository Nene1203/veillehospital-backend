from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from auth import get_current_user, require_can_saisir, get_etablissement_ids_for_user
import models, schemas

router = APIRouter(prefix="/veilles", tags=["Veilles"])


@router.get("/", response_model=List[schemas.VeilleOut])
def list_veilles(
    campagne_id: str = None,
    etablissement_id: str = None,
    db: Session = Depends(get_db),
    current_user: models.Utilisateur = Depends(get_current_user)
):
    etab_ids = get_etablissement_ids_for_user(current_user)
    q = db.query(models.Veille)

    if campagne_id:
        q = q.filter(models.Veille.campagne_id == campagne_id)

    # Filtre établissement demandé par le client
    if etablissement_id:
        # Vérifier que l'utilisateur a accès à cet établissement
        if etab_ids is not None and etablissement_id not in etab_ids:
            raise HTTPException(status_code=403, detail="Accès non autorisé à cet établissement")
        q = q.filter(models.Veille.etablissement_id == etablissement_id)
    elif etab_ids is not None:
        # Filtrer automatiquement selon les établissements du user
        q = q.filter(models.Veille.etablissement_id.in_(etab_ids))

    return q.order_by(models.Veille.created_at.desc()).all()


@router.post("/", response_model=schemas.VeilleOut, status_code=201)
def create_veille(
    data: schemas.VeilleCreate,
    db: Session = Depends(get_db),
    current_user: models.Utilisateur = Depends(require_can_saisir)
):
    # Vérifier l'accès à l'établissement pour contrib
    etab_ids = get_etablissement_ids_for_user(current_user)
    if etab_ids is not None and str(data.etablissement_id) not in etab_ids:
        raise HTTPException(status_code=403, detail="Accès non autorisé à cet établissement")

    existing = db.query(models.Veille).filter(
        models.Veille.campagne_id == data.campagne_id,
        models.Veille.etablissement_id == data.etablissement_id
    ).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail="Une veille existe déjà pour cet établissement dans cette campagne"
        )

    hosps_data = data.hospitalisations
    veille_data = data.model_dump(exclude={"hospitalisations"})
    veille = models.Veille(**veille_data, responsable_id=current_user.id)
    db.add(veille)
    db.flush()

    for h in hosps_data:
        hosp = models.Hospitalisation(**h.model_dump(), veille_id=veille.id)
        db.add(hosp)

    db.commit()
    db.refresh(veille)
    return veille


@router.get("/{veille_id}", response_model=schemas.VeilleOut)
def get_veille(
    veille_id: str,
    db: Session = Depends(get_db),
    current_user: models.Utilisateur = Depends(get_current_user)
):
    v = db.query(models.Veille).filter(models.Veille.id == veille_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Veille introuvable")

    etab_ids = get_etablissement_ids_for_user(current_user)
    if etab_ids is not None and str(v.etablissement_id) not in etab_ids:
        raise HTTPException(status_code=403, detail="Accès non autorisé")

    return v


@router.put("/{veille_id}", response_model=schemas.VeilleOut)
def update_veille(
    veille_id: str,
    data: schemas.VeilleUpdate,
    db: Session = Depends(get_db),
    current_user: models.Utilisateur = Depends(require_can_saisir)
):
    v = db.query(models.Veille).filter(models.Veille.id == veille_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Veille introuvable")

    etab_ids = get_etablissement_ids_for_user(current_user)
    if etab_ids is not None and str(v.etablissement_id) not in etab_ids:
        raise HTTPException(status_code=403, detail="Accès non autorisé")

    update_fields = data.model_dump(exclude={"hospitalisations"}, exclude_none=True)
    for field, value in update_fields.items():
        setattr(v, field, value)

    if data.hospitalisations is not None:
        for h in v.hospitalisations:
            db.delete(h)
        db.flush()
        for h in data.hospitalisations:
            hosp = models.Hospitalisation(**h.model_dump(), veille_id=v.id)
            db.add(hosp)

    db.commit()
    db.refresh(v)
    return v


@router.patch("/{veille_id}/soumettre")
def soumettre_veille(
    veille_id: str,
    db: Session = Depends(get_db),
    current_user: models.Utilisateur = Depends(require_can_saisir)
):
    v = db.query(models.Veille).filter(models.Veille.id == veille_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Veille introuvable")

    etab_ids = get_etablissement_ids_for_user(current_user)
    if etab_ids is not None and str(v.etablissement_id) not in etab_ids:
        raise HTTPException(status_code=403, detail="Accès non autorisé")

    v.statut = "soumis"
    db.commit()
    return {"message": "Veille soumise avec succès"}


@router.delete("/{veille_id}", status_code=204)
def delete_veille(
    veille_id: str,
    db: Session = Depends(get_db),
    current_user: models.Utilisateur = Depends(require_can_saisir)
):
    v = db.query(models.Veille).filter(models.Veille.id == veille_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Veille introuvable")

    etab_ids = get_etablissement_ids_for_user(current_user)
    if etab_ids is not None and str(v.etablissement_id) not in etab_ids:
        raise HTTPException(status_code=403, detail="Accès non autorisé")

    db.delete(v)
    db.commit()
