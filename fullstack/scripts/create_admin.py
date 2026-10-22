"""Initialise un compte administrateur TGCA depuis la ligne de commande."""
import getpass
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import db,now,password_hash

def main():
    email=input('Email administrateur : ').strip().lower()
    name=input('Nom : ').strip()
    pw=getpass.getpass('Mot de passe (12 caractères minimum) : ')
    if len(pw)<12 or '@' not in email or not name:
        raise SystemExit('Email, nom et mot de passe de 12 caractères minimum requis.')
    with db() as c:
        c.execute('INSERT INTO users(email,name,password_hash,role,created_at) VALUES(?,?,?,?,?) ON CONFLICT(email) DO UPDATE SET name=excluded.name,password_hash=excluded.password_hash,role=excluded.role',
                  (email,name,password_hash(pw),'admin',now()))
    print('Administrateur enregistré. Connectez-vous à /connexion.')

if __name__=='__main__': main()
