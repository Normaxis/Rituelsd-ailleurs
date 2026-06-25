# Architecture — Ritual Manager

## Objectif

Le projet doit évoluer vers une application métier complète pour gérer deux instituts :

- Rituels d’Ailleurs ;
- Le Petit Rituel.

L’application regroupe deux parties :

1. **Site public** : présentation, prestations, réservation, contact.
2. **ERP interne** : planning, ILU, cabines, stocks, routines, utilisateurs, audit.

## Arborescence cible

```text
app/
├── auth/          # Connexion, déconnexion, sessions
├── public/        # Pages publiques
├── booking/       # Parcours de réservation client
├── admin/         # Dashboard et administration générale
├── planning/      # Planning réel daté du personnel et des cabines
├── ilu/           # Matrice ILU salariés x prestations
├── stocks/        # Produits, mouvements, seuils d’alerte
├── routines/      # Routines type Fabriq, QR codes, rapports
├── models/        # Modèles SQLAlchemy
├── services/      # Logique métier réutilisable
├── utils/         # Décorateurs, helpers, sécurité
├── templates/     # Templates Jinja
└── static/        # CSS, JS, images, uploads
```

## Principe de routing

Les routes sont séparées par blueprint :

- `/` : site public ;
- `/auth` : connexion ;
- `/reservation` : réservation client ;
- `/admin` : ERP interne ;
- `/admin/planning` : planning ;
- `/admin/ilu` : compétences ILU ;
- `/admin/stocks` : stocks ;
- `/admin/routines` : routines.

## Règles métier essentielles

### Réservation

Un créneau client ne peut être proposé que si :

- la prestation est active ;
- une praticienne travaille réellement ce jour-là ;
- la praticienne possède un niveau ILU `L` ou `U` ;
- une cabine compatible est libre ;
- aucun rendez-vous ne chevauche le créneau ;
- la durée de la prestation rentre dans le planning.

### ILU

- Vide : la salariée ne connaît pas la prestation ;
- `I` : initiée, non réservable ;
- `L` : autonome, réservable ;
- `U` : experte, réservable.

### Droits

- Administratrice générale : tous les instituts, tous les modules ;
- Responsable d’institut : uniquement son institut ;
- Accueil : clients, réservations, planning opérationnel ;
- Praticienne : son planning, ses routines, ses formations.

## Évolutions techniques prévues

- Ajouter Flask-Migrate pour gérer les évolutions de base ;
- Isoler les données de démonstration dans un module dédié ;
- Ajouter des services métier pour la réservation, les stocks et l’audit ;
- Ajouter des tests automatisés ;
- Préparer PostgreSQL pour la production.
