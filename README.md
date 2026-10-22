# TGCA SARL.AU — Construction au Maroc

Site professionnel TGCA pour la construction de villas, immeubles, appartements et résidences, développé par Beyond Expertise.

## Versions disponibles

- **Vitrine autonome :** [index.html](./index.html), HTML avec les images 3D et les présentations BTP. Un CDN peut afficher cette page sans back-end, mais son formulaire de démonstration ne stocke aucun prospect.
- **Véritable site full-stack :** [fullstack/](./fullstack) — FastAPI, templates, interface d'administration, portail client sécurisé, formulaires enregistrés en SQLite, galerie administrable et images webp optimisées.
- **API légère alternative :** [backend/](./backend) — API distincte de réception des leads, lorsqu'on souhaite conserver un front-end statique.
- **Render Blueprint :** [render.yaml](./render.yaml) — déploiement de démonstration gratuit du site full-stack.
- **Tests :** [fullstack/tests/](./fullstack/tests) et workflow « Vérification du site TGCA ».

## Exécuter le site complet localement

~~~bash
cd fullstack
python -m pip install -r requirements.txt
cp .env.example .env
# Remplacer la valeur SESSION_SECRET dans .env par une clé aléatoire
python scripts/create_admin.py
python -m uvicorn app:app --reload
~~~

Ouvrir http://127.0.0.1:8000 et consulter [la documentation](./fullstack/README.md).

## Hébergement

GitHub Pages nécessite son activation dans Settings > Pages ; il n'est pas activé via l'intégration. Render prend en charge un service Python gratuit de démonstration, mais **le stockage SQLite du plan gratuit Render est éphémère** : comptes, fichiers et devis peuvent être effacés lors des mises en veille ou redéploiements. Avant une exploitation commerciale, configurer une base persistante, SMTP, sauvegardes et secrets de production.

**Important :** les images des villas, riads, immeubles et appartements sont des illustrations 3D, et non des réalisations certifiées de TGCA. Aucun logo d'entreprise tierce n'est présenté comme client sans validation.

## Coordonnées TGCA

N° 520, Route de Kénitra, Km 7, Salé, Maroc · 05 37 89 60 70 · 06 61 25 85 15.
