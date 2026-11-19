from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, ConfigDict, Field

from models import TypeTransaction, TypeInteraction


# ---------- Annonces ----------

class AnnonceBase(BaseModel):
    reference: str
    titre: str
    ville: str
    type_transaction: TypeTransaction
    prix: float
    surface_m2: float
    chambres: int = 0
    description: str = ""


class AnnonceCreate(AnnonceBase):
    pass


class AnnonceUpdate(BaseModel):
    titre: Optional[str] = None
    ville: Optional[str] = None
    type_transaction: Optional[TypeTransaction] = None
    prix: Optional[float] = None
    surface_m2: Optional[float] = None
    chambres: Optional[int] = None
    description: Optional[str] = None


class AnnonceOut(AnnonceBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    cree_le: datetime


class AnnonceRecommandee(AnnonceOut):
    """Une annonce enrichie de son score de similarité (0 à 1)."""
    score: float


# ---------- Contact ----------

class MessageContactCreate(BaseModel):
    nom: str
    email: EmailStr
    message: str


class MessageContactOut(MessageContactCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    envoye_le: datetime


# ---------- Authentification (agents / back-office) ----------

class AgentCreate(BaseModel):
    nom_utilisateur: str
    mot_de_passe: str = Field(min_length=12, description="12 caractères minimum")


class AgentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nom_utilisateur: str
    est_administrateur: bool


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    nom_utilisateur: Optional[str] = None


# ---------- Recommandation ----------

class InteractionCreate(BaseModel):
    utilisateur_session_id: str
    annonce_id: int
    type: TypeInteraction


class InteractionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    utilisateur_id: int
    annonce_id: int
    type: TypeInteraction
    poids: float
    horodatage: datetime


class PreferenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    ville_preferee: Optional[str] = None
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    type_transaction_prefere: Optional[TypeTransaction] = None
