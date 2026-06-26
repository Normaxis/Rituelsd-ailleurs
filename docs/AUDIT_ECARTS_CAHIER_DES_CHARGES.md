# Audit des ecarts - cahier des charges

## Synthese

Le projet contient deja les bases suivantes : vitrine, reservation, planning, ILU, cabines, stocks, routines, RH, formations et habilitations. Cependant, le cahier des charges cible une plateforme beaucoup plus large, avec un remplacement complet de Planity et un vrai pilotage multi-sites.

## Deja present ou partiellement present

- Site public vitrine : partiel.
- Reservation en ligne : partiel.
- Planning date : partiel.
- Drag and drop planning : base presente.
- ILU : base presente.
- Cabines : base presente.
- Stocks : base presente.
- Routines : base presente.
- RH formations habilitations : base presente.
- Multi-sites : base presente via les instituts.

## Ecarts prioritaires

### Critique

1. Donnees initiales / compte admin : le seed automatique a ete retire, il faut un script d'initialisation propre.
2. Reservation : le client doit pouvoir choisir l'institut et eventuellement la praticienne.
3. Clients : fiche client, historique, preferences, allergies et contre-indications absents.
4. Cartes cadeaux : module absent.
5. Paiement acompte : absent.
6. Documents : absent.
7. Fournisseurs : absent.
8. Tableau de bord dirigeante : incomplet.

### Important

1. Planning semaine/mois a renforcer.
2. Habilitations : alertes 90/60/30/7/J a ajouter.
3. Stocks : fournisseur, cout, peremption et consommation par prestation a ajouter.
4. Cabines : compatibilite structuree avec les prestations a creer.
5. Fidelite client : absent.

### Evolution

1. SMS / email automatiques.
2. PDF cartes cadeaux.
3. QR code cartes cadeaux.
4. Module QSE complet.
5. Versionnage documentaire.

## Reprise technique decidee

- Verrouiller le cahier des charges dans docs.
- Ajouter les modeles manquants : Client, GiftCard, Supplier, Document, QSEAction.
- Ajouter progressivement les routes admin propres par domaine.
- Eviter les routes melangees entre modules.
- Garder une architecture par blueprint : public, auth, admin, booking, planning, ilu, stocks, routines, hr, clients, giftcards, documents, qse.
