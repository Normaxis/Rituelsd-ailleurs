# Roadmap — Ritual Manager

## Phase 0 — Stabilisation technique

Objectif : rendre la base propre avant de développer les modules métier.

- [x] Ajouter un `.gitignore` ;
- [x] Préparer la configuration par variables d’environnement ;
- [x] Supprimer le point d’entrée `app.py` pour éviter le conflit avec le package `app/` ;
- [x] Ajouter un point d’entrée `wsgi.py` ;
- [x] Ajouter la documentation d’architecture ;
- [ ] Passer le dépôt en privé ;
- [ ] Retirer les fichiers déjà versionnés qui ne devraient pas l’être (`__pycache__`, base SQLite, instance locale) ;
- [ ] Déplacer les données de démonstration dans un module dédié ;
- [ ] Ajouter Flask-Migrate.

## Phase 1 — Authentification et droits

- Connexion unique ;
- Gestion des rôles ;
- Gestion des utilisateurs ;
- Droits par institut ;
- Redirection selon rôle ;
- Changement de mot de passe ;
- Journalisation des connexions.

## Phase 2 — Site public

- Accueil premium ;
- Pages instituts ;
- Pages prestations ;
- Équipe ;
- Contact ;
- FAQ ;
- Design responsive moderne.

## Phase 3 — Réservation client professionnelle

Parcours cible :

1. Choix de la prestation ;
2. Calendrier mensuel ;
3. Sélection d’un jour disponible ;
4. Choix de l’horaire ;
5. Informations client ;
6. Confirmation.

Le moteur doit vérifier : planning réel, ILU minimum `L`, cabine compatible et absence de chevauchement.

## Phase 4 — Planning professionnel

- Vue jour ;
- Vue semaine ;
- Vue ressources ;
- Planning personnel ;
- Planning cabines ;
- Absences ;
- Congés ;
- Échanges de jours ;
- Samedis tournants ;
- Formations ;
- Indisponibilités cabine.

## Phase 5 — ILU général

- Tableau salariés x prestations ;
- Cellules modifiables ;
- Légende claire ;
- Filtre par institut ;
- Filtre par catégorie ;
- Sauvegarde rapide ;
- Liaison directe avec la réservation.

## Phase 6 — Prestations et cabines

- CRUD complet prestations ;
- CRUD complet cabines ;
- Compatibilités prestation/cabine ;
- Images prestations ;
- Durées, prix, catégories ;
- Statut actif/inactif.

## Phase 7 — Stocks

- Produits ;
- Fournisseurs ;
- Entrées/sorties ;
- Inventaires ;
- Seuils d’alerte ;
- Consommation moyenne par prestation ;
- Déduction automatique après rendez-vous réalisé.

## Phase 8 — Routines type Fabriq

- QR code cabine ;
- Checklist ;
- Photos ;
- Commentaires ;
- Rapport ;
- Historique ;
- Anomalies ;
- Signature par utilisateur connecté.

## Phase 9 — CRM client

- Fiche client ;
- Historique rendez-vous ;
- Préférences ;
- Contre-indications ;
- Notes internes ;
- Espace client ;
- Annulation/modification selon règles.

## Phase 10 — Pilotage entreprise

- Tableau de bord global ;
- CA par institut ;
- Taux de remplissage ;
- Occupation cabines ;
- Stocks bas ;
- Routines non réalisées ;
- Habilitations à renouveler ;
- Exports.
