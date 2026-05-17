from flask import Blueprint, request, jsonify
from datetime import datetime
from app.extensions import db
from app.models import User, Paciente  # Importamos Paciente aqui para o vinculo
from flask_jwt_extended import (
    create_access_token, 
    create_refresh_token, 
    jwt_required, 
    get_jwt_identity
)

# Define o Blueprint seguindo a padronização v1 do guia técnico
auth = Blueprint('auth', __name__, url_prefix='/api/v1/auth')

# 1. CADASTRO DE NOVOS PACIENTES COM INTEGRAÇÃO PARA O ML (POST /api/v1/auth/register)
@auth.route('/register', methods=['POST'])
def register():
    dados = request.get_json()
    
    email = dados.get('email')
    cpf = dados.get('cpf')
    genero = dados.get('genero')
    data_nasc_str = dados.get('data_nascimento')
    senha = dados.get('senha') or dados.get('password') # Aceita ambos para não quebrar o front

    # Validação dos campos obrigatórios da tela do Angular
    if not all([dados.get('nome'), email, senha, cpf, genero, data_nasc_str]):
        return jsonify({"message": "Todos os campos (Nome, Email, Senha, CPF, Gênero e Data de Nascimento) são obrigatórios"}), 400
    
    # Verifica duplicidade no banco
    if User.query.filter_by(email=email).first():
        return jsonify({"message": "Este e-mail já está cadastrado"}), 400
        
    if Paciente.query.filter_by(cpf=cpf).first():
        return jsonify({"message": "Este CPF já está cadastrado"}), 400

    try:
        # Converte a data de nascimento vinda do Angular de texto para Date
        if '-' in data_nasc_str:
            data_nascimento = datetime.strptime(data_nasc_str, '%Y-%m-%d').date()
        else:
            data_nascimento = datetime.strptime(data_nasc_str, '%d/%m/%Y').date()

        # Instancia o Novo Usuário
        novo_usuario = User(
            nome=dados.get('nome'),
            email=email,
            perfil=dados.get('perfil', 'Paciente') 
        )
        novo_usuario.set_password(senha)

        db.session.add(novo_usuario)
        db.session.flush() # Gera o ID do usuário temporariamente para vincular o paciente

        # Instancia o Paciente vinculado ao Usuário (Guarda Gênero e Idade para o ML)
        novo_paciente = Paciente(
            user_id=novo_usuario.id,
            cpf=cpf,
            data_nascimento=data_nascimento,
            genero=genero.upper() # Salva 'M' ou 'F'
        )
        
        db.session.add(novo_paciente)
        db.session.commit() # Salva tudo definitivamente no SQLite
        
        return jsonify({
            "message": "Usuário e dados de Paciente cadastrados com sucesso!",
            "id": novo_usuario.id
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Erro ao salvar no banco", "error": str(e)}), 500

# 2. AUTENTICAÇÃO (POST /api/v1/auth/login)
@auth.route('/login', methods=['POST'])
def login():
    dados = request.get_json()
    email = dados.get('email')
    senha = dados.get('senha') or dados.get('password')

    usuario = User.query.filter_by(email=email).first()

    if not usuario or not usuario.check_password(senha):
        return jsonify({"message": "E-mail ou senha inválidos"}), 401

    access_token = create_access_token(identity=str(usuario.id))
    refresh_token = create_refresh_token(identity=str(usuario.id))

    return jsonify({
        "token": access_token,
        "refresh_token": refresh_token,
        "user": {
            "id": usuario.id,
            "nome": usuario.nome,
            "email": usuario.email,
            "perfil": usuario.perfil,
            "especialidade": usuario.especialidade,
            "crm": usuario.crm,
            "foto": usuario.foto,
            "sobre": usuario.sobre,
            "uf": usuario.uf,
            "localAtendimento": usuario.local_atendimento
        }
    }), 200

# 3. RETORNA O PERFIL DO USUÁRIO LOGADO (GET /api/v1/auth/me)
@auth.route('/me', methods=['GET'])
@jwt_required()
def get_me():
    user_id = get_jwt_identity()
    usuario = User.query.get(int(user_id))
    
    if not usuario:
        return jsonify({"message": "Usuário não encontrado"}), 404

    return jsonify({
        "id": usuario.id,
        "nome": usuario.nome,
        "email": usuario.email,
        "perfil": usuario.perfil,
        "especialidade": usuario.especialidade,
        "crm": usuario.crm,
        "foto": usuario.foto,
        "sobre": usuario.sobre,
        "uf": usuario.uf
    }), 200

# 4. RENOVA O TOKEN DE ACESSO (POST /api/v1/auth/refresh)
@auth.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()
    new_access_token = create_access_token(identity=identity)
    return jsonify({"token": new_access_token}), 200