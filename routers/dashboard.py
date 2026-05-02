from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from typing import Optional
from database import get_db
import models, schemas

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

NOMS_MOIS = {
    1:"Jan", 2:"Fév", 3:"Mar", 4:"Avr", 5:"Mai", 6:"Jun",
    7:"Jul", 8:"Aoû", 9:"Sep", 10:"Oct", 11:"Nov", 12:"Déc"
}


def build_hosp_query(db, campagne_id=None, etablissement_id=None,
                     annee=None, mois=None, semaine=None, jour=None):
    q = (
        db.query(models.Hospitalisation)
        .join(models.Veille, models.Hospitalisation.veille_id == models.Veille.id)
    )
    if campagne_id:
        q = q.filter(models.Veille.campagne_id == campagne_id)
    if etablissement_id:
        q = q.filter(models.Veille.etablissement_id == etablissement_id)
    if annee:
        q = q.filter(extract('year', models.Hospitalisation.date_hosp) == int(annee))
    if mois:
        q = q.filter(extract('month', models.Hospitalisation.date_hosp) == int(mois))
    if semaine:
        q = q.filter(extract('week', models.Hospitalisation.date_hosp) == int(semaine))
    if jour:
        q = q.filter(models.Hospitalisation.date_hosp == jour)
    return q


def build_veille_query(db, campagne_id=None, etablissement_id=None,
                       annee=None, mois=None, semaine=None):
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


def duree_en_jours(duree_str: str) -> Optional[float]:
    """Convertit '<24H' → 0.5, '7' → 7.0, etc."""
    if not duree_str:
        return None
    if duree_str == "<24H":
        return 0.5
    try:
        return float(duree_str)
    except ValueError:
        return None


# ── Années disponibles ────────────────────────────────────────
@router.get("/filtres/annees")
def get_annees(
    etablissement_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    q = db.query(
        extract('year', models.Hospitalisation.date_hosp).label('annee')
    ).join(models.Veille).filter(models.Hospitalisation.date_hosp.isnot(None))
    if etablissement_id:
        q = q.filter(models.Veille.etablissement_id == etablissement_id)
    annees = sorted(
        set(int(r.annee) for r in q.distinct().all()),
        reverse=True
    )
    return annees


# ── Mois disponibles ──────────────────────────────────────────
@router.get("/filtres/mois")
def get_mois(
    annee: int = Query(...),
    etablissement_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    q = db.query(
        extract('month', models.Hospitalisation.date_hosp).label('mois')
    ).join(models.Veille).filter(
        models.Hospitalisation.date_hosp.isnot(None),
        extract('year', models.Hospitalisation.date_hosp) == annee
    )
    if etablissement_id:
        q = q.filter(models.Veille.etablissement_id == etablissement_id)
    NOMS = {1:'Janvier',2:'Février',3:'Mars',4:'Avril',5:'Mai',6:'Juin',
            7:'Juillet',8:'Août',9:'Septembre',10:'Octobre',11:'Novembre',12:'Décembre'}
    mois = sorted(set(int(r.mois) for r in q.distinct().all()))
    return [{"numero": m, "nom": NOMS[m]} for m in mois]


# ── Semaines disponibles ──────────────────────────────────────
@router.get("/filtres/semaines")
def get_semaines(
    annee: int = Query(...),
    mois: Optional[int] = Query(None),
    etablissement_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    q = db.query(
        extract('week', models.Hospitalisation.date_hosp).label('semaine'),
        func.min(models.Hospitalisation.date_hosp).label('debut')
    ).join(models.Veille).filter(
        models.Hospitalisation.date_hosp.isnot(None),
        extract('year', models.Hospitalisation.date_hosp) == annee
    )
    if mois:
        q = q.filter(extract('month', models.Hospitalisation.date_hosp) == mois)
    if etablissement_id:
        q = q.filter(models.Veille.etablissement_id == etablissement_id)
    rows = q.group_by(
        extract('week', models.Hospitalisation.date_hosp)
    ).order_by('semaine').all()
    return [{"numero": int(r.semaine), "debut": str(r.debut)} for r in rows]


# ── KPIs ──────────────────────────────────────────────────────
@router.get("/kpis")
def get_kpis(
    campagne_id:      Optional[str] = Query(None),
    etablissement_id: Optional[str] = Query(None),
    annee:            Optional[int] = Query(None),
    mois:             Optional[int] = Query(None),
    semaine:          Optional[int] = Query(None),
    jour:             Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    hosps = build_hosp_query(
        db, campagne_id, etablissement_id, annee, mois, semaine, jour
    ).all()

    total = len(hosps)

    # Durée moyenne (conversion <24H → 0.5j)
    durees = [duree_en_jours(h.duree_hosp) for h in hosps if h.duree_hosp]
    durees = [d for d in durees if d is not None]

    urgences   = sum(1 for h in hosps if h.type_hosp == "Urgence")
    planifiees = sum(1 for h in hosps if h.type_hosp == "Planifiée")
    nuit       = sum(1 for h in hosps if h.heure_hosp == "Nuit (20h-8h)")
    weekend    = sum(1 for h in hosps if h.jour_hosp in ("Week-end", "Jour Férié"))
    retour_ems = sum(1 for h in hosps if h.issue == "Retour EMS")
    deces      = sum(1 for h in hosps if h.issue == "Décès")
    transferts = sum(1 for h in hosps if h.issue == "Transfert vers un autre EMS")

    # Top motif
    motif_counts: dict = {}
    for h in hosps:
        if h.motif:
            motif_counts[h.motif] = motif_counts.get(h.motif, 0) + 1
    top_motif = max(motif_counts, key=motif_counts.get) if motif_counts else None

    return {
        "total_hospitalisations":  total,
        "duree_moyenne_sejour":    round(sum(durees)/len(durees), 1) if durees else None,
        "repartition_urgences":    round(urgences/total*100, 1) if total else None,
        "repartition_planifiees":  round(planifiees/total*100, 1) if total else None,
        "taux_nuit":               round(nuit/total*100, 1) if total else None,
        "taux_weekend":            round(weekend/total*100, 1) if total else None,
        "top_motif":               top_motif,
        "taux_retour_ems":         round(retour_ems/total*100, 1) if total else None,
        "taux_deces":              round(deces/total*100, 1) if total else None,
        # Anciens champs conservés pour compatibilité dashboard existant
        "total_sortis":            retour_ems,
        "total_transferts":        transferts,
        "total_rehospitalisations": 0,
        "total_presents":          0,
        "attente_moyenne_avant_op": None,
        "taux_remplissage_moyen":  None,
    }


# ── Par établissement ─────────────────────────────────────────
@router.get("/par-etablissement")
def get_par_etablissement(
    campagne_id:      Optional[str] = Query(None),
    etablissement_id: Optional[str] = Query(None),
    annee:            Optional[int] = Query(None),
    mois:             Optional[int] = Query(None),
    semaine:          Optional[int] = Query(None),
    jour:             Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    etabs = db.query(models.Etablissement).filter(
        models.Etablissement.actif == True
    ).all()

    result = []
    for etab in etabs:
        if etablissement_id and str(etab.id) != etablissement_id:
            continue

        hosps = build_hosp_query(
            db, campagne_id, str(etab.id), annee, mois, semaine, jour
        ).all()

        total = len(hosps)
        durees = [duree_en_jours(h.duree_hosp) for h in hosps if h.duree_hosp]
        durees = [d for d in durees if d is not None]
        nuit = sum(1 for h in hosps if h.heure_hosp == "Nuit (20h-8h)")

        # nb_lits et nb_deces depuis la veille
        veilles = build_veille_query(
            db, campagne_id, str(etab.id), annee, mois, semaine
        ).all()
        nb_lits  = sum(v.nb_lits or 0 for v in veilles)
        nb_deces = sum(v.nb_deces or 0 for v in veilles)

        result.append({
            "etablissement_id":  str(etab.id),
            "etablissement_nom": etab.nom,
            "hospitalisations":  total,
            "urgences":          sum(1 for h in hosps if h.type_hosp == "Urgence"),
            "planifiees":        sum(1 for h in hosps if h.type_hosp == "Planifiée"),
            "duree_moyenne":     round(sum(durees)/len(durees), 1) if durees else None,
            "taux_nuit":         round(nuit/total*100, 1) if total else None,
            "retour_ems":        sum(1 for h in hosps if h.issue == "Retour EMS"),
            "deces":             sum(1 for h in hosps if h.issue == "Décès"),
            "transferts":        sum(1 for h in hosps if h.issue == "Transfert vers un autre EMS"),
            "nb_lits":           nb_lits or None,
            "nb_deces":          nb_deces or None,
            "statut_veille":     "Données disponibles" if hosps else "Aucune donnée",
            # Compatibilité anciens champs dashboard
            "duree_moyenne":     round(sum(durees)/len(durees), 1) if durees else None,
            "attente_moyenne":   None,
            "taux_remplissage":  None,
            "sortis":            sum(1 for h in hosps if h.issue == "Retour EMS"),
            "rehospitalisations": 0,
        })
    return result


# ── Par motif (ex-pathologie) ─────────────────────────────────
@router.get("/par-pathologie")
def get_par_pathologie(
    campagne_id:      Optional[str] = Query(None),
    etablissement_id: Optional[str] = Query(None),
    annee:            Optional[int] = Query(None),
    mois:             Optional[int] = Query(None),
    semaine:          Optional[int] = Query(None),
    jour:             Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    hosps = build_hosp_query(
        db, campagne_id, etablissement_id, annee, mois, semaine, jour
    ).filter(models.Hospitalisation.motif.isnot(None)).all()

    total = len(hosps)
    if total == 0:
        return []

    counts: dict = {}
    for h in hosps:
        counts[h.motif] = counts.get(h.motif, 0) + 1

    return [
        {"pathologie": k, "count": v, "pourcentage": round(v/total*100, 1)}
        for k, v in sorted(counts.items(), key=lambda x: -x[1])
    ]


# ── Évolution temporelle ──────────────────────────────────────
@router.get("/evolution")
def get_evolution(
    campagne_id:      Optional[str] = Query(None),
    etablissement_id: Optional[str] = Query(None),
    annee:            Optional[int] = Query(None),
    mois:             Optional[int] = Query(None),
    semaine:          Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    q = build_hosp_query(
        db, campagne_id, etablissement_id, annee, mois, semaine
    ).filter(models.Hospitalisation.date_hosp.isnot(None))

    all_hosps = q.all()

    def make_row(label, hosps_list):
        total = len(hosps_list)
        durees = [duree_en_jours(h.duree_hosp) for h in hosps_list if h.duree_hosp]
        durees = [d for d in durees if d is not None]
        return {
            "label":             label,
            "value":             total,
            "hospitalisations":  total,
            "urgences":          sum(1 for h in hosps_list if h.type_hosp == "Urgence"),
            "planifiees":        sum(1 for h in hosps_list if h.type_hosp == "Planifiée"),
            "nuit":              sum(1 for h in hosps_list if h.heure_hosp == "Nuit (20h-8h)"),
            "retour_ems":        sum(1 for h in hosps_list if h.issue == "Retour EMS"),
            "deces":             sum(1 for h in hosps_list if h.issue == "Décès"),
            "taux_deces":        round(sum(1 for h in hosps_list if h.issue == "Décès")/total*100, 1) if total else 0,
            "repartition_urgences": round(sum(1 for h in hosps_list if h.type_hosp == "Urgence")/total*100, 1) if total else 0,
            "taux_nuit":         round(sum(1 for h in hosps_list if h.heure_hosp == "Nuit (20h-8h)")/total*100, 1) if total else 0,
            "taux_weekend":      round(sum(1 for h in hosps_list if h.jour_hosp in ("Week-end", "Jour Férié"))/total*100, 1) if total else 0,"deces":             sum(1 for h in hosps_list if h.issue == "Décès"),
            "duree_moyenne":     round(sum(durees)/len(durees), 1) if durees else 0,
            # Compatibilité
            "sortis":            sum(1 for h in hosps_list if h.issue == "Retour EMS"),
            "transferts":        sum(1 for h in hosps_list if h.issue == "Transfert vers un autre EMS"),
            "rehospitalisations": 0,
            "presents":          0,
            "attente_moyenne":   0,
            "taux_remplissage":  0,
        }

    if semaine and annee:
        JOURS = ['Lun','Mar','Mer','Jeu','Ven','Sam','Dim']
        by_day: dict = {}
        for h in all_hosps:
            by_day.setdefault(h.date_hosp, []).append(h)
        return [
            make_row(JOURS[d.weekday()], hosps_list)
            for d, hosps_list in sorted(by_day.items())
        ]

    elif mois and annee:
        by_week: dict = {}
        for h in all_hosps:
            week = h.date_hosp.isocalendar()[1]
            by_week.setdefault(week, []).append(h)
        return [
            make_row(f"S{w}", hosps_list)
            for w, hosps_list in sorted(by_week.items())
        ]

    elif annee:
        by_month: dict = {}
        for h in all_hosps:
            by_month.setdefault(h.date_hosp.month, []).append(h)
        return [
            make_row(NOMS_MOIS[m], hosps_list)
            for m, hosps_list in sorted(by_month.items())
        ]

    else:
        by_year: dict = {}
        for h in all_hosps:
            by_year.setdefault(h.date_hosp.year, []).append(h)
        return [
            make_row(str(y), hosps_list)
            for y, hosps_list in sorted(by_year.items())
        ]


# ─── Valeurs distinctes pour filtres ─────────────────────────
@router.get("/filtres/types-hosp")
def get_types_hosp(db: Session = Depends(get_db)):
    rows = db.query(models.Hospitalisation.type_hosp).distinct().filter(
        models.Hospitalisation.type_hosp.isnot(None)
    ).all()
    return sorted([r[0] for r in rows if r[0]])

@router.get("/filtres/motifs")
def get_motifs(db: Session = Depends(get_db)):
    rows = db.query(models.Hospitalisation.motif).distinct().filter(
        models.Hospitalisation.motif.isnot(None)
    ).all()
    return sorted([r[0] for r in rows if r[0]])

@router.get("/filtres/lieux")
def get_lieux(db: Session = Depends(get_db)):
    rows = db.query(models.Hospitalisation.lieu_hosp).distinct().filter(
        models.Hospitalisation.lieu_hosp.isnot(None)
    ).all()
    return sorted([r[0] for r in rows if r[0]])

@router.get("/filtres/demandeurs")
def get_demandeurs(db: Session = Depends(get_db)):
    rows = db.query(models.Hospitalisation.demandeur).distinct().filter(
        models.Hospitalisation.demandeur.isnot(None)
    ).all()
    return sorted([r[0] for r in rows if r[0]])

@router.get("/filtres/classes-plaisir")
def get_classes_plaisir(db: Session = Depends(get_db)):
    rows = db.query(models.Hospitalisation.classe_plaisir).distinct().filter(
        models.Hospitalisation.classe_plaisir.isnot(None)
    ).all()
    return sorted([r[0] for r in rows if r[0] is not None])


# ─── Stats enrichies (graphiques camemberts/histogrammes) ────
@router.get("/stats-enrichies")
def get_stats_enrichies(
    campagne_id: Optional[str] = Query(None),
    etablissement_id: Optional[str] = Query(None),
    annee: Optional[int] = Query(None),
    mois: Optional[int] = Query(None),
    semaine: Optional[int] = Query(None),
    jour: Optional[str] = Query(None),
    type_hosp: Optional[str] = Query(None),
    motif: Optional[str] = Query(None),
    lieu_hosp: Optional[str] = Query(None),
    demandeur: Optional[str] = Query(None),
    classe_plaisir: Optional[int] = Query(None),
    type_etab: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    q = (db.query(models.Hospitalisation)
         .join(models.Veille, models.Hospitalisation.veille_id == models.Veille.id))
    if campagne_id:
        q = q.filter(models.Veille.campagne_id == campagne_id)
    if etablissement_id:
        q = q.filter(models.Veille.etablissement_id == etablissement_id)
    if annee:
        q = q.filter(extract('year', models.Hospitalisation.date_hosp) == int(annee))
    if mois:
        q = q.filter(extract('month', models.Hospitalisation.date_hosp) == int(mois))
    if semaine:
        q = q.filter(extract('week', models.Hospitalisation.date_hosp) == int(semaine))
    if jour:
        q = q.filter(models.Hospitalisation.date_hosp == jour)

    # Filtres supplémentaires sur Hospitalisation
    if type_hosp:
        q = q.filter(models.Hospitalisation.type_hosp == type_hosp)
    if motif:
        q = q.filter(models.Hospitalisation.motif == motif)
    if lieu_hosp:
        q = q.filter(models.Hospitalisation.lieu_hosp == lieu_hosp)
    if demandeur:
        q = q.filter(models.Hospitalisation.demandeur == demandeur)
    if classe_plaisir is not None:
        q = q.filter(models.Hospitalisation.classe_plaisir == classe_plaisir)
    if type_etab:
        q = q.join(models.Etablissement, models.Veille.etablissement_id == models.Etablissement.id, isouter=True).filter(models.Etablissement.nom.ilike(f"{type_etab}%"))

    hosps = q.all()
    total = len(hosps)

    def count_field(field):
        counts = {}
        for h in hosps:
            val = getattr(h, field, None)
            if val is not None:
                counts[str(val)] = counts.get(str(val), 0) + 1
        tot = sum(counts.values())
        return [
            {"label": k, "count": v, "pourcentage": round(v/tot*100, 1) if tot > 0 else 0}
            for k, v in sorted(counts.items(), key=lambda x: -x[1])
        ]

    return {
        "total": total,
        "par_genre": count_field("genre"),
        "par_jour_hosp": count_field("jour_hosp"),
        "par_heure_hosp": count_field("heure_hosp"),
        "par_demandeur": count_field("demandeur"),
        "par_lieu_hosp": count_field("lieu_hosp"),
        "par_type_hosp": count_field("type_hosp"),
        "par_motif": count_field("motif"),
        "par_classe_plaisir": count_field("classe_plaisir"),
        "par_issue": count_field("issue"),
    }


# ─── Détail hospitalisations d'un établissement ───────────────
@router.get("/detail-hospitalisations")
def get_detail_hospitalisations(
    etablissement_id: str = Query(...),
    annee: Optional[int] = Query(None),
    mois: Optional[int] = Query(None),
    semaine: Optional[int] = Query(None),
    jour: Optional[str] = Query(None),
    type_hosp: Optional[str] = Query(None),
    motif: Optional[str] = Query(None),
    lieu_hosp: Optional[str] = Query(None),
    demandeur: Optional[str] = Query(None),
    classe_plaisir: Optional[int] = Query(None),
    limit: int = Query(100),
    db: Session = Depends(get_db)
):
    q = (db.query(models.Hospitalisation)
         .join(models.Veille, models.Hospitalisation.veille_id == models.Veille.id))
    q = q.filter(models.Veille.etablissement_id == etablissement_id)
    if annee:
        q = q.filter(extract('year', models.Hospitalisation.date_hosp) == int(annee))
    if mois:
        q = q.filter(extract('month', models.Hospitalisation.date_hosp) == int(mois))
    if semaine:
        q = q.filter(extract('week', models.Hospitalisation.date_hosp) == int(semaine))
    if jour:
        q = q.filter(models.Hospitalisation.date_hosp == jour)
    if type_hosp:
        q = q.filter(models.Hospitalisation.type_hosp == type_hosp)
    if motif:
        q = q.filter(models.Hospitalisation.motif == motif)
    if lieu_hosp:
        q = q.filter(models.Hospitalisation.lieu_hosp == lieu_hosp)
    if demandeur:
        q = q.filter(models.Hospitalisation.demandeur == demandeur)
    if classe_plaisir is not None:
        q = q.filter(models.Hospitalisation.classe_plaisir == classe_plaisir)

    hosps = q.order_by(models.Hospitalisation.date_hosp.desc()).limit(limit).all()
    return [
        {
            "id": str(h.id),
            "num_resident": h.num_resident,
            "date_hosp": str(h.date_hosp) if h.date_hosp else None,
            "age": h.age,
            "genre": h.genre,
            "classe_plaisir": h.classe_plaisir,
            "jour_hosp": h.jour_hosp,
            "heure_hosp": h.heure_hosp,
            "type_hosp": h.type_hosp,
            "demandeur": h.demandeur,
            "lieu_hosp": h.lieu_hosp,
            "duree_hosp": h.duree_hosp,
            "motif": h.motif,
            "issue": h.issue,
        }
        for h in hosps
    ]
