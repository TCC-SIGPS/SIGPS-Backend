import os
import pytest
from app import create_app
from app.extensions import db
from app.models import User

@pytest.fixture
def client():
    # Configure app for testing
    app = create_app('test')
    
    with app.test_client() as client:
        with app.app_context():
            # Create tables
            db.create_all()
            yield client
            # Drop tables after test
            db.session.remove()
            db.drop_all()

def test_full_system_flow(client):
    # 1. Register a Patient User
    res = client.post('/api/v1/auth/register', json={
        "nome": "Paciente Teste",
        "email": "paciente@teste.com",
        "password": "senha",
        "perfil": "Paciente"
    })
    assert res.status_code == 201
    assert res.json['message'] == "Usuário cadastrado com sucesso!"

    # 2. Login User
    res = client.post('/api/v1/auth/login', json={
        "email": "paciente@teste.com",
        "password": "senha"
    })
    assert res.status_code == 200
    token = res.json['token']
    
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Complete Patient Clinical Data
    res = client.post('/api/v1/patients/', json={
        "cpf": "123.456.789-00",
        "data_nascimento": "1990-01-01",
        "telefone": "11999999999",
        "tipo_sanguineo": "O+",
        "alergias": "Nenhuma",
        "comorbidades": "Diabetes"
    }, headers=headers)
    assert res.status_code == 201

    # 4. Check-in to Queue
    res = client.post('/api/v1/queue/check-in', headers=headers)
    assert res.status_code == 201
    assert res.json['score'] == 85 # Because of diabetes

    # 5. List Queue and verify Patient is there
    res = client.get('/api/v1/queue/')
    assert res.status_code == 200
    assert len(res.json) == 1
    assert res.json[0]['paciente'] == "Paciente Teste"

def test_admin_flow(client):
    # 1. Register an Admin (Simulating direct creation or admin registration)
    res = client.post('/api/v1/auth/register', json={
        "nome": "Admin Teste",
        "email": "admin@teste.com",
        "password": "senha",
        "perfil": "Admin" # Wait, the API only allows 'Paciente'. Let's see how it behaves
    })
    # As per auth.py, public register always creates 'Paciente'
    assert res.status_code == 201
    
    # Manually promote to Admin in database for test purposes
    with client.application.app_context():
        user = User.query.filter_by(email="admin@teste.com").first()
        user.perfil = "Admin"
        db.session.commit()

    # 2. Login Admin
    res = client.post('/api/v1/auth/login', json={
        "email": "admin@teste.com",
        "password": "senha"
    })
    assert res.status_code == 200
    admin_token = res.json['token']
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 3. Create a patient and put them in queue
    res = client.post('/api/v1/auth/register', json={
        "nome": "Paciente 2",
        "email": "pac2@teste.com",
        "password": "senha",
        "perfil": "Paciente"
    })
    res = client.post('/api/v1/auth/login', json={
        "email": "pac2@teste.com",
        "password": "senha"
    })
    pac_token = res.json['token']
    pac_headers = {"Authorization": f"Bearer {pac_token}"}
    
    res = client.post('/api/v1/patients/', json={
        "cpf": "000.000.000-00",
        "data_nascimento": "1995-01-01",
        "telefone": "11999999999",
        "tipo_sanguineo": "A+",
        "alergias": "Nenhuma",
        "comorbidades": ""
    }, headers=pac_headers)
    assert res.status_code == 201
    
    res = client.post('/api/v1/queue/check-in', headers=pac_headers)
    assert res.status_code == 201
    
    # 4. Get Queue ID
    res = client.get('/api/v1/queue/')
    assert res.status_code == 200
    queue_id = res.json[0]['id']
    
    # 5. Admin updates status
    res = client.patch(f'/api/v1/queue/{queue_id}/status', json={
        "status": "Em Atendimento"
    }, headers=admin_headers)
    assert res.status_code == 200
    
    # 6. Check queue is empty (since it lists only 'Aguardando')
    res = client.get('/api/v1/queue/')
    assert res.status_code == 200
    assert len(res.json) == 0
