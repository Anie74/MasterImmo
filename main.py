import os
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sqlalchemy.orm import Session

import models
import schemas
import auth
import recommandation
from database import engine, get_db

# Crée les tables si elles n'existent pas encore
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="API Haino et Cie Immobilier",
    description="API pour gérer les annonces, les messages de contact et les "
                 "recommandations personnalisées du site.",
    version="2.0.0",
)

# ---------- Limitation de débit (anti-abus, cf. conception 8.4) ----------
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ---------- CORS ----------
# En développement, on autorise tout. En production, définir la variable
# d'environnement ORIGINES_AUTORISEES avec le(s) domaine(s) exact(s) du site
# (cf. conception 8.4), par exemple :
#   export ORIGINES_AUTORISEES="https://www.haino-immobilier.fr"
origines = os.getenv("ORIGINES_AUTORISEES", "*")
origines_liste = [o.strip() for o in origines.split(",")] if origines != "*" else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origines_liste,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Statut"])
def racine():
    return {"statut": "ok", "message": "API Haino et Cie Immobilier — voir /docs"}


# ==================== AUTHENTIFICATION (back-office) ====================

@app.post("/token", response_model=schemas.Token, tags=["Authentification"])
@limiter.limit("10/minute")
def connexion(request: Request, form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Connexion d'un agent/administrateur. Renvoie un jeton JWT valide 1h,
    à fournir dans l'en-tête Authorization: Bearer <jeton> des requêtes protégées."""
    agent = auth.authentifier_agent(db, form.username, form.password)
    if not agent:
        raise HTTPException(status_code=401, detail="Identifiant ou mot de passe incorrect")
    return schemas.Token(access_token=auth.creer_jeton_acces(agent.nom_utilisateur))


@app.get("/agents/moi", response_model=schemas.AgentOut, tags=["Authentification"])
def mon_profil(agent: models.Agent = Depends(auth.agent_courant)):
    """Vérifie le jeton fourni et renvoie l'identité de l'agent connecté."""
    return agent


# ==================== ANNONCES ====================

@app.get("/annonces", response_model=List[schemas.AnnonceOut], tags=["Annonces"])
def lister_annonces(
    ville: Optional[str] = Query(None, description="Filtrer par ville"),
    type_transaction: Optional[models.TypeTransaction] = Query(None, description="vente / location / commercial"),
    prix_max: Optional[float] = Query(None, description="Prix maximum"),
    db: Session = Depends(get_db),
):
    """Liste les annonces, avec filtres optionnels. Accès public."""
    q = db.query(models.Annonce)
    if ville:
        q = q.filter(models.Annonce.ville.ilike(f"%{ville}%"))
    if type_transaction:
        q = q.filter(models.Annonce.type_transaction == type_transaction)
    if prix_max is not None:
        q = q.filter(models.Annonce.prix <= prix_max)
    return q.order_by(models.Annonce.cree_le.desc()).all()


@app.get("/annonces/{annonce_id}", response_model=schemas.AnnonceOut, tags=["Annonces"])
def obtenir_annonce(annonce_id: int, db: Session = Depends(get_db)):
    annonce = db.query(models.Annonce).filter(models.Annonce.id == annonce_id).first()
    if not annonce:
        raise HTTPException(status_code=404, detail="Annonce introuvable")
    return annonce


@app.post("/annonces", response_model=schemas.AnnonceOut, status_code=201, tags=["Annonces"])
def creer_annonce(
    annonce: schemas.AnnonceCreate,
    db: Session = Depends(get_db),
    agent: models.Agent = Depends(auth.agent_courant),
):
    """Réservé aux agents/administrateurs authentifiés (JWT)."""
    existe = db.query(models.Annonce).filter(models.Annonce.reference == annonce.reference).first()
    if existe:
        raise HTTPException(status_code=409, detail="Cette référence existe déjà")
    nouvelle = models.Annonce(**annonce.model_dump())
    db.add(nouvelle)
    db.commit()
    db.refresh(nouvelle)
    return nouvelle


@app.put("/annonces/{annonce_id}", response_model=schemas.AnnonceOut, tags=["Annonces"])
def modifier_annonce(
    annonce_id: int,
    maj: schemas.AnnonceUpdate,
    db: Session = Depends(get_db),
    agent: models.Agent = Depends(auth.agent_courant),
):
    """Réservé aux agents/administrateurs authentifiés (JWT)."""
    annonce = db.query(models.Annonce).filter(models.Annonce.id == annonce_id).first()
    if not annonce:
        raise HTTPException(status_code=404, detail="Annonce introuvable")
    for champ, valeur in maj.model_dump(exclude_unset=True).items():
        setattr(annonce, champ, valeur)
    db.commit()
    db.refresh(annonce)
    return annonce


@app.delete("/annonces/{annonce_id}", status_code=204, tags=["Annonces"])
def supprimer_annonce(
    annonce_id: int,
    db: Session = Depends(get_db),
    agent: models.Agent = Depends(auth.agent_courant),
):
    """Réservé aux agents/administrateurs authentifiés (JWT)."""
    annonce = db.query(models.Annonce).filter(models.Annonce.id == annonce_id).first()
    if not annonce:
        raise HTTPException(status_code=404, detail="Annonce introuvable")
    db.delete(annonce)
    db.commit()
    return None


# ==================== CONTACT ====================

@app.post("/contact", response_model=schemas.MessageContactOut, status_code=201, tags=["Contact"])
@limiter.limit("5/minute")
def envoyer_message(request: Request, msg: schemas.MessageContactCreate, db: Session = Depends(get_db)):
    """Endpoint appelé par le formulaire de contact du site. Limité à 5 requêtes/minute/IP."""
    nouveau = models.MessageContact(**msg.model_dump())
    db.add(nouveau)
    db.commit()
    db.refresh(nouveau)
    return nouveau


@app.get("/contact", response_model=List[schemas.MessageContactOut], tags=["Contact"])
def lister_messages(db: Session = Depends(get_db), agent: models.Agent = Depends(auth.agent_courant)):
    """Réservé aux agents/administrateurs authentifiés (JWT)."""
    return db.query(models.MessageContact).order_by(models.MessageContact.envoye_le.desc()).all()


# ==================== RECOMMANDATION ====================

def _obtenir_ou_creer_utilisateur(db: Session, session_id: str) -> models.Utilisateur:
    utilisateur = db.query(models.Utilisateur).filter(models.Utilisateur.session_id == session_id).first()
    if utilisateur is None:
        utilisateur = models.Utilisateur(session_id=session_id)
        db.add(utilisateur)
        db.commit()
        db.refresh(utilisateur)
    return utilisateur


@app.post("/interactions", response_model=schemas.InteractionOut, status_code=201, tags=["Recommandation"])
def enregistrer_interaction(inter: schemas.InteractionCreate, db: Session = Depends(get_db)):
    """Enregistre une interaction (vue, favori, contact) pour alimenter les
    recommandations. Crée l'utilisateur anonyme s'il n'existe pas encore."""
    utilisateur = _obtenir_ou_creer_utilisateur(db, inter.utilisateur_session_id)

    annonce = db.query(models.Annonce).filter(models.Annonce.id == inter.annonce_id).first()
    if not annonce:
        raise HTTPException(status_code=404, detail="Annonce introuvable")

    nouvelle = models.Interaction(
        utilisateur_id=utilisateur.id,
        annonce_id=inter.annonce_id,
        type=inter.type,
        poids=models.POIDS_INTERACTION[inter.type],
    )
    db.add(nouvelle)
    db.commit()
    db.refresh(nouvelle)
    return nouvelle


@app.get("/recommandations/{session_id}", response_model=List[schemas.AnnonceRecommandee], tags=["Recommandation"])
def obtenir_recommandations(
    session_id: str,
    n: int = Query(6, ge=1, le=20),
    db: Session = Depends(get_db),
):
    """Renvoie jusqu'à n annonces recommandées pour ce visiteur. Si aucun
    historique n'existe encore, renvoie les annonces les plus récentes
    (stratégie de démarrage à froid, cf. conception 7.5)."""
    utilisateur = db.query(models.Utilisateur).filter(models.Utilisateur.session_id == session_id).first()
    if utilisateur is None:
        resultats = recommandation.generer_recommandations(db, utilisateur_id=-1, n=n)
    else:
        resultats = recommandation.generer_recommandations(db, utilisateur.id, n=n)

    sortie = []
    for r in resultats:
        annonce_out = schemas.AnnonceRecommandee(**schemas.AnnonceOut.model_validate(r["annonce"]).model_dump(), score=r["score"])
        sortie.append(annonce_out)
    return sortie


@app.delete("/utilisateurs/{session_id}/donnees", status_code=204, tags=["Recommandation"])
def supprimer_donnees_utilisateur(session_id: str, db: Session = Depends(get_db)):
    """Droit à l'effacement (RGPD art. 17) : supprime toutes les interactions
    et préférences liées à ce visiteur. Voir conception, section 8.7."""
    utilisateur = db.query(models.Utilisateur).filter(models.Utilisateur.session_id == session_id).first()
    if utilisateur is None:
        return None
    db.query(models.Interaction).filter(models.Interaction.utilisateur_id == utilisateur.id).delete()
    db.query(models.Preference).filter(models.Preference.utilisateur_id == utilisateur.id).delete()
    db.delete(utilisateur)
    db.commit()
    return None


# ==================== INITIALISATION D'UN COMPTE ADMIN (développement) ====================

@app.on_event("startup")
def creer_admin_par_defaut():
    """En développement uniquement : crée un compte administrateur par défaut
    s'il n'en existe aucun, pour pouvoir tester les endpoints protégés.
    Mot de passe personnalisable via ADMIN_PASSWORD. À DÉSACTIVER en production
    (ou à changer immédiatement le mot de passe généré)."""
    db = next(get_db())
    if db.query(models.Agent).count() == 0:
        mot_de_passe = os.getenv("ADMIN_PASSWORD", "changeme123456")
        admin = models.Agent(
            nom_utilisateur="admin",
            mot_de_passe_hache=auth.hacher_mot_de_passe(mot_de_passe),
            est_administrateur=1,
        )
        db.add(admin)
        db.commit()
        print(f"[init] Compte administrateur créé : admin / {mot_de_passe} — à changer en production.")
