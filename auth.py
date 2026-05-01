from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional, List
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from dotenv import load_dotenv
import os

from database import get_db
import models

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", os.getenv("JWT_SECRET", "changez-moi-en-production"))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8  # 8 heures

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
router = APIRouter(prefix="/auth", tags=["Authentification"])


# ─── Schémas ─────────────────────────────────────────────────
class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict

class UserCreate(BaseModel):
    nom: str
    prenom: str
    email: str
    mot_de_passe: str
    role: str = "contrib"
    etablissement_ids: Optional[List[str]] = []  # Multi-établissements

class UserUpdate(BaseModel):
    nom: Optional[str] = None
    prenom: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    actif: Optional[bool] = None
    etablissement_ids: Optional[List[str]] = None


# ─── Utilitaires ─────────────────────────────────────────────
def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_user_by_email(db: Session, email: str):
    return db.query(models.Utilisateur).filter(models.Utilisateur.email == email).first()

def format_user(user: models.Utilisateur) -> dict:
    return {
        "id": str(user.id),
        "nom": user.nom,
        "prenom": user.prenom,
        "email": user.email,
        "role": user.role,
        "actif": user.actif,
        "etablissement_ids": [str(e.id) for e in user.etablissements],
        "etablissements": [{"id": str(e.id), "nom": e.nom} for e in user.etablissements],
        # Compatibilité ancienne version
        "etablissement_id": str(user.etablissements[0].id) if user.etablissements else None,
    }


# ─── Dépendance : utilisateur connecté ───────────────────────
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token invalide ou expiré",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = get_user_by_email(db, email)
    if user is None or not user.actif:
        raise credentials_exception
    return user


# ─── Dépendances de permissions ───────────────────────────────
def require_admin(current_user: models.Utilisateur = Depends(get_current_user)):
    """Accès réservé aux administrateurs."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs")
    return current_user

def require_can_saisir(current_user: models.Utilisateur = Depends(get_current_user)):
    """Peut saisir des campagnes : admin et contrib uniquement."""
    if current_user.role not in ["admin", "contrib"]:
        raise HTTPException(status_code=403, detail="Vous n'avez pas le droit de saisir des campagnes")
    return current_user

def require_can_export(current_user: models.Utilisateur = Depends(get_current_user)):
    """Peut exporter : admin, dir-hev, contrib."""
    if current_user.role not in ["admin", "dir-hev", "contrib"]:
        raise HTTPException(status_code=403, detail="Vous n'avez pas le droit d'exporter")
    return current_user

def require_authenticated(current_user: models.Utilisateur = Depends(get_current_user)):
    """Simple vérification d'authentification."""
    return current_user

def get_etablissement_ids_for_user(user: models.Utilisateur) -> Optional[List[str]]:
    """
    Retourne la liste des IDs d'établissements accessibles pour un user.
    None = tous les établissements (admin, dir-hev).
    Liste = seulement ces établissements (dir-eta, contrib).
    """
    if user.role in ["admin", "dir-hev"]:
        return None  # Accès total
    return [str(e.id) for e in user.etablissements]


# ─── Routes ──────────────────────────────────────────────────
@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = get_user_by_email(db, form_data.username)
    if not user or not verify_password(form_data.password, user.mot_de_passe):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
        )
    token = create_access_token({"sub": user.email, "role": user.role})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": format_user(user),
    }


@router.post("/register", status_code=201)
def register(data: UserCreate, db: Session = Depends(get_db)):
    if get_user_by_email(db, data.email):
        raise HTTPException(status_code=409, detail="Cet email est déjà utilisé")

    # Valider le rôle
    if data.role not in models.ROLES_VALIDES:
        raise HTTPException(status_code=400, detail=f"Rôle invalide. Rôles valides : {models.ROLES_VALIDES}")

    user = models.Utilisateur(
        nom=data.nom,
        prenom=data.prenom,
        email=data.email,
        mot_de_passe=hash_password(data.mot_de_passe),
        role=data.role,
    )

    # Rattacher les établissements
    if data.etablissement_ids:
        etabs = db.query(models.Etablissement).filter(
            models.Etablissement.id.in_(data.etablissement_ids)
        ).all()
        user.etablissements = etabs

    db.add(user)
    db.commit()
    db.refresh(user)
    return {"message": "Compte créé", "id": str(user.id)}


@router.get("/me")
def me(current_user: models.Utilisateur = Depends(get_current_user)):
    return format_user(current_user)


@router.get("/users", dependencies=[Depends(require_admin)])
def list_users(db: Session = Depends(get_db)):
    users = db.query(models.Utilisateur).order_by(models.Utilisateur.created_at.desc()).all()
    return [format_user(u) for u in users]


@router.post("/users", dependencies=[Depends(require_admin)], status_code=201)
def create_user(data: UserCreate, db: Session = Depends(get_db)):
    """Création d'un utilisateur par l'admin."""
    return register(data, db)


@router.patch("/users/{user_id}", dependencies=[Depends(require_admin)])
def update_user(user_id: str, data: UserUpdate, db: Session = Depends(get_db)):
    """Modification d'un utilisateur par l'admin."""
    user = db.query(models.Utilisateur).filter(models.Utilisateur.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    if data.nom is not None:
        user.nom = data.nom
    if data.prenom is not None:
        user.prenom = data.prenom
    if data.email is not None:
        existing = get_user_by_email(db, data.email)
        if existing and str(existing.id) != user_id:
            raise HTTPException(status_code=409, detail="Cet email est déjà utilisé")
        user.email = data.email
    if data.role is not None:
        if data.role not in models.ROLES_VALIDES:
            raise HTTPException(status_code=400, detail=f"Rôle invalide. Rôles valides : {models.ROLES_VALIDES}")
        user.role = data.role
    if data.actif is not None:
        user.actif = data.actif
    if data.etablissement_ids is not None:
        etabs = db.query(models.Etablissement).filter(
            models.Etablissement.id.in_(data.etablissement_ids)
        ).all()
        user.etablissements = etabs

    db.commit()
    db.refresh(user)
    return format_user(user)


@router.delete("/users/{user_id}", dependencies=[Depends(require_admin)], status_code=204)
def delete_user(user_id: str, db: Session = Depends(get_db)):
    """Désactivation d'un utilisateur par l'admin."""
    user = db.query(models.Utilisateur).filter(models.Utilisateur.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    user.actif = False
    db.commit()

@router.get("/roles")
def get_roles():
    """Retourne la liste des rôles disponibles avec leurs descriptions."""
    return [
        {
            "value": "admin",
            "label": "Administrateur Héviva",
            "description": "Accès complet : utilisateurs, paramètres, exports, toutes les données",
            "permissions": {
                "voir_tous_etablissements": True,
                "tableau_bord_global": True,
                "saisir_campagnes": True,
                "gerer_utilisateurs": True,
                "exporter": True,
            }
        },
        {
            "value": "dir-hev",
            "label": "Direction Héviva",
            "description": "Tableaux de bord consolidés et analyses globales — lecture seule",
            "permissions": {
                "voir_tous_etablissements": True,
                "tableau_bord_global": True,
                "saisir_campagnes": False,
                "gerer_utilisateurs": False,
                "exporter": True,
            }
        },
        {
            "value": "dir-eta",
            "label": "Direction Établissement",
            "description": "Accès limité à ses établissements — lecture seule",
            "permissions": {
                "voir_tous_etablissements": False,
                "tableau_bord_global": False,
                "saisir_campagnes": False,
                "gerer_utilisateurs": False,
                "exporter": False,
            }
        },
        {
            "value": "contrib",
            "label": "Contributeur Établissement",
            "description": "Saisie et consultation sur ses établissements + exports",
            "permissions": {
                "voir_tous_etablissements": False,
                "tableau_bord_global": False,
                "saisir_campagnes": True,
                "gerer_utilisateurs": False,
                "exporter": True,
            }
        },
    ]
