"""TGCA SARL.AU — public website + private project portal.
Run: uvicorn app:app --reload
"""
import base64
import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import smtplib
import sqlite3
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, Request, Form, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
import csv
import io

ROOT = Path(__file__).resolve().parent
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / '.env')
except ImportError:
    pass
DATA_DIR = Path(os.getenv('TGCA_DATA_DIR', str(ROOT / 'data')))
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS = DATA_DIR / 'uploads'
UPLOADS.mkdir(exist_ok=True)
PUBLIC_MEDIA = DATA_DIR / 'public_media'
PUBLIC_MEDIA.mkdir(exist_ok=True)
DATABASE = DATA_DIR / 'tgca.db'
IS_PROD = os.getenv('ENVIRONMENT') == 'production'
# Valeurs d'exemple ou triviales : jamais acceptées comme clé de signature.
WEAK_SECRETS = {'', 'REMPLACER_PAR_UNE_CLE_ALEATOIRE_LONGUE', 'changeme', 'secret', 'change-me', 'test'}

def secret_is_strong(value: str) -> bool:
    return value not in WEAK_SECRETS and len(value) >= 32

RAW_SECRET = os.getenv('SESSION_SECRET', '').strip()
if IS_PROD and not secret_is_strong(RAW_SECRET):
    raise RuntimeError('SESSION_SECRET absent, trop court (32 caractères minimum) ou laissé à sa valeur d\'exemple. '
                       'Générez-en un avec : python -c "import secrets; print(secrets.token_urlsafe(48))"')
if secret_is_strong(RAW_SECRET):
    SECRET = RAW_SECRET
else:
    SECRET = secrets.token_urlsafe(48)
    logging.warning('SESSION_SECRET absent ou faible : clé temporaire utilisée (sessions perdues au redémarrage).')
SITE_URL = os.getenv('SITE_URL', '').strip().rstrip('/')
# Coordonnées officielles TGCA (modifiables par variables d'environnement).
CONTACT = dict(
    phone=os.getenv('CONTACT_PHONE', '06 63 22 43 22'),
    tel=os.getenv('CONTACT_TEL', '+212663224322'),
    email=os.getenv('CONTACT_EMAIL', 'ste.tgca@gmail.com'),
)
WHATSAPP_NUMBER = re.sub(r'\D', '', os.getenv('WHATSAPP_NUMBER', '212663224322'))
app = FastAPI(title='TGCA SARL.AU', docs_url=None if IS_PROD else '/api/docs', redoc_url=None)
app.add_middleware(SessionMiddleware, secret_key=SECRET, same_site='lax', https_only=IS_PROD, session_cookie='tgca_session', max_age=60*60*10)
if os.getenv('ALLOWED_HOSTS'):
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=[s.strip() for s in os.getenv('ALLOWED_HOSTS','').split(',')])
app.mount('/static', StaticFiles(directory=ROOT/'static'), name='static')
app.mount('/media', StaticFiles(directory=PUBLIC_MEDIA), name='media')
templates = Jinja2Templates(directory=str(ROOT/'templates'))

SERVICES = [
    dict(slug='construction', icon='building-2', title='Construction de bâtiments', desc='Réalisation de bâtiments résidentiels et professionnels, des fondations aux finitions.', img='chantier.webp'),
    dict(slug='immeubles', icon='building', title='Immeubles résidentiels', desc='Des ensembles immobiliers contemporains pensés pour la qualité et la durabilité.', img='immeuble-avenue.webp'),
    dict(slug='villas', icon='house', title='Villas haut standing', desc='Des villas singulières, alliant architecture, confort et finitions soignées.', img='villa-coucher-soleil.webp'),
    dict(slug='appartements', icon='layout-dashboard', title='Appartements moyen standing', desc='Des logements fonctionnels et bien conçus, adaptés aux besoins de chacun.', img='appartements-contemporains.webp'),
    dict(slug='chantier', icon='hard-hat', title='Suivi de chantier', desc='Coordination des intervenants, suivi des jalons et contrôle de la qualité.', img='architecture.webp'),
    dict(slug='etudes', icon='drafting-compass', title='Études et pilotage', desc='Accompagnement, préparation technique et organisation des étapes du projet.', img='maquette-villa-3d.webp'),
]

PLANS_3D = [
    dict(slug='villa-patio', title='Villa contemporaine avec patio', tag='Villa • Haut standing', family='villa',
         desc='Volumes ouverts, suite parentale, séjour généreux et espace extérieur. Une distribution illustrant la fluidité des circulations.',
         rooms=['Grand séjour', 'Cuisine ouverte', 'Suite principale', 'Chambre invités', 'Bureau / hall', 'Terrasse paysagée']),
    dict(slug='appartement-3-chambres', title='Appartement moderne — trois chambres', tag='Appartement • Résidentiel', family='appartement',
         desc='Un exemple de circulation fonctionnelle entre espace de vie, cuisine, salles d’eau et espaces nuit.',
         rooms=['Salon / repas', 'Cuisine', 'Chambre 1', 'Chambre 2', 'Salle de bains', 'Chambre 3']),
    dict(slug='riad-contemporain', title='Riad contemporain avec bassin', tag='Riad • Architecture marocaine', family='riad',
         desc='Interprétation contemporaine du riad autour d’un patio, avec bassin, suite et espaces de réception.',
         rooms=['Salon marocain', 'Patio central', 'Suite', 'Salon / repas', 'Bassin', 'Cuisine']),
    dict(slug='etage-residentiel', title='Immeuble résidentiel — étage type', tag='Immeuble • Collectif', family='immeuble',
         desc='Schéma d’organisation d’un plateau résidentiel avec logements et accès partagés.',
         rooms=['Appartement A', 'Appartement B', 'Appartement C', 'Hall commun', 'Appartement D']),
]

PORTFOLIO_CATEGORIES=('Villa','Riad','Immeuble','Appartement','Bâtiment')

# Inspirations ajoutées en octobre 2026 : insérées une seule fois (une suppression par l'admin reste définitive).
SEED_V2=[
    ('villa-vue-atlas','Villa panoramique, vue sur l’Atlas','Marrakech','Villa','villa-atlas.webp','Inspiration architecturale : terrasse ouverte sur la piscine à débordement, pierre naturelle, moucharabiehs et vue dégagée sur les montagnes.'),
    ('riad-patio-bassin','Riad à patio et bassin','Marrakech','Riad','riad-patio.webp','Inspiration de riad contemporain : patio central, bassin, arcs sculptés et lanternes, dans l’esprit de l’architecture marocaine.'),
    ('villa-palmeraie','Villa contemporaine en palmeraie','Marrakech','Villa','villa-coucher-soleil.webp','Concept de villa haut standing : volumes en pierre, grandes baies vitrées, piscine et terrasses ombragées par les palmiers.'),
    ('residence-travertin','Résidence en pierre de travertin','Rabat','Immeuble','immeuble-avenue.webp','Inspiration d’immeuble résidentiel : façade en travertin, balcons vitrés végétalisés et rez-de-chaussée vitré sur avenue.'),
    ('residence-jardins-cascade','Résidence et jardins en cascade','Marrakech','Appartement','residence-marrakech.webp','Illustration d’un ensemble résidentiel organisé autour de jardins méditerranéens, de bassins en cascade et d’allées piétonnes.'),
    ('maquette-villa-patio','Maquette 3D d’une villa à patio','Salé','Villa','maquette-villa-3d.webp','Vue 3D en coupe : chambres, séjour, cuisine, piscine centrale, jardin et carport. Schéma d’inspiration, non contractuel.'),
]

def now():
    return datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

@contextmanager
def db():
    conn = sqlite3.connect(str(DATABASE), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    conn.execute('PRAGMA busy_timeout=30000')
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    with db() as c:
        c.executescript('''
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            password_hash TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('admin','client')),
            created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, email TEXT NOT NULL, phone TEXT NOT NULL,
            project_type TEXT NOT NULL, city TEXT, budget TEXT, message TEXT NOT NULL,
            consent INTEGER NOT NULL DEFAULT 0, status TEXT NOT NULL DEFAULT 'nouveau',
            created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS portfolio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT NOT NULL UNIQUE, title TEXT NOT NULL, city TEXT NOT NULL,
            category TEXT NOT NULL, image TEXT NOT NULL, description TEXT NOT NULL,
            is_illustration INTEGER NOT NULL DEFAULT 1,
            published INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reference TEXT NOT NULL UNIQUE, title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '', client_id INTEGER REFERENCES users(id),
            location TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'étude',
            progress INTEGER NOT NULL DEFAULT 0 CHECK (progress BETWEEN 0 AND 100),
            due_date TEXT, updated_at TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            title TEXT NOT NULL, done INTEGER NOT NULL DEFAULT 0, due_date TEXT, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS attachments (
            id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            filename TEXT NOT NULL, stored_name TEXT NOT NULL UNIQUE, mime TEXT NOT NULL,
            size INTEGER NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT, actor_id INTEGER REFERENCES users(id),
            action TEXT NOT NULL, entity TEXT NOT NULL, entity_id INTEGER NOT NULL, created_at TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS ix_leads_status ON leads(status);
        CREATE INDEX IF NOT EXISTS ix_projects_client ON projects(client_id);
        CREATE INDEX IF NOT EXISTS ix_tasks_project ON tasks(project_id);
        ''')
        if not c.execute('SELECT id FROM portfolio LIMIT 1').fetchone():
            concept = [
                ('villa-contemporaine','Villa contemporaine','Rabat','Villa','villa-piscine.webp','Inspiration architecturale : volumes épurés, larges baies vitrées et espaces extérieurs paysagers.'),
                ('residence-urbaine','Résidence urbaine','Casablanca','Immeuble','immeuble-premium.webp','Inspiration de résidence moderne avec balcons, espaces communs et finitions contemporaines.'),
                ('villa-paysagee','Villa paysagée','Marrakech','Villa','riad-luxe.webp','Concept de villa individuelle autour des espaces de détente et de la lumière naturelle.'),
                ('ensemble-residentiel','Ensemble résidentiel','Salé','Appartement','appartements-contemporains.webp','Illustration d’un ensemble d’appartements conçu pour un cadre de vie harmonieux.'),
            ]
            c.executemany('INSERT INTO portfolio(slug,title,city,category,image,description,is_illustration,published,created_at) VALUES (?,?,?,?,?,?,1,1,?)',
                         [(*row,now()) for row in concept])
        c.execute('CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
        if not c.execute("SELECT 1 FROM meta WHERE key='seed_v2'").fetchone():
            c.executemany('INSERT OR IGNORE INTO portfolio(slug,title,city,category,image,description,is_illustration,published,created_at) VALUES (?,?,?,?,?,?,1,1,?)',
                          [(*row,now()) for row in SEED_V2])
            c.execute("INSERT INTO meta(key,value) VALUES('seed_v2',?)",(now(),))

init_db()

def password_hash(value: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac('sha256',value.encode('utf-8'),salt,350000)
    return f'pbkdf2_sha256$350000${salt.hex()}${dk.hex()}'

def verify_password(value: str, stored: str) -> bool:
    try:
        alg, rounds, salt, digest = stored.split('$')
        if alg != 'pbkdf2_sha256': return False
        new = hashlib.pbkdf2_hmac('sha256',value.encode('utf-8'),bytes.fromhex(salt),int(rounds))
        return hmac.compare_digest(new,bytes.fromhex(digest))
    except (ValueError,TypeError): return False

def get_user(request):
    user_id = request.session.get('uid')
    if not isinstance(user_id,int): return None
    with db() as c:
        row = c.execute('SELECT id,email,name,role FROM users WHERE id=?',(user_id,)).fetchone()
    return dict(row) if row else None

def csrf_token(request):
    if 'csrf' not in request.session:
        request.session['csrf']=secrets.token_urlsafe(32)
    return request.session['csrf']

def check_csrf(request, submitted: str):
    secret = request.session.get('csrf')
    if not isinstance(secret,str) or not isinstance(submitted,str) or not hmac.compare_digest(secret,submitted):
        raise HTTPException(status_code=403, detail='Formulaire expiré. Rechargez la page et réessayez.')

def site_url(request) -> str:
    return SITE_URL or str(request.base_url).rstrip('/')

def render(request, name, status_code=200, **data):
    root = site_url(request)
    base = dict(request=request, user=get_user(request), csrf=csrf_token(request), year=datetime.now().year,
                services=SERVICES, title='TGCA SARL.AU | Construction au Maroc', description='TGCA SARL.AU : construction de bâtiments, immeubles, appartements et villas au Maroc. Études, réalisation et suivi de chantier.', current=request.url.path,
                site_url=root, canonical=root+request.url.path, whatsapp=WHATSAPP_NUMBER, contact=CONTACT, form={}, private=False)
    base.update(data)
    base['csp_nonce']=getattr(request.state,'csp_nonce','')
    return templates.TemplateResponse(request, name, base, status_code=status_code)

ERROR_TEXTS = {
    400: ('Demande incomplète', 'Certaines informations envoyées ne sont pas valides.'),
    403: ('Accès non autorisé', 'Vous n\'avez pas accès à cette page, ou le formulaire a expiré.'),
    404: ('Page introuvable', 'La page demandée n\'existe pas ou a été déplacée.'),
    409: ('Conflit', 'Cette information existe déjà.'),
    413: ('Fichier trop volumineux', 'Le fichier dépasse la taille autorisée.'),
    429: ('Trop de tentatives', 'Merci de patienter quelques minutes avant de réessayer.'),
}

@app.exception_handler(HTTPException)
@app.exception_handler(StarletteHTTPException)
async def html_errors(request: Request, exc):
    if 300 <= exc.status_code < 400 and exc.headers and 'Location' in exc.headers:
        return RedirectResponse(exc.headers['Location'], exc.status_code)
    heading, text = ERROR_TEXTS.get(exc.status_code, ('Une erreur est survenue', 'Veuillez réessayer.'))
    detail = exc.detail if isinstance(exc.detail, str) and exc.detail not in ('Not Found', 'Forbidden', 'Bad Request') else ''
    private = request.url.path.startswith(('/admin', '/espace-client', '/documents', '/mon-compte'))
    return render(request, 'error.html', status_code=exc.status_code, code=exc.status_code, heading=heading,
                  text=detail or text, private=private, title=f'{heading} | TGCA SARL.AU')

def require_role(request, role='admin'):
    user=get_user(request)
    if not user: raise HTTPException(303,headers={'Location':'/connexion?next='+quote(request.url.path)})
    if user['role']!=role: raise HTTPException(status_code=403,detail='Accès non autorisé')
    return user

def audit(user_id,action,entity,entity_id):
    with db() as c:
        c.execute('INSERT INTO activity(actor_id,action,entity,entity_id,created_at) VALUES (?,?,?,?,?)', (user_id,action,entity,entity_id,now()))

@app.middleware('http')
async def security_headers(request,call_next):
    request.state.csp_nonce=secrets.token_urlsafe(16)
    res=await call_next(request)
    res.headers['X-Content-Type-Options']='nosniff'
    res.headers['X-Frame-Options']='DENY'
    res.headers['Referrer-Policy']='strict-origin-when-cross-origin'
    res.headers['Permissions-Policy']='camera=(), microphone=(), geolocation=()'
    res.headers['Content-Security-Policy']=f"default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'nonce-{request.state.csp_nonce}'; connect-src 'self'; font-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'self'"
    if IS_PROD: res.headers['Strict-Transport-Security']='max-age=31536000; includeSubDomains'
    return res

@app.get('/',response_class=HTMLResponse)
def home(request:Request):
    with db() as c:
        entries=[dict(x) for x in c.execute('SELECT * FROM portfolio WHERE published=1 ORDER BY is_illustration ASC, id DESC LIMIT 4')]
    return render(request,'home.html',entries=entries,home=True)

@app.get('/entreprise',response_class=HTMLResponse)
def about(request:Request):
    return render(request,'about.html',title='Notre entreprise | TGCA SARL.AU',description='Découvrez TGCA SARL.AU, entreprise marocaine de construction de bâtiments, résidences et villas.')

@app.get('/expertises',response_class=HTMLResponse)
def expertises(request:Request):
    return render(request,'services.html',title='Nos expertises BTP | TGCA SARL.AU')

@app.get('/realisations',response_class=HTMLResponse)
def realisations(request:Request,category:str='Tous'):
    with db() as c:
        if category in PORTFOLIO_CATEGORIES:
            rows=c.execute('SELECT * FROM portfolio WHERE published=1 AND category=? ORDER BY is_illustration ASC,id DESC',(category,)).fetchall()
        else:
            rows=c.execute('SELECT * FROM portfolio WHERE published=1 ORDER BY is_illustration ASC,id DESC').fetchall()
    return render(request,'portfolio.html',entries=[dict(x) for x in rows],filter=category,title='Projets et inspirations | TGCA SARL.AU')

@app.get('/realisations/{slug}',response_class=HTMLResponse)
def realisation(request:Request,slug:str):
    with db() as c: item=c.execute('SELECT * FROM portfolio WHERE slug=? AND published=1',(slug,)).fetchone()
    if not item: raise HTTPException(404,'Projet introuvable')
    return render(request,'portfolio_detail.html',item=dict(item),title=str(item['title'])+' | TGCA SARL.AU')

@app.get('/plans-3d',response_class=HTMLResponse)
def plans_3d(request:Request, categorie:str='tous'):
    cats={'tous','villa','appartement','riad','immeuble'}
    categorie=categorie if categorie in cats else 'tous'
    plans=[p for p in PLANS_3D if categorie=='tous' or p['family']==categorie]
    return render(request,'plans_3d.html',plans=plans,hide_cta=True,selected=categorie,
                  title='Plans 3D : villas, appartements et immeubles | TGCA',
                  description='Découvrez les plans 3D isométriques de villas, appartements, riads et immeubles imaginés pour vos projets au Maroc.')

@app.get('/plans-3d/{slug}',response_class=HTMLResponse)
def plan_3d_detail(request:Request,slug:str):
    plan=next((p for p in PLANS_3D if p['slug']==slug),None)
    if plan is None: raise HTTPException(status_code=404,detail='Plan introuvable')
    return render(request,'plan_3d_detail.html',plan=plan,
                  title=plan['title']+' | Plan 3D TGCA',
                  description=plan['desc'])

@app.get('/devis',response_class=HTMLResponse)
def devis(request:Request):
    return render(request,'contact.html',quote=True,title='Demander un devis | TGCA SARL.AU')

@app.get('/contact',response_class=HTMLResponse)
def contact(request:Request):
    return render(request,'contact.html',quote=False,title='Contact | TGCA SARL.AU')

# Basic rate limit, in addition to the honeypot and CSRF checks.
_limits={}
_auth_limits={}
def rate_limited(ip):
    clock=time.monotonic()
    recent=[t for t in _limits.get(ip,[]) if clock-t<1800]
    if len(recent)>=6: return True
    recent.append(clock)
    _limits[ip]=recent
    if len(_limits)>10000:
        for key in list(_limits)[:4000]: _limits.pop(key,None)
    return False

@app.post('/contact')
def contact_submit(request:Request,csrf:str=Form(''),name:str=Form(''),email:str=Form(''),phone:str=Form(''),project_type:str=Form(''),city:str=Form(''),budget:str=Form(''),message:str=Form(''),consent:str=Form(''),website:str=Form('')):
    check_csrf(request,csrf)
    if website: return RedirectResponse('/merci',303)   # spam honeypot
    if rate_limited(request.client.host if request.client else 'unknown'):
        raise HTTPException(429,'Trop de demandes, veuillez réessayer ultérieurement.')
    name=name.strip(); email=email.strip().lower(); phone=phone.strip(); message=message.strip()
    valid_email=bool(re.fullmatch(r'[^\s@]{1,100}@[^\s@]{1,100}\.[^\s@]{2,30}',email))
    errors={}
    if not 2<=len(name)<=120: errors['name']='Indiquez votre nom (2 caractères minimum).'
    if not valid_email: errors['email']='Adresse e-mail invalide.'
    if not (6<=len(phone)<=35 and len(re.sub(r'\D','',phone))>=6): errors['phone']='Numéro de téléphone invalide.'
    if not 10<=len(message)<=4000: errors['message']='Décrivez votre projet en quelques mots (10 caractères minimum).'
    if consent!='yes': errors['consent']='Votre accord est nécessaire pour traiter la demande.'
    if errors:
        form=dict(name=name,email=email,phone=phone,project_type=project_type,city=city,budget=budget,message=message)
        return render(request,'contact.html',status_code=422,quote=True,errors=errors,form=form,
                      error='Certains champs sont à corriger : ils sont signalés ci-dessous.',title='Demander un devis | TGCA SARL.AU')
    with db() as c:
        c.execute('INSERT INTO leads(name,email,phone,project_type,city,budget,message,consent,created_at) VALUES(?,?,?,?,?,?,?,?,?)',
                  (name,email,phone,project_type[:100],city[:100],budget[:80],message,1,now()))
    notify_lead(name,email,phone,project_type,city,message)
    return RedirectResponse('/merci',303)

def notify_lead(name,email,phone,project_type,city,message):
    address=os.getenv('NOTIFICATION_EMAIL') or CONTACT['email']
    smtp_host=os.getenv('SMTP_HOST')
    if not address or not smtp_host: return
    try:
        em=EmailMessage(); em['To']=address; em['From']=os.getenv('SMTP_FROM',address); em['Subject']=f'[TGCA] Nouvelle demande : {project_type or "projet"} — {name}'[:150]; em['Reply-To']=email
        em.set_content(f'Nom : {name}\nEmail : {email}\nTéléphone : {phone}\nProjet : {project_type}\nVille : {city}\n\n{message}')
        with smtplib.SMTP(smtp_host,int(os.getenv('SMTP_PORT',587)),timeout=12) as s:
            s.starttls()
            if os.getenv('SMTP_USER'): s.login(os.getenv('SMTP_USER'),os.getenv('SMTP_PASSWORD',''))
            s.send_message(em)
    except Exception: logging.exception('Notification email non transmise ; demande sauvegardée en base.')

@app.get('/merci',response_class=HTMLResponse)
def thanks(request:Request): return render(request,'thanks.html',title='Merci pour votre demande | TGCA SARL.AU')

@app.get('/mentions-legales',response_class=HTMLResponse)
def legal(request:Request): return render(request,'legal.html',title='Mentions légales | TGCA SARL.AU')

@app.get('/confidentialite',response_class=HTMLResponse)
def privacy(request:Request): return render(request,'privacy.html',title='Confidentialité | TGCA SARL.AU')

@app.get('/robots.txt',response_class=PlainTextResponse)
def robots(request:Request):
    return f'User-agent: *\nDisallow: /admin\nDisallow: /espace-client\nDisallow: /connexion\nDisallow: /mon-compte\nDisallow: /documents\nSitemap: {site_url(request)}/sitemap.xml\n'

@app.get('/sitemap.xml')
def sitemap(request:Request):
    base=site_url(request)
    urls=['/','/entreprise','/expertises','/realisations','/plans-3d','/contact','/devis','/mentions-legales','/confidentialite']
    urls += ['/plans-3d/'+p['slug'] for p in PLANS_3D]
    with db() as c: urls += ['/realisations/'+x['slug'] for x in c.execute('SELECT slug FROM portfolio WHERE published=1')]
    xml='<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join('<url><loc>'+base+u+'</loc></url>' for u in urls)+'</urlset>'
    return Response(xml,media_type='application/xml')

@app.get('/connexion',response_class=HTMLResponse)
def login(request:Request,next:str=''):
    if get_user(request): return RedirectResponse('/admin' if get_user(request)['role']=='admin' else '/espace-client',303)
    next = next if next.startswith('/') and not next.startswith('//') else ''
    return render(request,'login.html',private=True,next=next,title='Connexion sécurisée | TGCA')

@app.post('/connexion')
def login_post(request:Request,csrf:str=Form(''),email:str=Form(''),password:str=Form(''),next:str=Form('')):
    check_csrf(request,csrf)
    ip=(request.client.host if request.client else 'unknown')
    current=time.monotonic()
    tries=[t for t in _auth_limits.get(ip,[]) if current-t<900]
    if len(tries)>=12: raise HTTPException(429,'Trop de tentatives de connexion.')
    with db() as c: row=c.execute('SELECT * FROM users WHERE email=?',(email.strip().lower(),)).fetchone()
    if not row or not verify_password(password,row['password_hash']):
        tries.append(current); _auth_limits[ip]=tries
        return render(request,'login.html',private=True,error='Identifiants invalides.',next='',title='Connexion | TGCA',status_code=200)
    _auth_limits.pop(ip,None)
    request.session.clear(); request.session['uid']=int(row['id'])
    path=next if next.startswith('/') and not next.startswith('//') else ('/admin' if row['role']=='admin' else '/espace-client')
    if path.startswith('/admin') and row['role']!='admin': path='/espace-client'
    return RedirectResponse(path,303)

@app.post('/deconnexion')
def logout(request:Request,csrf:str=Form('')):
    check_csrf(request,csrf)
    request.session.clear()
    return RedirectResponse('/',303)

@app.get('/espace-client',response_class=HTMLResponse)
def client_portal(request:Request):
    user=require_role(request,'client')
    with db() as c:
        projects=[dict(x) for x in c.execute('SELECT * FROM projects WHERE client_id=? ORDER BY updated_at DESC',(user['id'],))]
        for p in projects:
            p['tasks']=[dict(t) for t in c.execute('SELECT * FROM tasks WHERE project_id=? ORDER BY id',(p['id'],))]
            p['attachments']=[dict(a) for a in c.execute('SELECT * FROM attachments WHERE project_id=? ORDER BY id',(p['id'],))]
    return render(request,'client.html',projects=projects,private=True,pw_ok=request.query_params.get('mdp')=='ok',title='Mes projets | TGCA SARL.AU')

LEAD_STATUSES=('nouveau','en cours','traité','archivé')

def gallery_images():
    return sorted(p.name for p in (ROOT/'static'/'img').glob('*.webp'))

@app.get('/admin',response_class=HTMLResponse)
def admin(request:Request,statut:str=''):
    require_role(request)
    statut=statut if statut in LEAD_STATUSES else ''
    with db() as c:
        counts=dict(leads=c.execute('SELECT COUNT(*) n FROM leads').fetchone()['n'],new=c.execute("SELECT COUNT(*) n FROM leads WHERE status='nouveau'").fetchone()['n'],projects=c.execute('SELECT COUNT(*) n FROM projects').fetchone()['n'],customers=c.execute("SELECT COUNT(*) n FROM users WHERE role='client'").fetchone()['n'])
        if statut:
            leads=[dict(x) for x in c.execute('SELECT * FROM leads WHERE status=? ORDER BY id DESC LIMIT 100',(statut,))]
        else:
            leads=[dict(x) for x in c.execute("SELECT * FROM leads WHERE status!='archivé' ORDER BY id DESC LIMIT 100")]
        projects=[dict(x) for x in c.execute('SELECT p.*,u.name client_name FROM projects p LEFT JOIN users u ON p.client_id=u.id ORDER BY p.updated_at DESC LIMIT 50')]
        customers=[dict(x) for x in c.execute("SELECT u.id,u.name,u.email,(SELECT COUNT(*) FROM projects p WHERE p.client_id=u.id) nb FROM users u WHERE role='client' ORDER BY id DESC")]
        portfolio=[dict(x) for x in c.execute('SELECT * FROM portfolio ORDER BY id DESC')]
        activity=[dict(x) for x in c.execute('SELECT a.*,u.name actor FROM activity a LEFT JOIN users u ON u.id=a.actor_id ORDER BY a.id DESC LIMIT 12')]
    return render(request,'admin.html',counts=counts,leads=leads,projects=projects,customers=customers,entries=portfolio,activity=activity,
                  statut=statut,statuses=LEAD_STATUSES,images=gallery_images(),msg=request.query_params.get('msg',''),private=True,title='Administration | TGCA')

def _csv_safe(value):
    text='' if value is None else str(value)
    return "'"+text if text[:1] in ('=','+','-','@','\t','\r') else text

@app.get('/admin/demandes.csv')
def export_leads(request:Request):
    admin=require_role(request)
    buf=io.StringIO(); buf.write('﻿')
    w=csv.writer(buf,delimiter=';')
    w.writerow(['Date','Nom','Email','Téléphone','Type de projet','Ville','Budget','Message','Statut'])
    with db() as c:
        for l in c.execute('SELECT * FROM leads ORDER BY id DESC'):
            w.writerow([_csv_safe(l[k]) for k in ('created_at','name','email','phone','project_type','city','budget','message','status')])
    audit(admin['id'],'export','leads',0)
    name='TGCA-demandes-'+datetime.now().strftime('%Y-%m-%d')+'.csv'
    return Response(buf.getvalue(),media_type='text/csv; charset=utf-8',headers={'Content-Disposition':f'attachment; filename="{name}"','Cache-Control':'no-store'})

@app.post('/admin/clients/{client_id}/password')
def reset_client_password(request:Request,client_id:int,csrf:str=Form(''),password:str=Form('')):
    admin=require_role(request); check_csrf(request,csrf)
    if len(password)<12: raise HTTPException(400,'Mot de passe de 12 caractères minimum requis.')
    with db() as c:
        cur=c.execute("UPDATE users SET password_hash=? WHERE id=? AND role='client'",(password_hash(password),client_id))
        if not cur.rowcount: raise HTTPException(404,'Client introuvable')
    audit(admin['id'],'réinitialisation mot de passe','client',client_id)
    return RedirectResponse('/admin?msg=mdp#clients',303)

@app.post('/admin/clients/{client_id}/delete')
def delete_client(request:Request,client_id:int,csrf:str=Form('')):
    admin=require_role(request); check_csrf(request,csrf)
    with db() as c:
        if not c.execute("SELECT id FROM users WHERE id=? AND role='client'",(client_id,)).fetchone(): raise HTTPException(404,'Client introuvable')
        c.execute('UPDATE projects SET client_id=NULL WHERE client_id=?',(client_id,))
        c.execute('UPDATE activity SET actor_id=NULL WHERE actor_id=?',(client_id,))
        c.execute('DELETE FROM users WHERE id=?',(client_id,))
    audit(admin['id'],'suppression','client',client_id)
    return RedirectResponse('/admin?msg=client#clients',303)

def _remove_upload(stored_name):
    try: (UPLOADS/Path(stored_name).name).unlink(missing_ok=True)
    except OSError: logging.exception('Suppression de fichier impossible')

@app.post('/admin/projets/{project_id}/delete')
def delete_project(request:Request,project_id:int,csrf:str=Form('')):
    admin=require_role(request); check_csrf(request,csrf)
    with db() as c:
        if not c.execute('SELECT id FROM projects WHERE id=?',(project_id,)).fetchone(): raise HTTPException(404,'Projet introuvable')
        files=[r['stored_name'] for r in c.execute('SELECT stored_name FROM attachments WHERE project_id=?',(project_id,))]
        c.execute('DELETE FROM projects WHERE id=?',(project_id,))
    for f in files: _remove_upload(f)
    audit(admin['id'],'suppression','projet',project_id)
    return RedirectResponse('/admin?msg=projet#projets',303)

@app.post('/admin/documents/{file_id}/delete')
def delete_document(request:Request,file_id:int,csrf:str=Form('')):
    admin=require_role(request); check_csrf(request,csrf)
    with db() as c:
        doc=c.execute('SELECT project_id,stored_name FROM attachments WHERE id=?',(file_id,)).fetchone()
        if not doc: raise HTTPException(404,'Document introuvable')
        c.execute('DELETE FROM attachments WHERE id=?',(file_id,))
        c.execute('UPDATE projects SET updated_at=? WHERE id=?',(now(),doc['project_id']))
    _remove_upload(doc['stored_name'])
    audit(admin['id'],'suppression','document',file_id)
    return RedirectResponse(f'/admin/projets/{doc["project_id"]}#documents',303)

@app.get('/mon-compte/mot-de-passe',response_class=HTMLResponse)
def password_page(request:Request):
    user=get_user(request)
    if not user: return RedirectResponse('/connexion?next=/mon-compte/mot-de-passe',303)
    return render(request,'password.html',private=True,title='Changer mon mot de passe | TGCA')

@app.post('/mon-compte/mot-de-passe')
def password_change(request:Request,csrf:str=Form(''),current:str=Form(''),new:str=Form(''),confirm:str=Form('')):
    user=get_user(request)
    if not user: raise HTTPException(403)
    check_csrf(request,csrf)
    with db() as c: row=c.execute('SELECT password_hash FROM users WHERE id=?',(user['id'],)).fetchone()
    error=''
    if not verify_password(current,row['password_hash']): error='Le mot de passe actuel est incorrect.'
    elif len(new)<12: error='Le nouveau mot de passe doit contenir au moins 12 caractères.'
    elif new!=confirm: error='Les deux nouveaux mots de passe ne correspondent pas.'
    elif new==current: error='Choisissez un mot de passe différent de l\'actuel.'
    if error: return render(request,'password.html',status_code=422,error=error,private=True,title='Changer mon mot de passe | TGCA')
    with db() as c: c.execute('UPDATE users SET password_hash=? WHERE id=?',(password_hash(new),user['id']))
    audit(user['id'],'changement mot de passe','utilisateur',user['id'])
    return RedirectResponse(('/admin?msg=mdp' if user['role']=='admin' else '/espace-client?mdp=ok'),303)

@app.post('/admin/leads/{lead_id}/status')
def lead_status(request:Request,lead_id:int,csrf:str=Form(''),status:str=Form('')):
    admin=require_role(request); check_csrf(request,csrf)
    if status not in ('nouveau','en cours','traité','archivé'): raise HTTPException(400,'Statut invalide')
    with db() as c:
        if not c.execute('SELECT id FROM leads WHERE id=?',(lead_id,)).fetchone(): raise HTTPException(404)
        c.execute('UPDATE leads SET status=? WHERE id=?',(status,lead_id))
    audit(admin['id'],'changement de statut','lead',lead_id)
    return RedirectResponse('/admin#demandes',303)

@app.post('/admin/clients')
def create_client(request:Request,csrf:str=Form(''),name:str=Form(''),email:str=Form(''),password:str=Form('')):
    admin=require_role(request); check_csrf(request,csrf)
    name=name.strip(); email=email.strip().lower()
    if not name or len(password)<12 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email): raise HTTPException(400,'Nom, email et mot de passe de 12 caractères minimum requis.')
    try:
        with db() as c:
            cur=c.execute("INSERT INTO users(email,name,password_hash,role,created_at) VALUES (?,?,?,'client',?)",(email,name,password_hash(password),now()))
            client_id=cur.lastrowid
    except sqlite3.IntegrityError: raise HTTPException(409,'Adresse email déjà utilisée.')
    audit(admin['id'],'création','client',client_id)
    return RedirectResponse('/admin#clients',303)

@app.post('/admin/projets')
def create_project(request:Request,csrf:str=Form(''),title:str=Form(''),description:str=Form(''),client_id:str=Form(''),location:str=Form(''),due_date:str=Form('')):
    admin=require_role(request); check_csrf(request,csrf)
    if not title.strip(): raise HTTPException(400,'Titre requis')
    client=None
    if client_id.isdigit():
        client=int(client_id)
        with db() as c:
            if not c.execute("SELECT id FROM users WHERE id=? AND role='client'",(client,)).fetchone(): raise HTTPException(400,'Client non trouvé')
    reference='TGCA-'+datetime.now().strftime('%Y')+'-'+secrets.token_hex(3).upper()
    with db() as c:
        cur=c.execute('INSERT INTO projects(reference,title,description,client_id,location,due_date,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)',
                      (reference,title.strip()[:160],description.strip()[:4000],client,location.strip()[:120],due_date or None,now(),now()))
        pid=cur.lastrowid
    audit(admin['id'],'création','projet',pid)
    return RedirectResponse(f'/admin/projets/{pid}',303)

@app.get('/admin/projets/{project_id}',response_class=HTMLResponse)
def edit_project(request:Request,project_id:int):
    require_role(request)
    with db() as c:
        p=c.execute('SELECT * FROM projects WHERE id=?',(project_id,)).fetchone()
        if not p: raise HTTPException(404,'Projet introuvable')
        tasks=[dict(x) for x in c.execute('SELECT * FROM tasks WHERE project_id=? ORDER BY id',(project_id,))]
        files=[dict(x) for x in c.execute('SELECT * FROM attachments WHERE project_id=? ORDER BY id',(project_id,))]
        users=[dict(x) for x in c.execute("SELECT id,name,email FROM users WHERE role='client' ORDER BY name")]
    return render(request,'project_edit.html',p=dict(p),tasks=tasks,files=files,customers=users,private=True,title='Suivi de projet | TGCA')

@app.post('/admin/projets/{project_id}')
def update_project(request:Request,project_id:int,csrf:str=Form(''),title:str=Form(''),description:str=Form(''),status:str=Form(''),progress:int=Form(0),client_id:str=Form(''),location:str=Form(''),due_date:str=Form('')):
    admin=require_role(request);check_csrf(request,csrf)
    if status not in ('étude','planification','en cours','en attente','terminé') or not 0<=progress<=100: raise HTTPException(400,'Statut ou avancement invalide')
    client=int(client_id) if client_id.isdigit() else None
    with db() as c:
        if client and not c.execute("SELECT id FROM users WHERE id=? AND role='client'",(client,)).fetchone(): raise HTTPException(400,'Client invalide')
        cur=c.execute('UPDATE projects SET title=?,description=?,status=?,progress=?,client_id=?,location=?,due_date=?,updated_at=? WHERE id=?',
                      (title.strip()[:160],description.strip()[:4000],status,progress,client,location.strip()[:120],due_date or None,now(),project_id))
        if not cur.rowcount: raise HTTPException(404)
    audit(admin['id'],'modification','projet',project_id)
    return RedirectResponse(f'/admin/projets/{project_id}?ok=1',303)

@app.post('/admin/projets/{project_id}/tasks')
def add_task(request:Request,project_id:int,csrf:str=Form(''),title:str=Form(''),due_date:str=Form('')):
    admin=require_role(request);check_csrf(request,csrf)
    if not title.strip(): raise HTTPException(400)
    with db() as c:
        if not c.execute('SELECT id FROM projects WHERE id=?',(project_id,)).fetchone(): raise HTTPException(404)
        cur=c.execute('INSERT INTO tasks(project_id,title,due_date,created_at) VALUES (?,?,?,?)',(project_id,title.strip()[:180],due_date or None,now()))
    audit(admin['id'],'création','tâche',cur.lastrowid)
    return RedirectResponse(f'/admin/projets/{project_id}#taches',303)

@app.post('/admin/tasks/{task_id}/toggle')
def toggle_task(request:Request,task_id:int,csrf:str=Form('')):
    admin=require_role(request); check_csrf(request,csrf)
    with db() as c:
        t=c.execute('SELECT project_id FROM tasks WHERE id=?',(task_id,)).fetchone()
        if not t: raise HTTPException(404)
        c.execute('UPDATE tasks SET done=1-done WHERE id=?',(task_id,))
    audit(admin['id'],'validation','tâche',task_id)
    return RedirectResponse(f'/admin/projets/{t["project_id"]}#taches',303)

@app.post('/admin/tasks/{task_id}/delete')
def delete_task(request:Request,task_id:int,csrf:str=Form('')):
    admin=require_role(request);check_csrf(request,csrf)
    with db() as c:
        t=c.execute('SELECT project_id FROM tasks WHERE id=?',(task_id,)).fetchone()
        if not t: raise HTTPException(404)
        c.execute('DELETE FROM tasks WHERE id=?',(task_id,))
    audit(admin['id'],'suppression','tâche',task_id)
    return RedirectResponse(f'/admin/projets/{t["project_id"]}#taches',303)

MIMES={'application/pdf':'.pdf','image/jpeg':'.jpg','image/png':'.png','image/webp':'.webp'}
@app.post('/admin/projets/{project_id}/files')
async def upload_file(request:Request,project_id:int,csrf:str=Form(''),attachment:UploadFile=File(...)):
    admin=require_role(request);check_csrf(request,csrf)
    with db() as c:
        if not c.execute('SELECT id FROM projects WHERE id=?',(project_id,)).fetchone(): raise HTTPException(404)
    if attachment.content_type not in MIMES: raise HTTPException(400,'Seuls les PDF et images JPG, PNG, WebP sont acceptés.')
    data=await attachment.read(8*1024*1024+1)
    if len(data)>8*1024*1024: raise HTTPException(413,'Maximum 8 Mo par fichier.')
    # Verify file signatures, not only the user-provided MIME.
    mime=attachment.content_type
    magic_ok= (mime=='application/pdf' and data.startswith(b'%PDF-')) or (mime=='image/jpeg' and data.startswith(b'\xff\xd8\xff')) or (mime=='image/png' and data.startswith(b'\x89PNG\r\n\x1a\n')) or (mime=='image/webp' and data[:4]==b'RIFF' and data[8:12]==b'WEBP')
    if not magic_ok: raise HTTPException(400,'Le contenu du fichier ne correspond pas au type autorisé.')
    saved=uuid.uuid4().hex+MIMES[mime]
    (UPLOADS/saved).write_bytes(data)
    filename=Path(attachment.filename or 'document').name[:180]
    with db() as c:
        cur=c.execute('INSERT INTO attachments(project_id,filename,stored_name,mime,size,created_at) VALUES (?,?,?,?,?,?)',
                  (project_id,filename,saved,mime,len(data),now()))
    audit(admin['id'],'ajout','document',cur.lastrowid)
    return RedirectResponse(f'/admin/projets/{project_id}#documents',303)

@app.get('/documents/{file_id}')
def download_attachment(request:Request,file_id:int):
    user=get_user(request)
    if not user: raise HTTPException(403)
    with db() as c:
        doc=c.execute('SELECT a.*,p.client_id FROM attachments a JOIN projects p ON p.id=a.project_id WHERE a.id=?',(file_id,)).fetchone()
    if not doc: raise HTTPException(404)
    if user['role']!='admin' and doc['client_id']!=user['id']: raise HTTPException(403)
    path=UPLOADS/doc['stored_name']
    if not path.exists(): raise HTTPException(404)
    return FileResponse(path,filename=doc['filename'],media_type=doc['mime'],content_disposition_type='attachment')

@app.post('/admin/portfolio')
async def create_portfolio(request:Request,csrf:str=Form(''),title:str=Form(''),city:str=Form(''),category:str=Form(''),description:str=Form(''),image:str=Form(''),is_illustration:str=Form(''),photo:UploadFile|None=File(None)):
    admin=require_role(request);check_csrf(request,csrf)
    approved=set(gallery_images())
    if category not in PORTFOLIO_CATEGORIES: category='Bâtiment'
    if not title.strip() or (image not in approved and not (photo and photo.filename)): raise HTTPException(400,'Titre et image sont requis')
    if photo and photo.filename:
        if photo.content_type not in ('image/jpeg','image/png','image/webp'):
            raise HTTPException(400,'Photo non autorisée : utiliser JPG, PNG ou WebP')
        content=await photo.read(5*1024*1024+1)
        if len(content)>5*1024*1024:
            raise HTTPException(413,'Photo trop volumineuse : 5 Mo maximum')
        mime=photo.content_type
        okay=(mime=='image/jpeg' and content[:3]==b'\xff\xd8\xff') or (mime=='image/png' and content.startswith(b'\x89PNG\r\n\x1a\n')) or (mime=='image/webp' and content[:4]==b'RIFF' and content[8:12]==b'WEBP')
        if not okay: raise HTTPException(400,'Fichier image invalide')
        suffix={'image/jpeg':'.jpg','image/png':'.png','image/webp':'.webp'}[mime]
        filename=uuid.uuid4().hex+suffix
        (PUBLIC_MEDIA/filename).write_bytes(content)
        image='upload/'+filename
    slug=re.sub('[^a-z0-9]+','-',title.lower().strip()).strip('-')+'-'+secrets.token_hex(2)
    with db() as c:
        cur=c.execute('INSERT INTO portfolio(slug,title,city,category,image,description,is_illustration,published,created_at) VALUES(?,?,?,?,?,?,?,1,?)',
                      (slug,title.strip()[:150],city.strip()[:90],category[:40],image,description.strip()[:1500],int(is_illustration=='yes'),now()))
    audit(admin['id'],'création','portfolio',cur.lastrowid)
    return RedirectResponse('/admin#portfolio',303)

@app.post('/admin/portfolio/{entry_id}/toggle')
def toggle_portfolio(request:Request,entry_id:int,csrf:str=Form('')):
    admin=require_role(request);check_csrf(request,csrf)
    with db() as c:
        cur=c.execute('UPDATE portfolio SET published=1-published WHERE id=?',(entry_id,))
        if not cur.rowcount: raise HTTPException(404)
    audit(admin['id'],'publication','portfolio',entry_id)
    return RedirectResponse('/admin#portfolio',303)

@app.post('/admin/portfolio/{entry_id}/delete')
def delete_portfolio(request:Request,entry_id:int,csrf:str=Form('')):
    admin=require_role(request);check_csrf(request,csrf)
    with db() as c:
        row=c.execute('SELECT image FROM portfolio WHERE id=?',(entry_id,)).fetchone()
        if not row: raise HTTPException(404,'Contenu introuvable')
        c.execute('DELETE FROM portfolio WHERE id=?',(entry_id,))
    if row['image'].startswith('upload/'):
        try: (PUBLIC_MEDIA/Path(row['image'][7:]).name).unlink(missing_ok=True)
        except OSError: logging.exception('Suppression de la photo impossible')
    audit(admin['id'],'suppression','portfolio',entry_id)
    return RedirectResponse('/admin?msg=galerie#portfolio',303)

@app.get('/health',response_class=PlainTextResponse)
def health(): return 'ok'
