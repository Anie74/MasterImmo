# API Haino et Cie Immobilier

API REST pour gérer les annonces immobilières, les messages de contact, et
les recommandations personnalisées du site Haino et Cie Immobilier.
Construite avec **FastAPI** + **SQLAlchemy**, conforme au dossier de
conception (architecture, UML, sécurité).

## Installation

```bash
pip install -r requirements.txt
```

## Lancer l'API

```bash
uvicorn main:app --reload
```

L'API démarre sur `http://127.0.0.1:8000`. Une base SQLite (`immobilier.db`)
est créée automatiquement, ainsi qu'un **compte administrateur par défaut**
(voir ci-dessous) — pratique pour tester, mais à changer avant toute mise en
production.

## Compte administrateur par défaut

Au premier démarrage, si aucun compte n'existe, l'API crée automatiquement :
- nom d'utilisateur : `admin`
- mot de passe : `changeme123456` (ou la valeur de la variable `ADMIN_PASSWORD`)

```bash
export ADMIN_PASSWORD="un-mot-de-passe-robuste-a-toi"
uvicorn main:app --reload
```

⚠️ **Ne jamais laisser le mot de passe par défaut en production.**

## Documentation interactive

- **http://127.0.0.1:8000/docs** — Swagger UI, teste chaque endpoint directement
- **http://127.0.0.1:8000/redoc** — documentation en lecture seule

## Authentification (endpoints protégés)

1. Se connecter pour obtenir un jeton :
```bash
curl -X POST http://127.0.0.1:8000/token \
  -d "username=admin&password=TonMotDePasse"
```
2. Utiliser ce jeton dans les requêtes suivantes :
```bash
curl -X POST http://127.0.0.1:8000/annonces \
  -H "Authorization: Bearer <jeton_recu>" \
  -H "Content-Type: application/json" \
  -d '{...}'
```
Le jeton est valide 1 heure.

## Endpoints

### Annonces

| Méthode | Route              | Accès              | Description |
|---------|---------------------|---------------------|--------------|
| GET     | `/annonces`          | Public              | Liste (filtres : `ville`, `type_transaction`, `prix_max`) |
| GET     | `/annonces/{id}`     | Public              | Détail d'une annonce |
| POST    | `/annonces`          | Agent/Admin (JWT)   | Créer une annonce |
| PUT     | `/annonces/{id}`     | Agent/Admin (JWT)   | Modifier une annonce |
| DELETE  | `/annonces/{id}`     | Agent/Admin (JWT)   | Supprimer une annonce |

### Contact

| Méthode | Route      | Accès                          | Description |
|---------|------------|----------------------------------|--------------|
| POST    | `/contact` | Public (5 requêtes/minute/IP)   | Enregistrer un message |
| GET     | `/contact` | Agent/Admin (JWT)                | Lister les messages reçus |

### Recommandation

| Méthode | Route                              | Accès   | Description |
|---------|--------------------------------------|---------|--------------|
| POST    | `/interactions`                      | Public  | Enregistrer une vue/favori/contact |
| GET     | `/recommandations/{session_id}?n=6`  | Public  | Annonces recommandées pour ce visiteur |
| DELETE  | `/utilisateurs/{session_id}/donnees` | Public  | Suppression des données (droit RGPD à l'effacement) |

Le moteur de recommandation (`recommandation.py`) utilise un filtrage basé
sur le contenu : il compare le profil implicite du visiteur (ville, budget,
type de transaction dominants dans son historique) avec chaque annonce non
encore vue, et retient celles dont le score dépasse un seuil minimal. Sans
historique, il renvoie les annonces les plus récentes (démarrage à froid).

## Passer à PostgreSQL

```bash
export DATABASE_URL="postgresql://utilisateur:motdepasse@localhost:5432/immobilier"
pip install psycopg2-binary
uvicorn main:app --reload
```

## Variables d'environnement

| Variable | Rôle | Défaut |
|----------|------|--------|
| `DATABASE_URL` | Connexion à la base de données | SQLite local |
| `JWT_SECRET_KEY` | Clé de signature des jetons — **à définir en production** | clé de développement (non sûre) |
| `ADMIN_PASSWORD` | Mot de passe du compte admin créé au démarrage | `changeme123456` |
| `ORIGINES_AUTORISEES` | Domaine(s) autorisés à appeler l'API (CORS), séparés par des virgules | `*` (tout autoriser — dev uniquement) |

## Sécurité — à faire avant mise en production

Voir le dossier de conception (section Sécurité) pour le détail complet.
Résumé :
- [ ] Définir `JWT_SECRET_KEY` avec une valeur longue et aléatoire
- [ ] Définir `ORIGINES_AUTORISEES` avec le domaine exact du site
- [ ] Changer le mot de passe du compte admin
- [ ] Activer HTTPS (automatique chez la plupart des hébergeurs recommandés)
- [ ] Passer à PostgreSQL avec sauvegardes automatiques

## Connecter le site web (index.html)

Le site est déjà connecté : il appelle `/annonces`, `/contact`,
`/interactions` et `/recommandations/{session_id}` via la constante
`API_URL` définie en haut du `<script>`. En production, remplace-la par
l'URL réelle de l'API déployée.

## Déploiement

- **Render** (render.com) — déploiement direct depuis un dépôt GitHub
- **Railway** (railway.app) — idem, avec base PostgreSQL incluse
- **Fly.io** — bon support de PostgreSQL

## Structure du projet

```
api/
├── main.py            # Endpoints de l'API
├── models.py            # Tables de la base de données
├── schemas.py            # Validation des données (Pydantic)
├── database.py            # Connexion à la base de données
├── auth.py                # Authentification JWT, hachage des mots de passe
├── recommandation.py        # Moteur de recommandation (scoring)
├── requirements.txt
└── README.md
```