# CodeSafe

### Abstract
Dans le cadre de notre **Projet Pluridisciplinaire d'Informatique Intégrative** à Télécom Nancy,\
nous avons décidé de créer un site web interactif à visée éducative :\
sensibiliser à la sécurité informatique au travers de quizz, test de mots de passe, etc.

### Faire fonctionner le site web
Il suffit de cloner ce projet, \
puis d'exécuter la commande : ```pip install -r requirements.txt```\
et enfin de lancer le fichier app.py : ```python3 app.py```

### Points techniques
- création d'un site web à l'aide de Jinja & Flask *(app.py)*
- interaction en temps réel avec une base de données SQLite
- création d'un quizz, avec couleurs vertes ou rouges pour valider chaque réponse
- frontend à l'aide de HTML & CSS
- connexion chiffrée des utilisateurs
- gestion des pourcentages de réussite par catégorie pour chaque utilisateur
- ajout automatique des questions du fichier excel dans la base de données *(excel_to_db.py)*

### Aperçu du projet

#### Accueil
![Accueil](/static/screen_accueil.png?raw=true "Accueil")

#### Quizz
![Quizz](/static/screen_quizz.png?raw=true "Quizz")

#### Profil
![Profil](/static/screen_profil.png?raw=true "Profil")