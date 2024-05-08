import pandas as pd 
import sqlite3
from random import shuffle

# Ouverture du fichier excel sous forme de dictionnaire avec les catégories comme clés
questions = pd.read_excel('Questions PPII.xlsx', sheet_name=None)

with sqlite3.connect('codesafe.db') as conn:
    cursor = conn.cursor()

    for categorie in questions.keys():
        # Utilisation de transactions pour chaque catégorie
        conn.execute('BEGIN TRANSACTION')

        cats = conn.execute('SELECT nom_categorie FROM categories').fetchall()
        categories = [cat[0] for cat in cats]
        
        # Pour chaque catégorie on verifie si elle existe déjà dans la base de données
        if categorie not in categories:            
            conn.execute('INSERT INTO categories (nom_categorie) VALUES (?)', (categorie,))

        # Récupération de l'id de la categorie
        id_categorie = conn.execute('SELECT id_categorie FROM categories WHERE nom_categorie=?',
                                    (categorie,)).fetchone()[0]

        for quest_reps in questions[categorie].values:
            # On récupère la question et les réponses associées, la 1ere étant la bonne réponse
            question, *answers = quest_reps
            all_qs = cursor.execute('SELECT question_txt FROM questions WHERE id_categorie=?',
                                  (id_categorie,)).fetchall() 
            qs = [q[0] for q in all_qs]

            if question not in qs:
                # Si la question n'est pas déjà dans la base de données, on l'ajoute
                cursor.execute('INSERT INTO questions (question_txt, id_categorie) VALUES (?, ?)', 
                            (question, id_categorie))
                id_question = cursor.lastrowid

                # On mélange l'ordre des réponses pour que la 1ere ne soit pas toujours la bonne
                correct_answer = answers[0]
                shuffle(answers)

                # On récupère les reponses associées à la question
                all_ans = cursor.execute('SELECT reponse_txt FROM reponses WHERE id_question=?',
                                       (id_question,)).fetchall()
                ans = [a[0] for a in all_ans]

                if correct_answer not in ans:
                    for answer in answers:
                        # On ajoute les réponses à la base de données
                        cursor.execute('INSERT INTO reponses (id_question, reponse_txt, is_good) VALUES (?, ?, ?)',
                                       (id_question, answer, 1 if answer == correct_answer else 0))

        # Commit de la transaction après avoir traité toutes les questions d'une catégorie
        conn.execute('COMMIT')
