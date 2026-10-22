# TGCA SARL.AU — Site web BTP & portail de suivi

**Projet développé pour TGCA SARL.AU (Maroc)**. Identité visuelle bleu marine et or, site vitrine responsive, back-office sécurisé, demandes de devis et espace client de suivi de projets.

## Fonctionnalités livrées

| Public | Administration | Espace client |
|---|---|---|
| Accueil, entreprise, expertises BTP | Consultation des devis et contacts | Projets affectés uniquement |
| Galerie filtrable de concepts et projets | Statuts des demandes | Avancement (%) et états |
| Fiches détaillées | Création et modification des projets | Tâches et jalons |
| Formulaire de devis enregistré en SQLite | Gestion des comptes clients | Documents à télécharger |
| Téléphone, adresse et carte | Ajout de tâches et documents | Connexion sécurisée |
| SEO, sitemap, métadonnées, données structurées | Ajout de projets à la galerie avec photos | Protection des fichiers par compte |

Les images livrées avec le site sont des **illustrations architecturales** ; elles **ne prouvent pas** que TGCA a construit ces ouvrages. Les références réelles doivent être validées puis ajoutées via l'administration. Aucun chiffre de réalisations, chiffre d'affaires, nombre de clients ou durée d'expérience n'a été inventé.

## Démarrage local rapide

**Pré-requis :** Python 3.11 ou plus récent.

### Mac / Linux

```bash
cd TGCA-site-web
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Remplacer `SESSION_SECRET` dans `.env` par la valeur générée, puis :

```bash
python scripts/create_admin.py
uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```

### Windows (PowerShell)

```powershell
cd TGCA-site-web
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Coller le secret généré dans `.env`, puis :

```powershell
python scripts/create_admin.py
python -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```

Ouvrir **http://127.0.0.1:8000**. Les accès se trouvent sur `/connexion`, `/admin` et `/espace-client`.

## Utiliser l'administration

1. Créer votre **compte administrateur** avec `python scripts/create_admin.py`.
2. Se connecter sur `/connexion`.
3. Consulter les messages entrants dans **Demandes** : le formulaire public enregistre automatiquement les demandes.
4. Créer un **compte client** (avec mot de passe robuste de 12 caractères au minimum).
5. Créer un **projet**, l'affecter au client, définir son statut et son avancement.
6. Ajouter des **tâches** et des **documents** à partir de la fiche projet.
7. Le client voit exclusivement ses propres projets depuis son espace client.
8. Dans **Galerie**, créer des contenus avec une image illustrative ou une photo réelle, et masquer/publier les fiches.

Une notification e-mail des devis est **facultative** : elle nécessite un serveur SMTP configuré. Sans SMTP, aucune demande n'est perdue : elles restent accessibles dans le back-office.

## Déploiement avec Docker

Installer Docker / Docker Compose, copier `.env.example` vers `.env`, **remplacer `SESSION_SECRET` par un secret robuste**, configurer `SITE_URL` avec l'URL finale. Puis :

```bash
docker compose up -d --build
# Création du compte administrateur dans le conteneur :
docker compose exec tgca python scripts/create_admin.py
```

Les données SQLite et fichiers sont persistés dans le volume `tgca_data`. Pour un site public, placer un reverse-proxy TLS/HTTPS devant le service ; ne pas exposer directement un serveur de développement sur Internet.

## Configuration (.env)

| Paramètre | Description |
|---|---|
| `SESSION_SECRET` | Secret de signature des sessions (obligatoire en production) |
| `ENVIRONMENT=production` | Cookies HTTPS et HSTS, exigence d'un secret |
| `SITE_URL` | URL absolue du site (utilisée dans le sitemap) |
| `TGCA_DATA_DIR` | Dossier SQLite et fichiers |
| `ALLOWED_HOSTS` | Liste de domaines autorisés, séparés par des virgules |
| `NOTIFICATION_EMAIL` | Adresse destinataire des formulaires |
| `SMTP_HOST`, `SMTP_PORT` | Serveur mail (optionnel) |
| `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` | Identifiants et expéditeur SMTP |

## Structure du projet

```text
TGCA-site-web/
├── app.py                   Application FastAPI, services et routes
├── templates/               Pages publiques et privées en Jinja2
├── static/css/style.css     Design responsive
├── static/js/main.js        Menu mobile et interactions
├── static/img/              Logos SVG et images d'illustration locales
├── scripts/create_admin.py  Création d'un administrateur
├── tests/test_app.py        Tests HTTP, base, permissions et sécurité
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

**La base SQLite est créée automatiquement** dans `data/tgca.db` au premier lancement. Les fichiers importés sont stockés dans `data/uploads/` et `data/public_media/`. Le dossier `data/` n'est pas fourni prérempli pour ne pas diffuser de données privées.

## Sécurité déjà en place

- Mot de passe haché avec PBKDF2-SHA256 et sel aléatoire.
- Session signée, cookie SameSite et Secure en HTTPS/prod.
- Protection CSRF des formulaires, y compris administratifs.
- Autorisation côté serveur (administrateur/client) ; isolation des documents et projets par client.
- Restriction et vérification des types de fichiers importés ; tailles limitées.
- Anti-spam formulaire (champ piège + limitation de fréquence), limitation des tentatives de connexion.
- Requêtes SQL paramétrées, échappement HTML par moteur de templates.
- En-têtes de sécurité HTTP, CSP avec nonce et mode production HTTPS.

**Avant une mise en production publique**, faire valider l'application par le client, réaliser une revue de sécurité, configurer les sauvegardes, les journaux, la supervision et une politique effective de conservation des données. Faire les vérifications nécessaires au titre de la loi marocaine 09-08 et des éventuelles formalités CNDP. En cas de montée en charge importante, prévoir une migration de SQLite vers PostgreSQL.

## Contenus à confirmer avant publication

- Domaine internet et fournisseur d'hébergement.
- Logo officiel définitivement approuvé.
- Photos de projets réels et autorisations de publication.
- Textes exacts sur les activités (ne pas annoncer des métiers non exercés).
- Mention de l'hébergeur, durée de conservation et procédure de contact confidentialité.
- Adresse email officielle et paramètres SMTP si notifications souhaitées.
- Références, chiffres et labels réels, si souhaités.

## Tests

```bash
python -m pytest -q tests/test_app.py
```

Dans l'environnement de création, 17 tests automatisés ont réussi le 22 octobre 2026 ; les tests peuvent être relancés après installation de `pytest` et `httpx` pour un environnement vierge :

```bash
pip install pytest httpx
```

## Crédit de production

Développement demandé par Beyond Expertise Maroc pour TGCA SARL.AU. **La marque visible sur le site est TGCA**, pas Beyond Expertise. Aucun contenu de facture ni RIB n'est publié sur le site.

## Collection d'inspirations architecturales 2026

Les nouvelles images 3D (riad, villas, immeubles et appartements) sont intégrées à la vitrine, à la galerie et aux services ; elles sont des **illustrations** et ne peuvent être présentées comme des réalisations réelles de TGCA. Aucun logo de société tierce n'a été affiché en tant que client sans validation écrite du lien commercial.

## Attention au plan d'hébergement gratuit

Un plan gratuit Render sans disque persistant **ne permet pas de conserver de manière fiable les demandes enregistrées dans SQLite** : les données peuvent disparaître lors d'un redémarrage, d'un déploiement ou d'une mise en veille. Pour la mise en production du formulaire, utiliser un service avec stockage SQL persistant et sauvegardes, et configurer SMTP. La vitrine statique est disponible indépendamment sur GitHub ; le portail client sécurisé nécessite un serveur Python en fonctionnement.
