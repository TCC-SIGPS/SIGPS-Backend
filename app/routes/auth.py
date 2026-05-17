from flask import Blueprint, request, jsonify
from app.models import db, User
from flask_jwt_extended import (
    create_access_token, 
    create_refresh_token, 
    jwt_required, 
    get_jwt_identity
)

# Define o Blueprint seguindo a padronização v1 do guia técnico
auth = Blueprint('auth', __name__, url_prefix='/api/v1/auth')

# 1. CADASTRO DE NOVOS PACIENTES (POST /api/v1/auth/register)
@auth.route('/register', methods=['POST'])
def register():
    dados = request.get_json()
    
    usuario_existente = User.query.filter_by(email=dados.get('email')).first()
    if usuario_existente:
        return jsonify({"message": "Este e-mail já está cadastrado"}), 400

    # Perfis suportados: Paciente, Visualizador, Gestor, Especialista, Admin
    novo_usuario = User(
        nome=dados.get('nome'),
        email=dados.get('email'),
        perfil=dados.get('perfil', 'Paciente'),
        genero=dados.get('genero')
    )
    
    # Transforma a senha em hash antes de salvar no banco
    novo_usuario.set_password(dados.get('password'))

    try:
        db.session.add(novo_usuario)
        db.session.commit()
        return jsonify({
            "message": "Usuário cadastrado com sucesso!",
            "id": novo_usuario.id
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Erro ao salvar no banco", "error": str(e)}), 500

# 2. AUTENTICAÇÃO (POST /api/v1/auth/login)[cite: 1]
@auth.route('/login', methods=['POST'])
def login():
    dados = request.get_json()
    email = dados.get('email')
    senha = dados.get('password')

    usuario = User.query.filter_by(email=email).first()

    if not usuario or not usuario.check_password(senha):
        return jsonify({"message": "E-mail ou senha inválidos"}), 401

    # Gera o Token de Acesso e o Refresh Token[cite: 1]
    # O identity é o ID do usuário (como string) para facilitar buscas posteriores
    access_token = create_access_token(identity=str(usuario.id))
    refresh_token = create_refresh_token(identity=str(usuario.id))

    esp = usuario.especialista_info

    return jsonify({
        "token": access_token,
        "refresh_token": refresh_token,
        "user": {
            "id": usuario.id,
            "nome": usuario.nome,
            "email": usuario.email,
            "perfil": usuario.perfil,
            "genero": usuario.genero,
            "especialidade": esp.especialidade if esp else None,
            "crm": esp.crm if esp else None,
            "foto": esp.foto if esp else None,
            "sobre": esp.sobre if esp else None,
            "uf": esp.uf if esp else None,
            "localAtendimento": esp.local_atendimento if esp else None
        }
    }), 200

# 3. RETORNA O PERFIL DO USUÁRIO LOGADO (GET /api/v1/auth/me)[cite: 1]
@auth.route('/me', methods=['GET'])
@jwt_required()
def get_me():
    user_id = get_jwt_identity()
    usuario = User.query.get(int(user_id))
    
    if not usuario:
        return jsonify({"message": "Usuário não encontrado"}), 404

    esp = usuario.especialista_info

    return jsonify({
        "id": usuario.id,
        "nome": usuario.nome,
        "email": usuario.email,
        "perfil": usuario.perfil,
        "genero": usuario.genero,
        "especialidade": esp.especialidade if esp else None,
        "crm": esp.crm if esp else None,
        "foto": esp.foto if esp else None,
        "sobre": esp.sobre if esp else None,
        "uf": esp.uf if esp else None
    }), 200

# 4. RENOVA O TOKEN DE ACESSO (POST /api/v1/auth/refresh)[cite: 1]
@auth.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()
    new_access_token = create_access_token(identity=identity)
    return jsonify({"token": new_access_token}), 200