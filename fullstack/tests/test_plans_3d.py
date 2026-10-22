from fastapi.testclient import TestClient
from app import app

client=TestClient(app)

def test_plans_gallery():
    r=client.get('/plans-3d')
    assert r.status_code==200
    assert 'villa-patio.svg' in r.text
    assert 'appartement-3-chambres' in r.text
    assert 'Plan' in r.text

def test_plans_filters():
    r=client.get('/plans-3d?categorie=riad')
    assert r.status_code==200
    assert 'riad-contemporain.svg' in r.text
    assert 'villa-patio.svg' not in r.text

def test_plan_detail():
    r=client.get('/plans-3d/villa-patio')
    assert r.status_code==200
    assert 'Grand séjour' in r.text
    assert 'non contractuelle' in r.text

def test_plan_assets():
    for slug in ('villa-patio','appartement-3-chambres','riad-contemporain','etage-residentiel'):
        svg=client.get('/static/img/plans3d/'+slug+'.svg')
        assert svg.status_code==200
        assert '<svg' in svg.text
        png=client.get('/static/img/plans3d/'+slug+'.png')
        assert png.status_code==200

def test_plan_bad_slug():
    assert client.get('/plans-3d/inconnu').status_code==404

def test_sitemap_contains_plans():
    assert '/plans-3d/villa-patio' in client.get('/sitemap.xml').text
