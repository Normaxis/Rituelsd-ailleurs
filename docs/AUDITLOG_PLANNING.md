# AuditLog planning

Cette evolution ajoute une trace automatique des actions realisees depuis `/admin/planning`.

## Actions tracees

- Creation d'un rendez-vous depuis le planning.
- Modification ou deplacement d'un rendez-vous depuis le planning.
- Creation d'un creneau praticienne depuis le planning.
- Modification ou deplacement d'un creneau praticienne depuis le planning.

## Fonctionnement technique

Le module `app/audit_hooks.py` ecoute les evenements SQLAlchemy sur :

- `Appointment`
- `WorkSlot`

Les lignes sont ajoutees dans la table existante `AuditLog`, avec :

- `module = planning`
- `user_id` recupere depuis la session
- `action` en texte lisible

## Limitation volontaire

Les hooks n'ecrivent un audit que si la requete vient de `/admin/planning`. Les creations depuis d'autres modules ne sont donc pas encore tracees par cette evolution.
