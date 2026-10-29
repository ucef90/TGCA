# Journal des modifications — TGCA SARL.AU

## 29 octobre 2026 — Nouvelles coordonnées
- Coordonnées remplacées partout : **06 63 22 43 22** et **ste.tgca@gmail.com** (anciens 05 37 89 60 70 et 06 61 25 85 15 retirés).
- WhatsApp sur le 212 663 22 43 22.
- Coordonnées centralisées dans `app.py` (`CONTACT`, modifiables par `CONTACT_PHONE`, `CONTACT_TEL`, `CONTACT_EMAIL`).
- Demandes de devis notifiées par défaut à ste.tgca@gmail.com (si SMTP configuré), avec « Répondre à » = e-mail du prospect.
- Vitrine GitHub Pages : le formulaire de devis envoie réellement les demandes à ste.tgca@gmail.com via FormSubmit.

## 22 octobre 2026 — Correctifs et améliorations

### Sécurité
- **Clé de session faible refusée en production.** Avant, l'application démarrait en production avec la valeur d'exemple `REMPLACER_PAR_UNE_CLE_ALEATOIRE_LONGUE`, ce qui permettait de fabriquer une session administrateur. Désormais : refus de démarrer si la clé est absente, trop courte (< 32 caractères) ou laissée à sa valeur d'exemple.
- Pages privées (connexion, admin, espace client) marquées `noindex` pour les moteurs de recherche.
- Export CSV protégé contre l'injection de formules Excel (`=`, `+`, `-`, `@`).
- `robots.txt` bloque aussi `/documents` et `/mon-compte`.

### Corrections de bugs
- Logo : l'espace parasite entre « TGC » et « A » est supprimé (version claire et foncée).
- Page Entreprise : débordement horizontal sur mobile corrigé.
- Erreurs 403, 404, 429… : page HTML aux couleurs du site au lieu du texte brut `{"detail":"Not Found"}`.
- Formulaire de devis : en cas d'erreur, la saisie est conservée, chaque champ fautif est signalé et reçoit le focus (avant, tout était effacé avec un message général).
- `robots.txt` et balise `canonical` : URL absolues basées sur `SITE_URL`.

### Site public
- En-tête fixe au défilement.
- Mobile : barre d'actions en bas d'écran (« Appeler » + « Demander un devis »).
- Bouton WhatsApp : bouton flottant sur ordinateur, bouton dans la barre d'actions sur mobile. Réglable via `WHATSAPP_NUMBER`.
- Accueil allégé : suppression de la 2e section « 4 étapes » (doublon) et du 2e bloc « Demander un devis » consécutif.
- Cartes « expertises » entièrement cliquables.
- Bandeau final avec le numéro de téléphone cliquable.
- SEO : données structurées FAQ (accueil), `og:url`, `og:site_name`, image Open Graph absolue, préchargement de l'image d'accueil.
- Page Plans 3D : suppression du double appel à l'action.

### Nouvelles images (22/10/2026)
- 6 nouveaux rendus 3D intégrés (WebP optimisés, 1600 px) : villa vue Atlas, riad à patio, villa en palmeraie, résidence en travertin, résidence aux jardins en cascade, maquette 3D d'une villa à patio.
- Utilisés sur l'accueil (collection architecturale), les expertises, l'entreprise, le contact, la connexion et la page Plans 3D (maquette mise en avant).
- Galerie : 6 fiches d'inspiration ajoutées une seule fois (une suppression par l'admin reste définitive) et nouvelle catégorie « Riad ».
- Toutes restent signalées comme illustrations conceptuelles.

### Administration
- Demandes : filtres par statut, demandes archivées masquées par défaut, export CSV compatible Excel, messages longs repliables.
- Clients : réinitialisation du mot de passe, suppression de l'accès (les projets sont conservés).
- Projets : suppression d'un projet (tâches et fichiers inclus), suppression d'un document.
- Galerie : suppression d'une fiche (et de sa photo), miniature, lien « Voir », tous les visuels disponibles proposés.
- Journal des 12 dernières actions.
- Bandeau marketing et pied de page complet retirés des espaces privés.

### Espace client
- Changement de son propre mot de passe (`/mon-compte/mot-de-passe`).
- Compteur de tâches terminées, taille et date des documents.

### Tests
- 38 tests automatisés (23 existants + 15 nouveaux couvrant chaque point ci-dessus).
