import enum
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Enum, Text, ForeignKey
)
from sqlalchemy.orm import relationship
from database import Base


class TypeTransaction(str, enum.Enum):
    vente = "vente"
    location = "location"
    commercial = "commercial"


class TypeInteraction(str, enum.Enum):
    vue = "vue"
    favori = "favori"
    contact = "contact"


# Poids par défaut de chaque type d'interaction (voir dossier de conception, 6.5)
POIDS_INTERACTION = {
    TypeInteraction.vue: 1.0,
    TypeInteraction.favori: 3.0,
    TypeInteraction.contact: 5.0,
}


class Annonce(Base):
    __tablename__ = "annonces"

    id = Column(Integer, primary_key=True, index=True)
    reference = Column(String, unique=True, index=True, nullable=False)
    titre = Column(String, nullable=False)
    ville = Column(String, index=True, nullable=False)
    type_transaction = Column(Enum(TypeTransaction), nullable=False)
    prix = Column(Float, nullable=False)
    surface_m2 = Column(Float, nullable=False)
    chambres = Column(Integer, default=0)
    description = Column(Text, default="")
    cree_le = Column(DateTime, default=datetime.utcnow)

    interactions = relationship("Interaction", back_populates="annonce")


class MessageContact(Base):
    __tablename__ = "messages_contact"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String, nullable=False)
    email = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    envoye_le = Column(DateTime, default=datetime.utcnow)


class Agent(Base):
    """Compte permettant de créer/modifier/supprimer des annonces (back-office)."""
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True)
    nom_utilisateur = Column(String, unique=True, index=True, nullable=False)
    mot_de_passe_hache = Column(String, nullable=False)
    est_administrateur = Column(Integer, default=0)  # 0 = agent, 1 = administrateur
    cree_le = Column(DateTime, default=datetime.utcnow)


class Utilisateur(Base):
    """Visiteur du site, suivi via un identifiant de session anonyme
    (voir dossier de conception, 5.3 et 7.4)."""
    __tablename__ = "utilisateurs"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, nullable=True)
    cree_le = Column(DateTime, default=datetime.utcnow)

    interactions = relationship("Interaction", back_populates="utilisateur")
    preference = relationship("Preference", back_populates="utilisateur", uselist=False)


class Interaction(Base):
    """Trace un événement : quel utilisateur a vu / mis en favori / contacté
    quelle annonce, et quand (voir dossier de conception, 5.4)."""
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, index=True)
    utilisateur_id = Column(Integer, ForeignKey("utilisateurs.id"), nullable=False)
    annonce_id = Column(Integer, ForeignKey("annonces.id"), nullable=False)
    type = Column(Enum(TypeInteraction), nullable=False)
    poids = Column(Float, nullable=False)
    horodatage = Column(DateTime, default=datetime.utcnow)

    utilisateur = relationship("Utilisateur", back_populates="interactions")
    annonce = relationship("Annonce", back_populates="interactions")


class Preference(Base):
    """Profil de préférences déduit (ou déclaré) d'un utilisateur
    (voir dossier de conception, 5.5)."""
    __tablename__ = "preferences"

    id = Column(Integer, primary_key=True, index=True)
    utilisateur_id = Column(Integer, ForeignKey("utilisateurs.id"), unique=True, nullable=False)
    ville_preferee = Column(String, nullable=True)
    budget_min = Column(Float, nullable=True)
    budget_max = Column(Float, nullable=True)
    type_transaction_prefere = Column(Enum(TypeTransaction), nullable=True)

    utilisateur = relationship("Utilisateur", back_populates="preference")
