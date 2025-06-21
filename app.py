import os
import sqlite3
from flask import Flask, request, redirect, render_template, jsonify
import shortuuid

app = Flask(__name__)

# --- Configuration de la base de données SQLite ---
DATABASE = 'database.db' # Le fichier de base de données sera créé ici

def get_db_connection():
    """Crée et retourne une connexion à la base de données."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # Permet d'accéder aux colonnes par leur nom
    return conn

def init_db():
    """Initialise la base de données en créant la table 'links' si elle n'existe pas."""
    with app.app_context(): # Nécessaire pour accéder à l'application context hors d'une requête
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_url TEXT NOT NULL UNIQUE,
                short_code TEXT NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

# Initialise la base de données au démarrage de l'application
init_db()

# --- Routes de l'application Flask ---

@app.route('/')
def index():
    """Sert le fichier index.html."""
    return render_template('index.html')

@app.route('/shorten', methods=['POST'])
def shorten_url():
    """API pour créer un lien court à partir d'une URL longue."""
    original_url = request.json.get('original_url')

    if not original_url:
        return jsonify({'error': 'L\'URL originale est requise.'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Vérifie si l'URL originale existe déjà pour éviter les doublons
        cursor.execute('SELECT short_code FROM links WHERE original_url = ?', (original_url,))
        existing_link = cursor.fetchone()

        if existing_link:
            # Si l'URL existe déjà, renvoie le code court existant
            return jsonify({'short_url': existing_link['short_code']}), 200

        # Génère un nouveau code court unique
        short_code = shortuuid.uuid()[:8] # Utilise les 8 premiers caractères pour un code plus compact

        # Insère le nouveau lien dans la base de données
        cursor.execute('INSERT INTO links (original_url, short_code) VALUES (?, ?)',
                       (original_url, short_code))
        conn.commit()

        # Renvoie le code court généré
        return jsonify({'short_url': short_code}), 201

    except sqlite3.Error as e:
        app.logger.error(f"Erreur de base de données: {e}")
        return jsonify({'error': 'Erreur interne du serveur.'}), 500
    finally:
        conn.close()

@app.route('/<short_code>')
def redirect_to_original(short_code):
    """Gère la redirection des liens courts vers leurs URLs originales."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Cherche l'URL originale correspondant au code court
    cursor.execute('SELECT original_url FROM links WHERE short_code = ?', (short_code,))
    link = cursor.fetchone()
    conn.close()

    if link:
        # Redirection permanente (code 301) vers l'URL originale
        return redirect(link['original_url'], code=301)
    else:
        # Si le code court n'est pas trouvé
        return "Lien non trouvé", 404

if __name__ == '__main__':
    # Lance le serveur Flask en mode débogage pour le développement
    app.run(debug=True)