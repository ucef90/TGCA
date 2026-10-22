# TGCA SARL.AU — Construction au Maroc

Site professionnel TGCA pour la construction de villas, riads, immeubles, appartements et résidences, développé par Beyond Expertise.

## Voir le site

- **Vitrine en ligne (GitHub Pages, gratuite) :** https://ucef90.github.io/TGCA/
  Copie statique des pages publiques. Les formulaires et l'espace client y sont désactivés (un bandeau le signale).

## Contenu du dépôt

- **[fullstack/](./fullstack)** — le vrai site : FastAPI, back-office, espace client sécurisé, demandes de devis enregistrées en SQLite, galerie administrable. Voir [fullstack/README.md](./fullstack/README.md) et [fullstack/CHANGELOG.md](./fullstack/CHANGELOG.md).
- **[site/](./site)** — vitrine statique générée à partir de `fullstack/`, publiée automatiquement sur GitHub Pages à chaque push sur `main`.
- **[backend/](./backend)** — API légère alternative de réception des leads.
- **[render.yaml](./render.yaml)** — déploiement gratuit de démonstration du site complet sur Render.
- **Tests :** `fullstack/tests/` (38 tests), lancés par le workflow « Vérification du site TGCA ».

## Exécuter le site complet localement

~~~bash
cd fullstack
python -m pip install -r requirements.txt
cp .env.example .env
# Remplacer SESSION_SECRET dans .env : python -c "import secrets; print(secrets.token_urlsafe(48))"
python scripts/create_admin.py
python -m uvicorn app:app --reload
~~~

Ouvrir http://127.0.0.1:8000.

## Hébergement

- **GitHub Pages** (vitrine) : si la page n'apparaît pas après le premier push, activer une fois *Settings > Pages > Source : GitHub Actions*, puis relancer le workflow « Publier la vitrine TGCA sur GitHub Pages ».
- **Render** (site complet) : gratuit, mais **le disque du plan gratuit est éphémère** : comptes, fichiers et devis enregistrés en SQLite peuvent être effacés lors des mises en veille ou redéploiements. Avant une exploitation commerciale : base persistante, SMTP, sauvegardes et secrets de production.

**Important :** les images des villas, riads, immeubles et appartements sont des illustrations 3D, et non des réalisations de TGCA.

## Coordonnées TGCA

N° 520, Route de Kénitra, Km 7, Salé, Maroc · 05 37 89 60 70 · 06 61 25 85 15 (WhatsApp).
