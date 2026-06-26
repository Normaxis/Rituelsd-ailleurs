# Cahier des charges - Plateforme de gestion Rituels d'Ailleurs

## 1. Presentation du projet

### Contexte

L'entreprise utilise aujourd'hui plusieurs outils distincts : site internet vitrine, Planity pour les rendez-vous, tableurs Excel, documents papier et outils internes. Cette organisation provoque des doubles saisies, une perte de temps, un manque de visibilite globale, des risques d'erreurs et une difficulte de pilotage.

### Objectif

Developper une plateforme web unique permettant de gerer l'ensemble de l'activite de Rituels d'Ailleurs et Le Petit Rituel depuis une seule interface.

## 2. Architecture generale

### Espace public

L'espace public doit inclure : site vitrine, presentation des instituts, equipe, prestations, tarifs, cartes cadeaux, actualites, contact, FAQ, avis clients et reservation en ligne.

La reservation en ligne doit remplacer Planity. Le client doit pouvoir choisir son institut, sa prestation, sa praticienne, son creneau, payer un acompte et recevoir une confirmation.

### Espace administration

L'espace administration doit permettre de piloter : rendez-vous, planning, personnel, ILU, cabines, clients, stocks, fournisseurs, cartes cadeaux, documents, RH, habilitations, QSE et tableau de bord dirigeante.

## 3. Multi-sites

L'application doit gerer Rituels d'Ailleurs et Le Petit Rituel. Chaque institut possede ses horaires, cabines, salariees, prestations, statistiques et stocks. Une vue globale et une vue individuelle doivent etre disponibles.

## 4. Gestion des salariees

Chaque fiche salariee doit contenir : nom, prenom, photo, fonction, date d'embauche, contrat, coordonnees, institut de rattachement et planning.

Le planning doit gerer : horaires hebdomadaires, conges, RTT, arrets maladie, absences exceptionnelles et formations. Les vues attendues sont jour, semaine et mois.

## 5. Competences ILU

Le systeme ILU permet d'identifier les competences de chaque salariee.

- I = initiee : connait la prestation mais necessite un accompagnement.
- L = libre / autonome : realise seule la prestation.
- U = experte : referente technique.

Lors d'une reservation, le moteur verifie la competence requise, le niveau ILU et la disponibilite.

## 6. Cabines

Chaque cabine possede : nom, institut, type et disponibilite. Types possibles : massage solo, massage duo, visage, amincissant, drainage, femme enceinte, enfant et bronzage.

Un creneau est disponible uniquement si la praticienne est disponible, la competence est disponible, la cabine est disponible et le temps est suffisant.

## 7. Rendez-vous

Les rendez-vous peuvent etre crees depuis le site internet, le telephone, l'accueil ou l'administration. Fonctions attendues : deplacement, annulation, liste d'attente, confirmation automatique, rappels SMS et rappels email.

L'historique client doit conserver les prestations realisees, praticiennes, achats, cartes cadeaux et notes internes.

## 8. Clients et fidelite

La fiche client doit contenir les coordonnees, date anniversaire, preferences, allergies, contre-indications et historique complet.

La fidelite doit gerer points, remises, offres anniversaires et parrainage.

## 9. Cartes cadeaux

Les cartes cadeaux peuvent etre creees par montant libre, prestation, duo ou formule personnalisee. Une generation automatique PDF est attendue avec logo, numero unique, QR code et date d'expiration.

## 10. Stocks et fournisseurs

Chaque produit doit contenir reference, stock actuel, unite, fournisseur, cout d'achat et seuil minimum. La consommation par prestation doit permettre de deduire automatiquement les quantites lors d'un rendez-vous realise.

Les alertes attendues concernent seuil minimum, rupture imminente et produit perime. Le module fournisseur doit suivre fournisseurs, commandes, livraisons et factures.

## 11. RH et habilitations

Le module RH doit suivre SST, evacuation incendie, manipulation extincteurs, gestes et postures, habilitations electriques et formations internes.

Les documents RH doivent stocker certificats, attestations, contrats et avenants.

Les alertes habilitations doivent se declencher 90 jours, 60 jours, 30 jours, 7 jours avant expiration et le jour J.

## 12. Gestion documentaire

La plateforme doit centraliser procedures, modes operatoires, fiches de poste, reglements, audits et DUERP avec versionnage automatique.

## 13. Module QSE

Le module QSE est un differenciateur. Il doit couvrir : DUERP, plan d'actions, accidents du travail, presque accidents, audits, reclamations, satisfaction clients, actions correctives, consommations, dechets et suivi reglementaire.

## 14. Tableau de bord dirigeante

Le tableau de bord doit afficher les rendez-vous du jour, le chiffre d'affaires du jour, l'occupation des cabines, l'occupation des salariees, les alertes habilitations, stocks bas, cartes cadeaux expirantes et contrats arrivant a echeance.

Indicateurs attendus : chiffre d'affaires par institut, prestation et salariee, taux de remplissage, nombre de clients, fidelisation et panier moyen.

## 15. Responsive

L'application doit etre utilisable sur ordinateur, tablette et mobile, avec une attention particuliere pour l'administration sur tablette.
