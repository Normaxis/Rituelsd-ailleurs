# Avancement du module planning

## Pourcentage estime : 84 %

Le module planning dispose maintenant d'une base solide pour une pre-production controlee.

## Termine ou fortement avance

- Affichage jour par praticiennes.
- Affichage jour par cabines.
- Creation de rendez-vous depuis le planning.
- Deplacement drag-and-drop avec verification serveur.
- Protection CSRF sur les formulaires planning et l'API de deplacement.
- Droits de modification limites aux roles `general_admin` et `agency_manager`.
- Lecture seule pour les autres roles.
- Filtrage par etablissement pour les utilisateurs non `general_admin`.
- Verification de disponibilite praticienne.
- Verification de disponibilite cabine.
- Cabine consideree indisponible si aucune disponibilite n'est renseignee.
- Verification ILU L/U de la praticienne pour la prestation.
- Verification de coherence etablissement entre prestation, praticienne et cabine.
- Blocage de l'ecrasement du planning si des rendez-vous actifs existent deja.
- Champ `Appointment.note` ajoute au modele.
- Table `TreatmentCabinCompatibility` ajoutee au modele.
- Migration Alembic ajoutee pour `Appointment.note` et `TreatmentCabinCompatibility`.

## Reste a faire pour atteindre 100 %

### Priorite 1

- Ajouter une interface admin pour gerer les compatibilites prestation/cabine.
- Ajouter une vraie vue semaine exploitable, distincte de la modale de planification.
- Ajouter l'historique `AuditLog` sur creation, deplacement, modification et annulation de rendez-vous.
- Ajouter des tests automatises sur :
  - conflits de rendez-vous ;
  - disponibilite praticienne ;
  - disponibilite cabine ;
  - ILU ;
  - compatibilite cabine/prestation ;
  - roles ;
  - CSRF ;
  - multi-etablissements.

### Priorite 2

- Ajouter une gestion des statuts : arrive, en cours, termine, annule, no-show.
- Ajouter une modification detaillee d'un rendez-vous existant.
- Ajouter une confirmation avant les actions sensibles.
- Ajouter une meilleure gestion des exceptions de planning jour par jour.

## Commandes migrations

Installer les dependances :

```bash
pip install -r requirements.txt
```

Appliquer la migration :

```bash
flask db upgrade
```

## Remarque importante

Le projet conserve encore `db.create_all()` pour compatibilite avec le prototype existant. La migration ajoutee est donc prudente : elle verifie l'existence de la colonne et de la table avant modification.
