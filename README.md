# SYGALIN BASE PYTHON EPARGNE

Ceci est le projet de base pour le développement d'applications Python. Il contient les configurations et dépendances de base.

## Structure du projet.

- `app/` - Contient le code source de l'application. Dans ce dossier vous trouverez:
- `common/` - Qui contient les fonctions ou classes communes à tous les services
- `config/` - Qui contient les fichiers de configuration pour toute l'application
- `services/` - Qui contient les différents services/API de l'application. Chaque service est un package indépendant et contient les fichiers:
- `__init__.py` - Initialisation du service. Ce fichier est vide. Il sert juste à faire savoir qu'il s'agit d'un package
- `router.py` - Fichier contenant les routes de l'API du service
- `services.py` - Fichier contenant les logiques métiers et les traitements associés au service. Ce fichier contient généralement les méthodes appelées par le router. Ce sont les contrôleurs tels les connais dans le jargon habituel
- `schemas.py` - Fichier contenant les schémas Pydantic pour la validation des données envoyées et reçues par le service
- `dependencies.py` - Fichier contenant les dépendances et injections de dépendances pour le service. Ce sont des helpers
- `constants.py` - Fichier contenant les constantes utilisées dans le service
- `config.py` - Fichier contenant la configuration relatives au service (variables d'environnement, etc.)

Le fichier `main.py` à la racine contient le code de démarrage du service: Il effectue le chargement des différentes routes des différents service. Il est également configuré pour être déployé sur une lambda function (AWS).

**N.B:** Vous trouverez 02 exemples de services, `welcome` et `countries`.

### Création du nouveau service

La création d'un nouveau service consiste à créer un nouveau dossier dans le dossier du service contenant les 08 fichiers suivants: `__init__.py`, `router.py`, `services.py`, `schemas.py`, `dependencies.py`, `constants.py` et `config.py`.

Vous pouvez exécuter la commande suivante pour le faire automatiquement: 
```python
python scaffold.py service:create new_service
```
où `new_service` est le service à créer.

### Lancement de l'environnement de développement

Pour lancer l'environnement de développment:
- Mettez à jour le fichier `.env` avec les valeurs de votre environnement de développement
- Exécutez la commande ```venv\Scripts\activate``` pour activer l'environnement virtuel Python
- Exécutez ensuite la commande ```pip install poetry``` pour installer les dépendances
- Exécutez ensuite la commande ```poetry install``` pour installer les dépendances
- Exécutez enfin ```uvicorn main:app --host 0.0.0.0 --port 8000 --reload``` pour démarrer l'application en mode développement. Vous pouvez remplacer le port par une autre valeur si besoin

**N.B:** Vous devez avoir Python 3.13+ installé sur votre machine. [Télécharger ici](https://www.python.org/downloads/)

## Dépendances intégrées

### Framework de base

Le framework utilisé pour ce projet est FastAPI, un framework axé sur la vélocité d'exécution et sur la légèreté (très peu de dépendances embarquées). Vous trouvez les détails [ici](https://fastapi.tiangolo.com/).
Il supporte également les opération asynchrones.

### ORM

Vous n'aurez pas besoin d'écrire manuellement des requêtes SQL brutes pour communiquer avec votre base de données. L'ORM(Object Relational Mapper) nommé SQLAlchemly 2.0 sera utilisé pour mapper les objets Python aux tables de la base de données. Vous pouvez consulter [la documentation](https://docs.sqlalchemy.org/en/20/) pour savoir comment tirer pleinement parti de cet ORM. Vous trouverez un exemple de son utilisation dans le service `countries`.

En ce qui concerne les migration, c'est le package [Alembic](https://alembic.sqlalchemy.org/en/latest/) qui est utilisé.

* Créer une migration: `alembic revision --autogenerate -m "Your migration message"`. Les migrations seront ajoutées au dossier `alembic/versions`.
* Appliquer les migrations: `alembic upgrade head`
* Annuler toutes les migrations: `alembic downgrade base`

### Factories
* Executez `pip install factory_boy` puis lancer la route http://127.0.0.1:8001/v1/api/cycle_settings/activities/

### AWS

Le package `boto3` est préinstallé. Vous pourez si besoin communiquer avec les services AWS.

### Gestion des dates et fuseaux horaires

Le package utilisé pour la gestion des dates est `pendelum`. Le fuseau horaire par défaut est UTC. dans le fichier `app/common/moment.py`, vous trouverez la fonction à utiliser pour créer des objets de type Datetime et les manipuler.
**N.B:** Toujours enregistrer les données dans la BD au fuseau horaire UTC et les retourner également au front-end en UTC.

### Génération des chaînes UUID v4 et v5

Les chaînes UUID sont générées grace è la librairie statdard `uuid`, intyégrée à Python. Voir la [documentation](https://docs.python.org/3/library/uuid.html) pour plus d'informations.

### Encodage/décodage des chaînes JSON

Python supporte nativement la bibliothèque standard json pour encoder (`json.dumps()`) et décoder (`json.loads()`) des objets JSON. Voir la [documentation](https://docs.python.org/3/library/json.html#module-json).

### Requêtes HTTP

Les requêtes HTTP sont effectuées avec le package `httpx`. Voir la [documentation](https://www.python-httpx.org/) pour plus d'informations. Vous trouverez un exemple d'utilisation dans le service `countries`.

### Constantes pour les réponses API

Python embarque nativement la librairie http.client pour les codes de statut HTTP. Vous pouvez les importer dans votre code avec `import http.client`.
"# service epargnes et placements" 

### Authentification

faite une MAJ du package Jose avec la commande ``` pip install --upgrade python-jose ``` 

### Upload 

Pour l'upload des fichiers, installez les packages suivants
- ``` pip install boto3 ``` 
- ``` pip install python-multipart ``` 
- ``` pip install --upgrade python-jose ```
- ``` pip install pytest-asyncio httpx ```
- ``` pip install pydantic[email]  ```
test


