# Backend

Backend de l'application Boursomatic (FastAPI, Python 3.12).

## Structure
- `app/` : Code applicatif (API, modèles, services)
  - `models.py` : Modèles SQLModel pour la base de données
  - `database.py` : Configuration de connexion à la base de données
- `tests/` : Tests unitaires et d'intégration
- `alembic/` : Migrations de base de données
- `scripts/` : Scripts utilitaires (migrations, tests)
- `docs/` : Documentation (schéma DB, API, etc.)

## Installation

### Prérequis
- Python 3.12+
- PostgreSQL 14+
- pip ou uv pour la gestion des dépendances

### Configuration

1. Créer un environnement virtuel :
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# ou
venv\Scripts\activate  # Windows
```

2. Installer les dépendances :
```bash
pip install -r requirements.txt
# ou pour le développement :
pip install -r requirements-dev.txt
```

3. Configurer les variables d'environnement :
```bash
cp .env.example .env
# Éditer .env avec vos paramètres
```

## Base de Données

### Schéma

Le schéma initial inclut les tables suivantes :
- `users` : Comptes utilisateurs avec authentification
- `user_settings` : Paramètres et préférences utilisateur
- `instruments` : Instruments financiers (actions, ETFs)
- `price_bars` : Données OHLCV (daily + intraday)
- `features` : Indicateurs techniques calculés
- `model_versions` : Versions du modèle ML
- `recommendations` : Recommandations générées par le modèle

Voir [docs/database_schema.md](docs/database_schema.md) pour la documentation complète.

### Migrations

#### Appliquer les migrations
```bash
# Avec Alembic directement
alembic upgrade head

# Ou avec le script helper
./scripts/db_migration.sh migrate
```

#### Vérifier le statut
```bash
alembic current
alembic history

# Ou avec le script
./scripts/db_migration.sh status
```

#### Rollback
```bash
alembic downgrade -1  # Retour d'une version
alembic downgrade base  # Retour à zéro

# Ou avec le script
./scripts/db_migration.sh rollback
```

#### Recréer la base
```bash
./scripts/db_migration.sh recreate
```

### Tests

Valider le schéma sans base de données :
```bash
python scripts/test_schema.py
```

## Développement

### Linting
```bash
ruff check app/ tests/
ruff format app/ tests/
```

### Tests
```bash
pytest
```

### Créer une nouvelle migration
```bash
# Autogénérée (nécessite une connexion DB)
alembic revision --autogenerate -m "Description"

# Manuelle
alembic revision -m "Description"
```

## Convention de Code

- snake_case pour les noms de tables et colonnes
- UUID pour les clés primaires
- Type hints obligatoires
- Soft delete avec `is_deleted` au lieu de suppression physique
- Timestamps `created_at` et `updated_at` pour l'audit
