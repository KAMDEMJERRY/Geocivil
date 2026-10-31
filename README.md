# GéoCivil – API (étape 1 : socle)

FastAPI + PostgreSQL. Comptes (email + mot de passe, JWT), projets maison R+0 à R+2,
prix par ville (admin) avec ajustement par utilisateur. Normes visées : BAEL.

## Lancer en local
    cp .env.example .env        # puis éditer SECRET_KEY et ADMIN_EMAIL
    docker compose up --build   # API sur http://localhost:8000/docs

## Tests
    cd backend && python -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
    .venv/bin/python -m pytest -q

## Déployer sur Render
Pousser le dépôt sur GitHub, puis Render > New > Blueprint. Renseigner ADMIN_EMAIL
et CORS_ORIGINS (URL du futur frontend). Le compte créé avec ADMIN_EMAIL devient admin.

## Principaux endpoints
POST /auth/register, /auth/login · GET /auth/me · CRUD /projects ·
GET /prices?city= · PUT/DELETE /prices/overrides · PUT /admin/prices · POST /admin/price-items

## Moteur BAEL (étape 2)
POST /projects/{id}/analysis calcule et enregistre dalles, poutres, poteaux, semelles (ferraillage + ELS, flèche, fissuration, poinçonnement) ; GET renvoie la dernière analyse. Hypothèses listées dans la réponse.

## Prochaine étape
Métrés, devis Excel et rapport PDF (étapes 3 et 4).
# Geocivil
# Geocivil
