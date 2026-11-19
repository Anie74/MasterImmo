"""
Configuration de la base de données.

Par défaut, utilise SQLite (fichier local `immobilier.db`, aucune installation
requise). Pour passer à PostgreSQL, définis la variable d'environnement
DATABASE_URL avant de lancer l'app, par exemple :

    export DATABASE_URL="postgresql://user:password@localhost:5432/immobilier"

Le reste du code ne change pas : SQLAlchemy s'adapte automatiquement.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./immobilier.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Fournit une session DB à chaque requête, puis la ferme proprement."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
