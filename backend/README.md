# Backend de réception des devis TGCA

API FastAPI pour la réception des demandes du site vitrine.

## Installer en local

\`\`\`bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export TGCA_ADMIN_TOKEN="$(python -c 'import secrets;print(secrets.token_urlsafe(40))')"
uvicorn app:app --reload
\`\`\`

## API

- \`GET /api/health\` — statut
- \`POST /api/devis\` — enregistrement d'une demande (nom, email, téléphone, type de projet, ville, budget, message, consentement)
- \`GET /api/admin/leads\` — liste des demandes, en envoyant l'en-tête \`X-TGCA-Admin-Token\`
- \`PATCH /api/admin/leads/{id}\` — modification du statut (même en-tête)

Le fichier \`.env.example\` décrit les variables d'environnement ; elles doivent être déclarées dans l'hébergeur ou chargées avant le lancement du processus. Ne jamais committer les secrets réels.

## Mise en ligne : limites importantes

Le Blueprint \`render.yaml\` prépare le service sur le plan gratuit Render. **Il n'est pas encore déployé.** L'activation nécessite une connexion Render appartenant à TGCA / Beyond Expertise.

**Render Free supprime les fichiers locaux lors des mises en veille, redémarrages ou redéploiements.** La base SQLite ne constitue donc pas une conservation fiable des devis sur cette offre : n'utiliser ce déploiement que pour démonstration. Pour de vrais prospects, configurer un stockage SQL persistant (PostgreSQL managé) et les notifications SMTP avant de le rendre public. Ne jamais publier le jeton administrateur.

Le site vitrine sur GitHub est autonome et reste en **mode démonstration** tant que l'URL du backend n'a pas été configurée.

Le projet complet FastAPI avec l'interface d'administration et le portail client est conservé dans l'archive de livraison séparée.
