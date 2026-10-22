"""End-to-end HTTP tests of public pages, leads, admin and client isolation."""
import io
import re
import pytest
from fastapi.testclient import TestClient
import app as site

@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr(site,'DATABASE',tmp_path/'tgca_test.db')
    monkeypatch.setattr(site,'UPLOADS',tmp_path/'uploads')
    site.UPLOADS.mkdir()
    site.init_db()
    site._limits.clear()
    with TestClient(site.app,follow_redirects=False) as c:
        yield c

def csrf(client,path='/contact'):
    html=client.get(path).text
    return re.search(r'name="csrf" value="([^\"]+)"',html).group(1)

def admin_user():
    with site.db() as c:
        c.execute("INSERT INTO users(email,name,password_hash,role,created_at) VALUES (?,?,?,?,?)",('admin@example.ma','Admin TGCA',site.password_hash('safepassword012345'),'admin',site.now()))

def login(client,email='admin@example.ma',pw='safepassword012345'):
    tok=csrf(client,'/connexion')
    return client.post('/connexion',data={'csrf':tok,'email':email,'password':pw})

@pytest.mark.parametrize('path', ['/','/entreprise','/expertises','/realisations','/realisations/villa-contemporaine','/devis','/contact','/mentions-legales','/confidentialite','/sitemap.xml','/robots.txt'])
def test_public_pages(client,path):
    response=client.get(path)
    assert response.status_code==200,(path,response.text[:300])

def test_contact_form_saved_and_escaped(client):
    tok=csrf(client)
    content={'csrf':tok,'name':'Amina Test','email':'AMINA@EXAMPLE.MA','phone':'0661234567','project_type':'Villa haut standing','city':'Salé','budget':'1 500 000 à 5 000 000 DH','message':'Je souhaite construire une villa moderne.','consent':'yes'}
    r=client.post('/contact',data=content)
    assert r.status_code==303 and r.headers['location']=='/merci'
    with site.db() as c:
        row=c.execute('SELECT * FROM leads').fetchone()
        assert row and row['name']=='Amina Test' and row['email']=='amina@example.ma' and row['consent']==1
    r=client.post('/contact',data={**content,'csrf':'bad'})
    assert r.status_code==403

def test_contact_validation(client):
    token=csrf(client)
    r=client.post('/contact',data={'csrf':token,'name':'A','email':'a@b.ma','phone':'1234','message':'tiny','consent':''})
    assert r.status_code==422 and 'corriger' in r.text
    # La saisie est conservée et chaque champ fautif est signalé.
    assert 'value="a@b.ma"' in r.text and '>tiny</textarea>' in r.text
    assert 'aria-invalid="true"' in r.text and 'Numéro de téléphone invalide' in r.text
    with site.db() as c: assert c.execute('SELECT COUNT(*) n FROM leads').fetchone()['n']==0

def test_access_control(client):
    assert client.get('/admin').status_code==303
    assert client.get('/espace-client').status_code==303
    assert client.get('/documents/1').status_code==403

def test_admin_project_and_client_private_portal(client):
    admin_user()
    assert login(client).status_code==303
    page=client.get('/admin'); assert page.status_code==200
    token=csrf(client,'/admin')
    r=client.post('/admin/clients',data={'csrf':token,'name':'Client 1','email':'client1@test.ma','password':'clientPassword123!'}); assert r.status_code==303
    r=client.post('/admin/clients',data={'csrf':token,'name':'Client 2','email':'client2@test.ma','password':'clientPassword456!'}); assert r.status_code==303
    with site.db() as c:
        cid=c.execute("SELECT id FROM users WHERE email='client1@test.ma'").fetchone()['id']
    r=client.post('/admin/projets',data={'csrf':token,'title':'Construction villa Rabat','description':'Gros œuvre et second œuvre','client_id':str(cid),'location':'Rabat','due_date':'2027-08-30'})
    assert r.status_code==303
    m=re.search(r'^/admin/projets/(\d+)$',r.headers['location']); assert m
    pid=int(m.group(1))
    r=client.post(f'/admin/projets/{pid}',data={'csrf':token,'title':'Villa Rabat','description':'Projet suivi','client_id':str(cid),'status':'en cours','progress':'45','location':'Rabat','due_date':'2027-08-30'})
    assert r.status_code==303
    assert client.post(f'/admin/projets/{pid}/tasks',data={'csrf':token,'title':'Fondations'}).status_code==303
    assert client.post(f'/admin/projets/{pid}/files',data={'csrf':token},files={'attachment':('plan.pdf',b'%PDF-1.4\n1 0 obj\n','application/pdf')}).status_code==303
    with site.db() as c: docid=c.execute('SELECT id FROM attachments').fetchone()['id']
    assert client.get(f'/documents/{docid}').status_code==200
    logout_csrf=csrf(client,'/admin')
    client.post('/deconnexion',data={'csrf':logout_csrf})
    assert login(client,email='client1@test.ma',pw='clientPassword123!').status_code==303
    page=client.get('/espace-client'); assert 'Villa Rabat' in page.text and '45 %' in page.text
    assert client.get('/admin').status_code==403
    assert client.get(f'/documents/{docid}').status_code==200
    tok=csrf(client,'/espace-client')
    client.post('/deconnexion',data={'csrf':tok})
    assert login(client,email='client2@test.ma',pw='clientPassword456!').status_code==303
    page=client.get('/espace-client'); assert 'Villa Rabat' not in page.text
    assert client.get(f'/documents/{docid}').status_code==403

def test_portfolio_toggle_and_security(client):
    admin_user(); login(client)
    tok=csrf(client,'/admin')
    assert client.post('/admin/portfolio',data={'csrf':tok,'title':'Résidence Test','city':'Salé','category':'Immeuble','image':'residence.webp','description':'Exemple','is_illustration':'yes'}).status_code==303
    r=client.get('/realisations'); assert 'Résidence Test' in r.text
    assert client.post('/admin/portfolio',data={'csrf':tok,'title':'Hack','city':'','category':'Villa','image':'../../etc/passwd'}).status_code==400

def test_public_portfolio_photo_upload(client,tmp_path,monkeypatch):
    admin_user();assert login(client).status_code==303
    tok=csrf(client,'/admin')
    tiny_png=(b'\x89PNG\r\n\x1a\n'+b'\x00'*25)
    response=client.post('/admin/portfolio',data={'csrf':tok,'title':'Résidence documentée','city':'Salé','category':'Immeuble','description':'Projet illustré','is_illustration':'no','image':'residence.webp'},files={'photo':('residence.png',tiny_png,'image/png')})
    assert response.status_code==303
    with site.db() as c:
        entry=c.execute("SELECT * FROM portfolio WHERE title='Résidence documentée'").fetchone()
        assert entry['image'].startswith('upload/') and entry['is_illustration']==0
    public=client.get('/realisations')
    assert '/media/'+entry['image'][7:] in public.text
    media_path=site.PUBLIC_MEDIA / entry['image'][7:]
    assert media_path.exists()
    try:
        media=client.get('/media/'+entry['image'][7:]); assert media.status_code==200
    finally:
        media_path.unlink(missing_ok=True)
