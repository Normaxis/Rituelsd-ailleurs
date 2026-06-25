# Déploiement Render

## Préparation effectuée

Le dépôt contient maintenant :

- `render.yaml` pour créer le service Render ;
- `gunicorn` dans `requirements.txt` ;
- `wsgi.py` comme point d’entrée de production ;
- `config.py` compatible avec les variables d’environnement.

## Configuration Render recommandée

Depuis Render :

1. `New` → `Web Service` ;
2. connecter le dépôt GitHub `Normaxis/Rituelsd-ailleurs` ;
3. choisir la branche `main` ;
4. Render détectera le fichier `render.yaml`.

Si tu configures manuellement :

```text
Language: Python 3
Build Command: pip install -r requirements.txt
Start Command: gunicorn wsgi:app
```

## Variables d’environnement

À définir sur Render :

```text
SECRET_KEY = valeur générée automatiquement par Render
```

Pour une version de production complète, il faudra ensuite ajouter une base PostgreSQL et définir :

```text
DATABASE_URL = URL interne PostgreSQL Render
```

## Limite actuelle

La version actuelle peut fonctionner avec SQLite pour une démonstration, mais SQLite sur Render n’est pas adapté à la production durable. La prochaine étape sera d’ajouter PostgreSQL + Flask-Migrate.
