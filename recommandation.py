"""
Moteur de recommandation — filtrage basé sur le contenu.
Voir dossier de conception, section 6 (diagramme d'activité, formule de score).

Principe : à partir des interactions passées d'un utilisateur (vues, favoris,
contacts), on construit un profil implicite (ville, budget moyen, type de
transaction dominant, surface moyenne), puis on note chaque annonce non
encore vue selon sa ressemblance avec ce profil.
"""

from collections import Counter
from typing import List
from sqlalchemy.orm import Session

import models

SEUIL_MINIMAL = 0.15  # score en dessous duquel une annonce n'est pas retenue

# Poids de chaque critère dans le score final (doivent sommer à 1.0)
POIDS_VILLE = 0.4
POIDS_TRANSACTION = 0.3
POIDS_PRIX = 0.2
POIDS_SURFACE = 0.1


def construire_profil(db: Session, utilisateur_id: int) -> dict:
    """Construit le profil implicite d'un utilisateur à partir de ses interactions."""
    interactions = (
        db.query(models.Interaction)
        .filter(models.Interaction.utilisateur_id == utilisateur_id)
        .all()
    )
    if not interactions:
        return None

    villes = Counter()
    transactions = Counter()
    prix_ponderes, poids_totaux = 0.0, 0.0
    surfaces_ponderees = 0.0
    annonces_vues_ids = set()

    for inter in interactions:
        annonce = inter.annonce
        if annonce is None:
            continue
        annonces_vues_ids.add(annonce.id)
        villes[annonce.ville] += inter.poids
        transactions[annonce.type_transaction] += inter.poids
        prix_ponderes += annonce.prix * inter.poids
        surfaces_ponderees += annonce.surface_m2 * inter.poids
        poids_totaux += inter.poids

    if poids_totaux == 0:
        return None

    return {
        "ville_dominante": villes.most_common(1)[0][0] if villes else None,
        "transaction_dominante": transactions.most_common(1)[0][0] if transactions else None,
        "budget_moyen": prix_ponderes / poids_totaux,
        "surface_moyenne": surfaces_ponderees / poids_totaux,
        "annonces_vues_ids": annonces_vues_ids,
    }


def calculer_score(annonce: models.Annonce, profil: dict) -> float:
    """Calcule le score de similarité d'une annonce avec le profil (0 à 1)."""
    score = 0.0

    if profil["ville_dominante"] and annonce.ville == profil["ville_dominante"]:
        score += POIDS_VILLE

    if profil["transaction_dominante"] and annonce.type_transaction == profil["transaction_dominante"]:
        score += POIDS_TRANSACTION

    budget_moyen = profil["budget_moyen"]
    if budget_moyen:
        ecart_prix = abs(annonce.prix - budget_moyen) / budget_moyen
        score += POIDS_PRIX * max(0, 1 - ecart_prix)

    surface_moyenne = profil["surface_moyenne"]
    if surface_moyenne:
        ecart_surface = abs(annonce.surface_m2 - surface_moyenne) / surface_moyenne
        score += POIDS_SURFACE * max(0, 1 - ecart_surface)

    return round(score, 3)


def generer_recommandations(db: Session, utilisateur_id: int, n: int = 6) -> List[dict]:
    """Renvoie jusqu'à n annonces recommandées, chacune avec son score.
    Stratégie de démarrage à froid : si l'utilisateur n'a pas encore
    d'historique, renvoie simplement les annonces les plus récentes."""
    profil = construire_profil(db, utilisateur_id)

    if profil is None:
        recentes = (
            db.query(models.Annonce)
            .order_by(models.Annonce.cree_le.desc())
            .limit(n)
            .all()
        )
        return [{"annonce": a, "score": 0.0} for a in recentes]

    candidates = (
        db.query(models.Annonce)
        .filter(~models.Annonce.id.in_(profil["annonces_vues_ids"]))
        .all()
    )

    notees = []
    for annonce in candidates:
        score = calculer_score(annonce, profil)
        if score > SEUIL_MINIMAL:
            notees.append({"annonce": annonce, "score": score})

    notees.sort(key=lambda x: x["score"], reverse=True)
    return notees[:n]
