-- ============================================================
--  VeilleHospital — Schéma PostgreSQL
-- ============================================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ------------------------------------------------------------
-- 1. Établissements
-- ------------------------------------------------------------
CREATE TABLE etablissements (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nom         VARCHAR(200) NOT NULL,
    adresse     TEXT,
    telephone   VARCHAR(20),
    nb_lits     INTEGER DEFAULT 0,
    actif       BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ------------------------------------------------------------
-- 2. Utilisateurs (responsables de saisie)
-- ------------------------------------------------------------
CREATE TABLE utilisateurs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nom             VARCHAR(100) NOT NULL,
    prenom          VARCHAR(100) NOT NULL,
    email           VARCHAR(200) UNIQUE NOT NULL,
    mot_de_passe    VARCHAR(200) NOT NULL,  -- hashé bcrypt
    role            VARCHAR(20) DEFAULT 'responsable' CHECK (role IN ('admin','responsable','lecteur')),
    etablissement_id UUID REFERENCES etablissements(id) ON DELETE SET NULL,
    actif           BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ------------------------------------------------------------
-- 3. Campagnes de saisie
-- ------------------------------------------------------------
CREATE TABLE campagnes (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    titre           VARCHAR(200) NOT NULL,
    type            VARCHAR(20) DEFAULT 'hebdomadaire' CHECK (type IN ('hebdomadaire','mensuel','annuel')),
    date_debut      DATE NOT NULL,
    date_fin        DATE NOT NULL,
    statut          VARCHAR(20) DEFAULT 'ouverte' CHECK (statut IN ('ouverte','cloturee','archivee')),
    created_by      UUID REFERENCES utilisateurs(id),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ------------------------------------------------------------
-- 4. Veilles (une saisie par établissement par campagne)
-- ------------------------------------------------------------
CREATE TABLE veilles (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    campagne_id         UUID NOT NULL REFERENCES campagnes(id) ON DELETE CASCADE,
    etablissement_id    UUID NOT NULL REFERENCES etablissements(id) ON DELETE CASCADE,
    responsable_id      UUID REFERENCES utilisateurs(id),
    statut              VARCHAR(20) DEFAULT 'brouillon' CHECK (statut IN ('brouillon','soumis','valide')),
    date_saisie         DATE DEFAULT CURRENT_DATE,
    nb_lits_disponibles INTEGER DEFAULT 0,
    nb_lits_occupes     INTEGER DEFAULT 0,
    commentaires        TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (campagne_id, etablissement_id)
);

-- ------------------------------------------------------------
-- 5. Patients hospitalisés (lignes du formulaire)
-- ------------------------------------------------------------
CREATE TABLE patients (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    veille_id           UUID NOT NULL REFERENCES veilles(id) ON DELETE CASCADE,

    -- Identité
    nom                 VARCHAR(100),
    prenom              VARCHAR(100),
    age                 INTEGER CHECK (age BETWEEN 0 AND 130),
    chambre             VARCHAR(20),

    -- Médical
    pathologie          VARCHAR(100),
    operation_subie     VARCHAR(200),

    -- Temporel
    date_entree         DATE,
    date_sortie         DATE,
    duree_sejour        INTEGER GENERATED ALWAYS AS (
                            CASE WHEN date_sortie IS NOT NULL AND date_entree IS NOT NULL
                            THEN (date_sortie - date_entree)
                            ELSE NULL END
                        ) STORED,

    -- Opératoire
    attente_avant_op_jours  INTEGER DEFAULT 0,
    temps_apres_op_jours    INTEGER DEFAULT 0,

    -- Logistique
    mode_entree         VARCHAR(50) DEFAULT 'Urgences'
                            CHECK (mode_entree IN ('Urgences','Programmé','Transfert','Autre')),
    statut              VARCHAR(30) DEFAULT 'Hospitalisé'
                            CHECK (statut IN ('Hospitalisé','Sorti','Transféré','Décédé')),
    destination_sortie  VARCHAR(50)
                            CHECK (destination_sortie IN ('Domicile','Autre EHPAD','Hôpital','Famille','Décès', NULL)),
    rehospitalisation   BOOLEAN DEFAULT FALSE,

    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- ------------------------------------------------------------
-- Index utiles pour les filtres dashboard
-- ------------------------------------------------------------
CREATE INDEX idx_patients_veille      ON patients(veille_id);
CREATE INDEX idx_patients_pathologie  ON patients(pathologie);
CREATE INDEX idx_patients_statut      ON patients(statut);
CREATE INDEX idx_veilles_campagne     ON veilles(campagne_id);
CREATE INDEX idx_veilles_etab         ON veilles(etablissement_id);
CREATE INDEX idx_campagnes_dates      ON campagnes(date_debut, date_fin);

-- ------------------------------------------------------------
-- Données de démo
-- ------------------------------------------------------------
INSERT INTO etablissements (nom, nb_lits) VALUES
    ('Résidence du Parc', 80),
    ('Les Jardins d''Automne', 65),
    ('Villa Soleil', 90),
    ('Maison de repos Nord', 55),
    ('Résidence Belle-Vue', 70);
