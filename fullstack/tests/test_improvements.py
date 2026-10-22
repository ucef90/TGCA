"""Tests des améliorations : sécurité de la clé, pages d'erreur, export, suppressions, mot de passe."""
import subprocess
import sys
from pathlib import Path

import pytest
import app as site
from tests.test_app import client, csrf, admin_user, login  # noqa: F401  (fixture réutilisée)

ROOT = Path(__file__).resolve().parents[1]


def _boot(env):
    code = 'import app'
    return subprocess.run([sys.executable, '-c', code], cwd=ROOT, env=env, capture_output=True, text=True)


@pytest.mark.parametrize('secret', ['REMPLACER_PAR_UNE_CLE_ALEATOIRE_LONGUE', 'court', ''])
def test_production_refuses_weak_secret(secret, tmp_path):
    env = {'PATH': '/usr/bin:/bin', 'ENVIRONMENT': 'production', 'SESSION_SECRET': secret,
           'TGCA_DATA_DIR': str(tmp_path), 'PYTHONPATH': str(ROOT)}
    r = _boot(env)
    assert r.returncode != 0 and 'SESSION_SECRET' in r.stderr


def test_production_accepts_strong_secret(tmp_path):
    env = {'PATH': '/usr/bin:/bin', 'ENVIRONMENT': 'production', 'SESSION_SECRET': 'x' * 48,
           'TGCA_DATA_DIR': str(tmp_path), 'PYTHONPATH': str(ROOT)}
    assert _boot(env).returncode == 0


def test_html_error_pages(client):
    r = client.get('/page-qui-n-existe-pas')
    assert r.status_code == 404 and 'text/html' in r.headers['content-type'] and 'Page introuvable' in r.text
    r = client.get('/realisations/inconnu')
    assert r.status_code == 404 and 'Projet introuvable' in r.text
    assert client.get('/admin').status_code == 303  # la redirection vers la connexion reste intacte


def test_seo_absolute_urls(client):
    assert 'Sitemap: http' in client.get('/robots.txt').text
    home = client.get('/').text
    assert 'FAQPage' in home and '<link rel="canonical" href="http' in home
    assert 'noindex' in client.get('/connexion').text and 'noindex' not in home


def test_leads_filter_and_csv_export(client):
    tok = csrf(client)
    client.post('/contact', data={'csrf': tok, 'name': 'Injection', 'email': 'x@test.ma', 'phone': '0661000000',
                                  'message': '=HYPERLINK("http://evil")', 'consent': 'yes'})
    admin_user(); login(client)
    assert 'Injection' in client.get('/admin?statut=nouveau').text
    assert 'Injection' not in client.get('/admin?statut=archivé').text
    r = client.get('/admin/demandes.csv')
    assert r.status_code == 200 and 'attachment' in r.headers['content-disposition']
    assert "'=HYPERLINK" in r.text  # neutralisation des formules Excel


def test_csv_export_requires_admin(client):
    assert client.get('/admin/demandes.csv').status_code == 303


def _make_project_with_file(client):
    admin_user(); login(client)
    tok = csrf(client, '/admin')
    client.post('/admin/clients', data={'csrf': tok, 'name': 'Client X', 'email': 'cx@test.ma', 'password': 'clientPassword123!'})
    with site.db() as c:
        cid = c.execute("SELECT id FROM users WHERE email='cx@test.ma'").fetchone()['id']
    r = client.post('/admin/projets', data={'csrf': tok, 'title': 'Projet X', 'client_id': str(cid)})
    pid = int(r.headers['location'].rsplit('/', 1)[1])
    client.post(f'/admin/projets/{pid}/files', data={'csrf': tok}, files={'attachment': ('p.pdf', b'%PDF-1.4\n', 'application/pdf')})
    with site.db() as c:
        doc = c.execute('SELECT * FROM attachments').fetchone()
    return tok, cid, pid, doc


def test_delete_document_and_project_remove_files(client):
    tok, cid, pid, doc = _make_project_with_file(client)
    path = site.UPLOADS / doc['stored_name']
    assert path.exists()
    assert client.post(f"/admin/documents/{doc['id']}/delete", data={'csrf': tok}).status_code == 303
    assert not path.exists()
    client.post(f'/admin/projets/{pid}/files', data={'csrf': tok}, files={'attachment': ('q.pdf', b'%PDF-1.4\n', 'application/pdf')})
    with site.db() as c:
        second = site.UPLOADS / c.execute('SELECT stored_name FROM attachments').fetchone()['stored_name']
    assert client.post(f'/admin/projets/{pid}/delete', data={'csrf': tok}).status_code == 303
    assert not second.exists()
    with site.db() as c:
        assert c.execute('SELECT COUNT(*) n FROM projects').fetchone()['n'] == 0


def test_delete_client_keeps_projects(client):
    tok, cid, pid, doc = _make_project_with_file(client)
    assert client.post(f'/admin/clients/{cid}/delete', data={'csrf': tok}).status_code == 303
    with site.db() as c:
        assert c.execute('SELECT client_id FROM projects WHERE id=?', (pid,)).fetchone()['client_id'] is None
        assert c.execute('SELECT COUNT(*) n FROM users WHERE id=?', (cid,)).fetchone()['n'] == 0


def test_client_cannot_use_admin_actions(client):
    tok, cid, pid, doc = _make_project_with_file(client)
    client.post('/deconnexion', data={'csrf': tok})
    login(client, email='cx@test.ma', pw='clientPassword123!')
    t = csrf(client, '/espace-client')
    for url in (f'/admin/projets/{pid}/delete', f"/admin/documents/{doc['id']}/delete", f'/admin/clients/{cid}/delete'):
        assert client.post(url, data={'csrf': t}).status_code == 403


def test_admin_reset_and_client_password_change(client):
    tok, cid, pid, doc = _make_project_with_file(client)
    assert client.post(f'/admin/clients/{cid}/password', data={'csrf': tok, 'password': 'court'}).status_code == 400
    assert client.post(f'/admin/clients/{cid}/password', data={'csrf': tok, 'password': 'nouveauMotDePasse2026'}).status_code == 303
    client.post('/deconnexion', data={'csrf': tok})
    assert login(client, email='cx@test.ma', pw='nouveauMotDePasse2026').headers['location'] == '/espace-client'
    t = csrf(client, '/mon-compte/mot-de-passe')
    bad = client.post('/mon-compte/mot-de-passe', data={'csrf': t, 'current': 'faux', 'new': 'unAutreMotDePasse99', 'confirm': 'unAutreMotDePasse99'})
    assert bad.status_code == 422 and 'incorrect' in bad.text
    ok = client.post('/mon-compte/mot-de-passe', data={'csrf': t, 'current': 'nouveauMotDePasse2026', 'new': 'unAutreMotDePasse99', 'confirm': 'unAutreMotDePasse99'})
    assert ok.status_code == 303
    client.post('/deconnexion', data={'csrf': t})
    assert login(client, email='cx@test.ma', pw='unAutreMotDePasse99').status_code == 303


def test_portfolio_delete_removes_uploaded_photo(client):
    admin_user(); login(client)
    tok = csrf(client, '/admin')
    png = b'\x89PNG\r\n\x1a\n' + b'\x00' * 25
    client.post('/admin/portfolio', data={'csrf': tok, 'title': 'A supprimer', 'city': 'Salé', 'category': 'Villa', 'image': 'residence.webp', 'is_illustration': 'no'},
                files={'photo': ('a.png', png, 'image/png')})
    with site.db() as c:
        e = c.execute("SELECT * FROM portfolio WHERE title='A supprimer'").fetchone()
    media = site.PUBLIC_MEDIA / e['image'][7:]
    assert media.exists()
    assert client.post(f"/admin/portfolio/{e['id']}/delete", data={'csrf': tok}).status_code == 303
    assert not media.exists() and client.get(f"/realisations/{e['slug']}").status_code == 404


def test_new_images_exist_and_gallery_seeded(client):
    img = ROOT / 'static' / 'img'
    for s in site.SERVICES:
        assert (img / s['img']).exists(), s['img']
    for row in site.SEED_V2:
        assert (img / row[4]).exists(), row[4]
    page = client.get('/realisations?category=Riad').text
    assert 'Riad à patio et bassin' in page and 'riad-patio.webp' in page
    assert 'maquette-villa-3d.webp' in client.get('/plans-3d').text


def test_seed_v2_not_reinserted_after_admin_delete(client):
    admin_user(); login(client)
    tok = csrf(client, '/admin')
    with site.db() as c:
        eid = c.execute("SELECT id FROM portfolio WHERE slug='villa-vue-atlas'").fetchone()['id']
    client.post(f'/admin/portfolio/{eid}/delete', data={'csrf': tok})
    site.init_db()
    with site.db() as c:
        assert c.execute("SELECT COUNT(*) n FROM portfolio WHERE slug='villa-vue-atlas'").fetchone()['n'] == 0
