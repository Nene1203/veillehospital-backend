# VeilleHospital — Backend FastAPI + PostgreSQL

## Prérequis

- Python 3.11+
- PostgreSQL installé et en cours d'exécution
- Node.js 18+ (pour le frontend React)

---

## Étape 1 — Créer la base de données PostgreSQL

Ouvrez un terminal et connectez-vous à PostgreSQL :

```bash
psql -U postgres
```

Puis créez la base :

```sql
CREATE DATABASE veille_hospital;
\q
```

Ensuite, exécutez le schéma :

```bash
psql -U postgres -d veille_hospital -f schema.sql
```

---

## Étape 2 — Configurer le backend

```bash
# Dans le dossier backend/
cd backend

# Créer un environnement virtuel Python
python3 -m venv venv
source venv/bin/activate      # Mac/Linux
# venv\Scripts\activate       # Windows

# Installer les dépendances
pip install -r requirements.txt

# Configurer les variables d'environnement
cp .env.example .env
```

Éditez le fichier `.env` :

```
DATABASE_URL=postgresql://postgres:VOTRE_MOT_DE_PASSE@localhost:5432/veille_hospital
SECRET_KEY=une-cle-secrete-longue-et-aleatoire
ALLOWED_ORIGINS=http://localhost:5173
```

---

## Étape 3 — Lancer le backend

```bash
# Depuis le dossier backend/, avec le venv activé
uvicorn main:app --reload --port 8000
```

L'API est disponible sur :
- **http://localhost:8000** — API
- **http://localhost:8000/docs** — Documentation interactive (Swagger)
- **http://localhost:8000/redoc** — Documentation alternative

---

## Étape 4 — Connecter le frontend React

Copiez le fichier `api.js` dans votre projet React :

```bash
cp api.js ../veille-hospital/src/data/api.js
```

Créez un fichier `.env` dans votre projet React :

```bash
# Dans veille-hospital/
echo "VITE_API_URL=http://localhost:8000" > .env
```

Ensuite dans `Dashboard.jsx`, remplacez les données mockées par des appels API :

```jsx
import { getKpis, getParEtablissement, getParPathologie } from "../data/api";

// Dans un useEffect :
useEffect(() => {
  getKpis({ campagne_id: campagneId }).then(setKpis);
  getParEtablissement({ campagne_id: campagneId }).then(setEtabData);
  getParPathologie({ campagne_id: campagneId }).then(setPathoData);
}, [campagneId]);
```

Dans `Saisie.jsx`, pour soumettre le formulaire :

```jsx
import { createVeille, soumettreVeille } from "../data/api";

const handleSubmit = async () => {
  const veille = await createVeille({
    campagne_id: campagneSelectionnee,
    etablissement_id: etablissementId,
    nb_lits_disponibles: nbLits,
    nb_lits_occupes: litsOccupes,
    patients: rows.map(r => ({
      ...r,
      rehospitalisation: r.rehospitalisation === "Oui",
    })),
  });
  await soumettreVeille(veille.id);
  alert("Saisie soumise !");
};
```

---

## Routes disponibles

| Méthode | Route | Description |
|---------|-------|-------------|
| GET | `/etablissements/` | Liste des établissements |
| GET | `/campagnes/` | Liste des campagnes |
| POST | `/campagnes/` | Créer une campagne |
| PATCH | `/campagnes/{id}/cloturer` | Clôturer une campagne |
| GET | `/veilles/` | Liste des veilles (filtrable) |
| POST | `/veilles/` | Créer une veille + patients |
| GET | `/veilles/{id}` | Détail d'une veille |
| PUT | `/veilles/{id}` | Modifier une veille |
| PATCH | `/veilles/{id}/soumettre` | Soumettre une veille |
| DELETE | `/veilles/{id}` | Supprimer une veille |
| GET | `/dashboard/kpis` | KPIs globaux |
| GET | `/dashboard/par-etablissement` | Stats par établissement |
| GET | `/dashboard/par-pathologie` | Stats par pathologie |

Tous les endpoints GET du dashboard acceptent les paramètres : `campagne_id`, `etablissement_id`, `date_debut`, `date_fin`.
