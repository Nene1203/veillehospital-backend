-- ============================================================
-- VeilleHospital — schéma propre (sans table patients orpheline)
-- À appliquer sur veille_hospital_uat et veille_hospital_prod
-- ============================================================

-- Extension UUID
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ─── Établissements ──────────────────────────────────────────
CREATE TABLE etablissements (
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nom        VARCHAR(200) NOT NULL,
    adresse    TEXT,
    telephone  VARCHAR(20),
    nb_lits    INTEGER DEFAULT 0,
    actif      BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT etablissements_nom_unique UNIQUE (nom)
);

-- ─── Utilisateurs ────────────────────────────────────────────
CREATE TABLE utilisateurs (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nom              VARCHAR(100) NOT NULL,
    prenom           VARCHAR(100) NOT NULL,
    email            VARCHAR(200) NOT NULL UNIQUE,
    mot_de_passe     VARCHAR(200) NOT NULL,
    role             VARCHAR(20) DEFAULT 'responsable',
    etablissement_id UUID REFERENCES etablissements(id) ON DELETE SET NULL,
    actif            BOOLEAN DEFAULT TRUE,
    created_at       TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT utilisateurs_role_check CHECK (role IN ('admin', 'responsable', 'lecteur'))
);

-- ─── Campagnes ───────────────────────────────────────────────
CREATE TABLE campagnes (
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    titre      VARCHAR(200) NOT NULL,
    type       VARCHAR(20) DEFAULT 'hebdomadaire',
    date_debut DATE NOT NULL,
    date_fin   DATE NOT NULL,
    statut     VARCHAR(20) DEFAULT 'ouverte',
    created_by UUID REFERENCES utilisateurs(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT campagnes_type_check   CHECK (type   IN ('hebdomadaire', 'mensuel', 'annuel')),
    CONSTRAINT campagnes_statut_check CHECK (statut IN ('ouverte', 'cloturee', 'archivee'))
);

CREATE INDEX idx_campagnes_dates ON campagnes (date_debut, date_fin);

-- ─── Veilles ─────────────────────────────────────────────────
CREATE TABLE veilles (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    campagne_id         UUID NOT NULL REFERENCES campagnes(id)      ON DELETE CASCADE,
    etablissement_id    UUID NOT NULL REFERENCES etablissements(id)  ON DELETE CASCADE,
    responsable_id      UUID REFERENCES utilisateurs(id),
    statut              VARCHAR(20) DEFAULT 'brouillon',
    date_saisie         DATE DEFAULT CURRENT_DATE,
    nb_lits_disponibles INTEGER DEFAULT 0,
    nb_lits_occupes     INTEGER DEFAULT 0,
    nb_lits             INTEGER DEFAULT 0,
    nb_deces            INTEGER DEFAULT 0,
    reseau_sante        VARCHAR(100),
    commentaires        TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT veilles_statut_check CHECK (statut IN ('brouillon', 'soumis', 'valide')),
    CONSTRAINT veilles_campagne_etab_unique UNIQUE (campagne_id, etablissement_id)
);

CREATE INDEX idx_veilles_campagne ON veilles (campagne_id);
CREATE INDEX idx_veilles_etab     ON veilles (etablissement_id);

-- ─── Hospitalisations ────────────────────────────────────────
CREATE TABLE hospitalisations (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    veille_id       UUID NOT NULL REFERENCES veilles(id) ON DELETE CASCADE,
    date_hosp       DATE,
    num_resident    VARCHAR(50),
    age             INTEGER,
    genre           VARCHAR(10),
    classe_plaisir  INTEGER,
    jour_hosp       VARCHAR(30),
    heure_hosp      VARCHAR(20),
    type_hosp       VARCHAR(20),
    demandeur       VARCHAR(60),
    lieu_hosp       VARCHAR(20),
    duree_hosp      VARCHAR(10),
    motif           VARCHAR(100),
    issue           VARCHAR(50),
    remarques       TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_hosp_veille ON hospitalisations (veille_id);
CREATE INDEX idx_hosp_type   ON hospitalisations (type_hosp);
CREATE INDEX idx_hosp_motif  ON hospitalisations (motif);
