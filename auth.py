"""
Authentification des agents/administrateurs (back-office), par jeton JWT.
Voir dossier de conception, section 8.2 (JWT) et 8.6 (hachage des mots de passe).

Variable d'environnement attendue en production :
    JWT_SECRET_KEY   — longue chaîne aléatoire et secrète (jamais dans le code)
Si absente, une clé de développement est utilisée : NE JAMAIS utiliser cette
valeur par défaut en production.
"""

import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
import bcrypt
from sqlalchemy.orm import Session

import models
from database import get_db

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "cle-de-developpement-a-ne-jamais-utiliser-en-production")
ALGORITHM = "HS256"
DUREE_JETON_MINUTES = 60  # jeton valide 1h, cf. conception 8.6

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def _vers_octets(mot_de_passe: str) -> bytes:
    # bcrypt ne traite que les 72 premiers octets : on tronque explicitement
    # (les versions récentes de bcrypt lèvent sinon une erreur).
    return mot_de_passe.encode("utf-8")[:72]


def hacher_mot_de_passe(mot_de_passe: str) -> str:
    return bcrypt.hashpw(_vers_octets(mot_de_passe), bcrypt.gensalt()).decode("utf-8")


def verifier_mot_de_passe(mot_de_passe: str, mot_de_passe_hache: str) -> bool:
    try:
        return bcrypt.checkpw(_vers_octets(mot_de_passe), mot_de_passe_hache.encode("utf-8"))
    except ValueError:
        return False


def creer_jeton_acces(nom_utilisateur: str) -> str:
    expiration = datetime.utcnow() + timedelta(minutes=DUREE_JETON_MINUTES)
    payload = {"sub": nom_utilisateur, "exp": expiration}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def authentifier_agent(db: Session, nom_utilisateur: str, mot_de_passe: str) -> Optional[models.Agent]:
    agent = db.query(models.Agent).filter(models.Agent.nom_utilisateur == nom_utilisateur).first()
    if not agent or not verifier_mot_de_passe(mot_de_passe, agent.mot_de_passe_hache):
        return None
    return agent


def agent_courant(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.Agent:
    """Dépendance FastAPI : à ajouter sur tout endpoint réservé aux agents/admins.
    Décode le jeton JWT, vérifie sa validité, et renvoie l'agent correspondant."""
    exception_invalide = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Jeton invalide ou expiré",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        nom_utilisateur = payload.get("sub")
        if nom_utilisateur is None:
            raise exception_invalide
    except JWTError:
        raise exception_invalide

    agent = db.query(models.Agent).filter(models.Agent.nom_utilisateur == nom_utilisateur).first()
    if agent is None:
        raise exception_invalide
    return agent


def administrateur_courant(agent: models.Agent = Depends(agent_courant)) -> models.Agent:
    """Dépendance plus stricte : réservée aux endpoints administrateur uniquement."""
    if not agent.est_administrateur:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Réservé aux administrateurs")
    return agent
