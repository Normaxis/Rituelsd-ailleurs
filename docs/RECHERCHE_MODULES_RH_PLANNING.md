# Recherche modules deja definis - planning, RH, formations, habilitations

## Ce qui etait prevu

Le projet Rituels d'Ailleurs / Le Petit Rituel devait integrer un vrai pilotage interne, pas seulement un site vitrine.

Fonctionnalites retrouvees dans les decisions projet :

- planning date, flexible, non fixe ;
- jours de repos variables ;
- echanges de jours ;
- samedi tournant ;
- formations integrees au planning ;
- conges et absences ;
- reservation client debloquee par le planning reel ;
- matrice ILU ;
- reservation seulement si niveau ILU L ou U ;
- gestion des cabines ;
- gestion du personnel ;
- suivi des habilitations ;
- suivi des formations ;
- alertes de renouvellement ;
- rattachement a un institut ;
- compte personnel par salarie ;
- historique et tracabilite.

## Regle planning

Le planning doit etre le centre du logiciel. Il doit gerer :

- presence ;
- repos ;
- conge ;
- formation ;
- indisponibilite ;
- rendez-vous ;
- cabine reservee ;
- ressource humaine associee.

## Regle reservation

Un rendez-vous client ne doit etre propose que si :

- la prestation est active ;
- une salariee travaille sur la date demandee ;
- la salariee a le niveau ILU L ou U ;
- la cabine compatible est libre ;
- aucun chevauchement n'existe ;
- la duree rentre dans le planning.

## Regle RH

Le module RH doit suivre :

- personnel ;
- roles ;
- institut de rattachement ;
- formations realisees ;
- formations prevues ;
- habilitations ;
- dates de validite ;
- alertes a 60 jours ;
- statut expire / a renouveler / valide.

## Elements reconstruits maintenant

- modeles formations ;
- modeles habilitations ;
- base de module RH ;
- dashboard admin renforce ;
- rappel des fonctions planning / ILU / RH dans le pilotage.

## Prochaines reprises techniques

1. activer le module RH dans la navigation admin ;
2. creer les pages personnel, formations, habilitations ;
3. connecter les formations et conges au planning ;
4. afficher les alertes de renouvellement ;
5. connecter les habilitations aux droits operationnels.
