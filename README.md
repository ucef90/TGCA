# TGCA SARL.AU — Site de présentation

Site vitrine TGCA, entreprise de construction au Maroc (immeubles, appartements, villas, bâtiments).

## Ouvrir immédiatement la vitrine via un CDN gratuit
https://rawcdn.githack.com/ucef90/TGCA/81f7cc994b91317a5a820c3b5f7c9ca9cdbbbf45/index.html

Ce lien affiche le HTML présent dans GitHub grâce à raw.githack, sans configuration GitHub Pages. Ce n'est pas un hébergement applicatif et le contenu est figé sur cette version. Les formulaires restent des démonstrations.

## Version en ligne (GitHub Pages)
Une fois GitHub Pages activé dans **Settings > Pages > Build and deployment > Source: GitHub Actions**, le site sera accessible à :
https://ucef90.github.io/TGCA/

L'action `.github/workflows/deploy-pages.yml` déploie les mises à jour automatiquement. Vérifier l'onglet **Actions** et **Settings > Pages** pour confirmer le succès.

## Notes importantes
- Il s'agit du site vitrine statique, avec formulaire de devis de démonstration : aucune demande n'est transmise.
- L'administration, la base SQLite et l'espace client nécessitent le déploiement séparé du serveur Python FastAPI, absent de cette version statique.
- Les photos représentent des illustrations, pas des réalisations vérifiées de TGCA.
- Les contenus métier et mentions légales doivent être approuvés avant publication commerciale définitive.

Développement initial : Beyond Expertise Maroc.
