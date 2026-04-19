from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from typing import Optional
from database import get_db
import models, schemas

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def build_patient_query(db, campagne_id=None, etablissement_id=None, annee=None, mois=None, semaine=None, jour=None):
    q = (
        db.query(models.Patient)
        .join(models.Veille, models.Patient.veille_id == models.Veille.id)
    )
    if campagne_id:
        q = q.filter(models.Veille.campagne_id == campagne_id)
    if etablissement_id:
        q = q.filter(models.Veille.etablissement_id == etablissement_id)
    if annee:
        q = q.filter(extract('year', models.Patient.date_entree) == int(annee))
    if mois:
        q = q.filter(extract('month', models.Patient.date_entree) == int(mois))
    if semaine:
        q = q.filter(extract('week', models.Patient.date_entree) == int(semaine))
    if jour:
        q = q.filter(models.Patient.date_entree == jour)
    return q


def build_veille_query(db, campagne_id=None, etablissement_id=None, annee=None, mois=None, semaine=None):
    q = (
        db.query(models.Veille)
        .join(models.Campagne, models.Veille.campagne_id == models.Campagne.id)
    )
    if campagne_id:
        q = q.filter(models.Veille.campagne_id == campagne_id)
    if etablissement_id:
        q = q.filter(models.Veille.etablissement_id == etablissement_id)
    if annee:
        q = q.filter(extract('year', models.Campagne.date_debut) == int(annee))
    if mois:
        q = q.filter(extract('month', models.Campagne.date_debut) == int(mois))
    if semaine:
        q = q.filter(extract('week', models.Campagne.date_debut) == int(semaine))
    return q


# ─── Filtre en cascade : années disponibles ──────────────────
@router.get("/filtres/annees")
def get_annees(etablissement_id: Optional[str] = Query(None), db: Session = Depends(get_db)):
    q = db.query(
        extract('year', models.Patient.date_entree).label('annee')
    ).join(models.Veille)
    if etablissement_id:
        q = q.filter(models.Veille.etablissement_id == etablissement_id)
    annees = sorted(set(int(r.annee) for r in q.filter(models.Patient.date_entree.isnot(None)).distinct().all()), reverse=True)
    return annees


# ─── Mois disponibles pour une année ─────────────────────────
@router.get("/filtres/mois")
def get_mois(annee: int = Query(...), etablissement_id: Optional[str] = Query(None), db: Session = Depends(get_db)):
    q = db.query(
        extract('month', models.Patient.date_entree).label('mois')
    ).join(models.Veille).filter(
        models.Patient.date_entree.isnot(None),
        extract('year', models.Patient.date_entree) == annee
    )
    if etablissement_id:
        q = q.filter(models.Veille.etablissement_id == etablissement_id)
    mois = sorted(set(int(r.mois) for r in q.distinct().all()))
    NOMS_MOIS = {1:'Janvier',2:'Février',3:'Mars',4:'Avril',5:'Mai',6:'Juin',
                 7:'Juillet',8:'Août',9:'Septembre',10:'Octobre',11:'Novembre',12:'Décembre'}
    return [{"numero": m, "nom": NOMS_MOIS[m]} for m in mois]


# ─── Semaines disponibles pour année+mois ────────────────────
@router.get("/filtres/semaines")
def get_semaines(annee: int = Query(...), mois: Optional[int] = Query(None), etablissement_id: Optional[str] = Query(None), db: Session = Depends(get_db)):
    q = db.query(
        extract('week', models.Patient.date_entree).label('semaine'),
        func.min(models.Patient.date_entree).label('debut')
    ).join(models.Veille).filter(
        models.Patient.date_entree.isnot(None),
        extract('year', models.Patient.date_entree) == annee
    )
    if mois:
        q = q.filter(extract('month', models.Patient.date_entree) == mois)
    if etablissement_id:
        q = q.filter(models.Veille.etablissement_id == etablissement_id)
    rows = q.group_by(extract('week', models.Patient.date_entree)).order_by('semaine').all()
    return [{"numero": int(r.semaine), "debut": str(r.debut)} for r in rows]


# ─── Jours disponibles pour année+mois+semaine ───────────────
@router.get("/filtres/jours")
def get_jours(annee: int = Query(...), mois: Optional[int] = Query(None), semaine: Optional[int] = Query(None), etablissement_id: Optional[str] = Query(None), db: Session = Depends(get_db)):
    q = db.query(
        models.Patient.date_entree
    ).join(models.Veille).filter(
        models.Patient.date_entree.isnot(None),
        extract('year', models.Patient.date_entree) == annee
    )
    if mois:
        q = q.filter(extract('month', models.Patient.date_entree) == mois)
    if semaine:
        q = q.filter(extract('week', models.Patient.date_entree) == semaine)
    if etablissement_id:
        q = q.filter(models.Veille.etablissement_id == etablissement_id)
    jours = sorted(set(str(r.date_entree) for r in q.distinct().all()))
    return jours


# ─── KPIs ────────────────────────────────────────────────────
@router.get("/kpis")
def get_kpis(
    campagne_id: Optional[str] = Query(None),
    etablissement_id: Optional[str] = Query(None),
    annee: Optional[int] = Query(None),
    mois: Optional[int] = Query(None),
    semaine: Optional[int] = Query(None),
    jour: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    patients = build_patient_query(db, campagne_id, etablissement_id, annee, mois, semaine, jour).all()
    durees = [p.duree_sejour for p in patients if p.duree_sejour is not None]
    attentes = [p.attente_avant_op_jours for p in patients if p.attente_avant_op_jours is not None]

    veilles = build_veille_query(db, campagne_id, etablissement_id, annee, mois, semaine).all()
    taux_list = [v.nb_lits_occupes / v.nb_lits_disponibles * 100 for v in veilles if v.nb_lits_disponibles and v.nb_lits_disponibles > 0]

    return {
        "total_hospitalisations": len(patients),
        "duree_moyenne_sejour": round(sum(durees)/len(durees), 1) if durees else None,
        "attente_moyenne_avant_op": round(sum(attentes)/len(attentes), 1) if attentes else None,
        "taux_remplissage_moyen": round(sum(taux_list)/len(taux_list), 1) if taux_list else None,
        "total_sortis": sum(1 for p in patients if p.statut == "Sorti"),
        "total_transferts": sum(1 for p in patients if p.statut == "Transféré"),
        "total_rehospitalisations": sum(1 for p in patients if p.rehospitalisation),
        "total_presents": sum(1 for p in patients if p.statut == "Hospitalisé"),
    }


# ─── Par établissement ───────────────────────────────────────
@router.get("/par-etablissement")
def get_par_etablissement(
    campagne_id: Optional[str] = Query(None),
    etablissement_id: Optional[str] = Query(None),
    annee: Optional[int] = Query(None),
    mois: Optional[int] = Query(None),
    semaine: Optional[int] = Query(None),
    jour: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    etabs = db.query(models.Etablissement).filter(models.Etablissement.actif == True).all()
    result = []
    for etab in etabs:
        if etablissement_id and str(etab.id) != etablissement_id:
            continue
        patients = build_patient_query(db, campagne_id, str(etab.id), annee, mois, semaine, jour).all()
        durees = [p.duree_sejour for p in patients if p.duree_sejour is not None]
        attentes = [p.attente_avant_op_jours for p in patients if p.attente_avant_op_jours is not None]
        veilles = build_veille_query(db, campagne_id, str(etab.id), annee, mois, semaine).all()
        taux_list = [v.nb_lits_occupes / v.nb_lits_disponibles * 100 for v in veilles if v.nb_lits_disponibles and v.nb_lits_disponibles > 0]

        result.append({
            "etablissement_id": str(etab.id),
            "etablissement_nom": etab.nom,
            "hospitalisations": len(patients),
            "duree_moyenne": round(sum(durees)/len(durees), 1) if durees else None,
            "attente_moyenne": round(sum(attentes)/len(attentes), 1) if attentes else None,
            "taux_remplissage": round(sum(taux_list)/len(taux_list), 1) if taux_list else None,
            "sortis": sum(1 for p in patients if p.statut == "Sorti"),
            "transferts": sum(1 for p in patients if p.statut == "Transféré"),
            "rehospitalisations": sum(1 for p in patients if p.rehospitalisation),
            "statut_veille": "Données disponibles" if patients else "Aucune donnée",
        })
    return result


# ─── Par pathologie ──────────────────────────────────────────
@router.get("/par-pathologie")
def get_par_pathologie(
    campagne_id: Optional[str] = Query(None),
    etablissement_id: Optional[str] = Query(None),
    annee: Optional[int] = Query(None),
    mois: Optional[int] = Query(None),
    semaine: Optional[int] = Query(None),
    jour: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    patients = build_patient_query(db, campagne_id, etablissement_id, annee, mois, semaine, jour).filter(
        models.Patient.pathologie.isnot(None)
    ).all()
    total = len(patients)
    if total == 0:
        return []
    counts = {}
    for p in patients:
        counts[p.pathologie] = counts.get(p.pathologie, 0) + 1
    return [
        {"pathologie": k, "count": v, "pourcentage": round(v/total*100, 1)}
        for k, v in sorted(counts.items(), key=lambda x: -x[1])
    ]


# ─── Évolution temporelle pour graphique ligne ───────────────
@router.get("/evolution")
def get_evolution(
    campagne_id: Optional[str] = Query(None),
    etablissement_id: Optional[str] = Query(None),
    annee: Optional[int] = Query(None),
    mois: Optional[int] = Query(None),
    semaine: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    q = build_patient_query(db, campagne_id, etablissement_id, annee, mois, semaine).filter(
        models.Patient.date_entree.isnot(None)
    )

    if semaine and annee:
        # Par jour
        rows = q.with_entities(
            models.Patient.date_entree,
            func.count().label('n')
        ).group_by(models.Patient.date_entree).order_by(models.Patient.date_entree).all()
        JOURS = ['Lun','Mar','Mer','Jeu','Ven','Sam','Dim']
        return [{"label": JOURS[r.date_entree.weekday()], "value": r.n, "date": str(r.date_entree)} for r in rows]
    elif mois and annee:
        # Par semaine du mois
        rows = q.with_entities(
            extract('week', models.Patient.date_entree).label('s'),
            func.count().label('n')
        ).group_by('s').order_by('s').all()
        return [{"label": f"S{int(r.s)}", "value": r.n} for r in rows]
    elif annee:
        # Par mois
        NOMS = {1:'Jan',2:'Fév',3:'Mar',4:'Avr',5:'Mai',6:'Jun',7:'Jul',8:'Aoû',9:'Sep',10:'Oct',11:'Nov',12:'Déc'}
        rows = q.with_entities(
            extract('month', models.Patient.date_entree).label('m'),
            func.count().label('n')
        ).group_by('m').order_by('m').all()
        return [{"label": NOMS[int(r.m)], "value": r.n} for r in rows]
    else:
        # Par année
        rows = q.with_entities(
            extract('year', models.Patient.date_entree).label('y'),
            func.count().label('n')
        ).group_by('y').order_by('y').all()
        return [{"label": str(int(r.y)), "value": r.n} for r in rows]
