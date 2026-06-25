# Rituels d'Ailleurs — Ritual Manager

Base propre pour le logiciel métier : **site public + réservation client + ERP interne**.

## Objectif

Créer une plateforme unique pour gérer :

- Rituels d’Ailleurs ;
- Le Petit Rituel.

Le logiciel doit couvrir le site public, la réservation, le planning, les compétences ILU, les cabines, les stocks, les routines terrain et le pilotage de l’entreprise.

## Lancement local

```bash
pip install -r requirements.txt
python run.py
```

Puis ouvrir :

```text
http://127.0.0.1:5000
```

## Identifiants de démonstration

Les comptes de démonstration sont créés automatiquement au premier lancement de la base locale.

## Modules inclus actuellement

- Site public ;
- Connexion unique ;
- Rôles utilisateurs ;
- Prestations ;
- Cabines ;
- Planning daté ;
- ILU général ;
- Réservation client : prestation → calendrier mensuel → créneaux ;
- Stocks ;
- Routines type Fabriq ;
- Journal d’audit.

## Documentation

- `docs/ARCHITECTURE.md` : architecture technique et métier ;
- `docs/ROADMAP.md` : plan de réalisation du projet.

## Commandes Git utiles

```powershell
git status
git add .
git commit -m "Message clair du changement"
git push
```

## Notes de sécurité

Le dépôt doit rester privé avant d’ajouter des données réelles, des fichiers clients ou des clés de production.

Les fichiers suivants ne doivent pas être versionnés :

- `.env` ;
- `instance/` ;
- bases SQLite ;
- `__pycache__/` ;
- uploads locaux.
