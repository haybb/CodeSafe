from flask import Flask, render_template, redirect, request, make_response
from flask_login import LoginManager, UserMixin, current_user, login_user, login_required, logout_user
from flask_bcrypt import Bcrypt
import sqlite3

# Initialisation
app = Flask(__name__)
app.config['SECRET_KEY'] = "MySuperSecretKey"
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)

# Connection à la base de données
def db_connection():
    conn = sqlite3.connect('codesafe.db')
    return conn

# Classe utilisateur
class User(UserMixin):
    def __init__(self, username, password):
        self.username = username
        self.password = password

    @property
    def id(self):
        return self.username

    @staticmethod
    def get_user_by_username(username):
        conn = db_connection()
        user_data = conn.execute('''
            SELECT * FROM users WHERE username=?''',
            (username,)).fetchone()
        conn.close()
        if user_data:
            return User(user_data[0], user_data[1])
        return None

# User loader
@login_manager.user_loader
def load_user(username):
    return User.get_user_by_username(username)

# Index
@app.route('/', methods=['GET'])
def index():
    conn = db_connection()
    categories = conn.execute('''
        SELECT id_categorie, nom_categorie
        FROM categories''').fetchall()
    return render_template('index.html', bd=categories)

# Header
@app.route('/header/', methods=['GET'])
def header():
    if current_user.is_authenticated:
        return render_template("header.html", current_user=current_user, isauth=True)
    else:
        return render_template("header.html", current_user=current_user, isauth=False)

# Footer
@app.route('/footer/', methods=['GET'])
def footer():
    return render_template("footer.html")

# Register
@app.route('/register/', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect('/')
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        conn = db_connection()
        try:
            conn.execute('''
                INSERT INTO users
                VALUES (?, ?)''',
                (username, hashed_password))
        except sqlite3.IntegrityError:
            return render_template('register.html', usernameExists=True)
        conn.commit()
        conn.close()
        return redirect('/')
    return render_template('register.html')

# Login
@app.route('/login/', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect('/')
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.get_user_by_username(username)
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            return redirect('/')
        else:
            return render_template('login.html', badCredentials=True)
    return render_template('login.html', badCredentials=False)

# Logout
@app.route('/logout/', methods=['GET'])
@login_required
def logout():
    logout_user()
    return redirect('/')

# Quizz
@app.route('/quizz/<categorie>', methods=['GET','POST'])
def quizz(categorie): 
    # Si l'utilisateur n'est pas connecté, on le renvoie sur la page login
    if not current_user.is_authenticated:
        return redirect('/login/')
    
    try:
        question_index = int(request.args.get('question_index'))

    except TypeError:
        question_index = 0

    conn = db_connection()

    question_data = conn.execute('''
        SELECT id_question, question_txt
        FROM questions
        WHERE id_categorie=?''',
        (categorie,)).fetchall()

    # on met toutes les informations dans une liste de listes res :
    # [ ['question1', ['réponse1', 'réponse2', ...], 'réponse juste'], ['question2', ...], ... ]
    res = []
    for question in question_data:
        reponses = conn.execute('''
            SELECT reponse_txt
            FROM reponses
            WHERE id_question = ?''',
            (question[0],)).fetchall()
        list_reponses = [reponse[0] for reponse in reponses]
        bonne_reponse = conn.execute('''
            SELECT reponse_txt
            FROM reponses
            WHERE id_question = ?
            AND is_good = 1''',
            (question[0],)).fetchone()[0]
        res.append([question[1], list_reponses, bonne_reponse])

    current_question = res[question_index] if question_index < len(res) else None
    count = int(request.cookies.get('bonnes_reponses',0))
    nb_rep = len(res)

    if request.method == 'POST':
        user_response = request.form.get('reponse')
        is_correct = user_response == current_question[2]        
        # Si on commence le quizz, on remet le compteur à 0
        if question_index == 0:
            count = 0
        count = count+1 if is_correct else count
        
        # Si on a atteint la fin du quizz, on modifie la bd
        if question_index == len(question_data)-1:
            # On regarde le meilleur pourcentage actuel
            pct_cat = conn.execute('''
                SELECT pourcent 
                FROM pourcent_categorie
                WHERE id_categorie = ?
                AND username = ?''',
                (categorie, current_user.username)).fetchone()
            if pct_cat is None:
                pct_cat = -1
            else:
                pct_cat = pct_cat[0]
            # On calcule le poucentage de l'essai actuel
            pourcent = round(count / len(question_data) * 100, 2)
            # Si l'utilisateur a fait mieux que son record, on actualise
            if pourcent > pct_cat:
                try:
                    conn.execute('''
                        INSERT INTO pourcent_categorie 
                        (id_categorie, username, pourcent)
                        VALUES (?,?,?)''',
                        (categorie, current_user.username, pourcent))
                except sqlite3.IntegrityError:
                    conn.execute('''
                        UPDATE pourcent_categorie
                        SET pourcent=?
                        WHERE id_categorie=? AND username=?''',
                        (pourcent, categorie, current_user.username))
                conn.commit()
                conn.close()
        
        response = make_response(render_template('quizz.html', current_question=current_question,
                               question_index=question_index, user_response=user_response,
                               correct_answer=current_question[2], categorie=categorie, count=count, nb_rep=nb_rep))
        response.set_cookie('bonnes_reponses', str(count))
        return response
    
    else:
        return render_template('quizz.html', current_question=current_question, 
                               question_index=question_index, categorie=categorie,
                               count=count, nb_rep=nb_rep)
    
# Page pour voir son profil
@app.route('/profile/', methods=['GET', 'POST'])
@login_required
def profile():
    # Si l'utilisateur veut afficher la page
    if request.method == 'GET':
        conn = db_connection()
        # On récupère les ids de toutes les catégories
        all_categories = conn.execute('''
            SELECT id_categorie, nom_categorie FROM categories''').fetchall()
        all_categories = [list(id_cat) for id_cat in all_categories]
        # On récupère les résultats de l'utilisateur dans chaque catégorie
        data = []
        for id_cat, nom_cat in all_categories:
            pourcent = conn.execute('''
                SELECT pourcent FROM pourcent_categorie
                WHERE id_categorie=? AND username=?''',
                (id_cat, current_user.username)).fetchone()
            if pourcent != None:
                data.append([nom_cat, pourcent[0]])
            else:
                data.append([nom_cat, 0])
        conn.close()
        # On affiche la page
        return render_template('profile.html', username=current_user.username,
                            data=data)
    # Si l'utilisateur veut changer de mot de passe
    else:
        old_password = request.form['old-password']
        new_password1 = request.form['new-password1']
        new_password2 = request.form['new-password2']
        user = User.get_user_by_username(current_user.username)
        if (user and bcrypt.check_password_hash(user.password, old_password)
            and new_password1 == new_password2):
            # Le mot de passe est changé
            hashed_password = bcrypt.generate_password_hash(new_password1).decode('utf-8')
            conn = db_connection()
            conn.execute('''
                UPDATE users
                SET password=?
                WHERE username=?''',
                (hashed_password, current_user.username))
            conn.commit()
            conn.close()
            logout_user()
            return redirect('/login/')
        elif user and bcrypt.check_password_hash(user.password, old_password):
            # Les deux nouveaux mots de passe ne sont pas les mêmes
            # On doit récupérer les résultats pour les réafficher
            conn = db_connection()
            # On récupère les ids de toutes les catégories
            all_categories = conn.execute('''
                SELECT id_categorie, nom_categorie FROM categories''').fetchall()
            all_categories = [list(id_cat) for id_cat in all_categories]
            # On récupère les résultats de l'utilisateur dans chaque catégorie
            data = []
            for id_cat, nom_cat in all_categories:
                pourcent = conn.execute('''
                    SELECT pourcent FROM pourcent_categorie
                    WHERE id_categorie=? AND username=?''',
                    (id_cat, nom_cat)).fetchone()
                if pourcent != None:
                    data.append([nom_cat, pourcent])
                else:
                    data.append([nom_cat, 0])
            conn.close()
            return render_template('profile.html', username=current_user.username,
                                   data=data, differentNewPasswords=True)
        else:
            # Le mot de passe actuel entré ne correspond pas à celui de la BD
            # On doit récupérer les résultats pour les réafficher
            conn = db_connection()
            # On récupère les ids de toutes les catégories
            all_categories = conn.execute('''
                SELECT id_categorie, nom_categorie FROM categories''').fetchall()
            all_categories = [list(id_cat) for id_cat in all_categories]
            # On récupère les résultats de l'utilisateur dans chaque catégorie
            data = []
            for id_cat, nom_cat in all_categories:
                pourcent = conn.execute('''
                    SELECT pourcent FROM pourcent_categorie
                    WHERE id_categorie=? AND username=?''',
                    (id_cat, nom_cat)).fetchone()
                if pourcent != None:
                    data.append([nom_cat, pourcent])
                else:
                    data.append([nom_cat, 0])
            conn.close()
            return render_template('profile.html', username=current_user.username,
                                   data=data, badOldPassword=True)

if __name__ == '__main__':
    app.run(debug=True)
