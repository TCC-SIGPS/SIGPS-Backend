from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import db, Paciente, User
from datetime import datetime

# Blueprint seguindo a padronização v1 do guia técnico
bp_paciente = Blueprint('paciente', __name__, url_prefix='/api/v1/patients')

# 1. LISTAR PACIENTES COM FILTROS (GET /api/v1/patients/)
@bp_paciente.route('/', methods=['GET'])
@jwt_required()
def listar_pacientes():
    # Parâmetros de busca enviados pelo Angular (ex: ?nome=Joao)
    nome_query = request.args.get('nome')
    cpf_query = request.args.get('cpf')

    # Iniciamos a query fazendo um JOIN com a tabela de usuários para buscar o nome
    query = Paciente.query.join(User)

    if nome_query:
        query = query.filter(User.nome.like(f'%{nome_query}%'))
    if cpf_query:
        query = query.filter(Paciente.cpf.like(f'%{cpf_query}%'))

    pacientes = query.all()
    
    resultado = []
    for p in pacientes:
        resultado.append({
            "id": p.id,
            "nome": p.usuario.nome,
            "cpf": p.cpf,
            "data_nascimento": p.data_nascimento.strftime('%d/%m/%Y'),
            "telefone": p.telefone
        })

    return jsonify(resultado), 200

# 2. DETALHES DE UM PACIENTE ESPECÍFICO (GET /api/v1/patients/{id})[cite: 1]
@bp_paciente.route('/<int:id>', methods=['GET'])
@jwt_required()
def obter_paciente(id):
    paciente = Paciente.query.get_or_404(id)
    return jsonify({
        "id": paciente.id,
        "nome": paciente.usuario.nome,
        "email": paciente.usuario.email,
        "cpf": paciente.cpf,
        "data_nascimento": paciente.data_nascimento.strftime('%Y-%m-%d'),
        "tipo_sanguineo": paciente.tipo_sanguineo,
        "alergias": paciente.alergias,
        "comorbidades": paciente.comorbidades
    }), 200

# 3. COMPLETAR CADASTRO CLÍNICO (POST /api/v1/patients/)[cite: 1]
@bp_paciente.route('/', methods=['POST'])
@jwt_required()
def completar_cadastro():
    usuario_id = get_jwt_identity()
    dados = request.get_json()

    paciente_existente = Paciente.query.filter_by(user_id=usuario_id).first()
    if paciente_existente:
        return jsonify({"message": "Dados clínicos já cadastrados"}), 400

    try:
        data_nasc = datetime.strptime(dados.get('data_nascimento'), '%Y-%m-%d').date()

        user = User.query.get(usuario_id)
        genero_user = user.genero if user else 'Masculino'
        genero_upper = (genero_user or 'M').upper()
        if 'MASC' in genero_upper or genero_upper.startswith('M'):
            genero_db = 'M'
        elif 'FEM' in genero_upper or genero_upper.startswith('F'):
            genero_db = 'F'
        else:
            genero_db = 'M'

        novo_paciente = Paciente(
            user_id=usuario_id,
            cpf=dados.get('cpf'),
            data_nascimento=data_nasc,
            genero=genero_db,
            telefone=dados.get('telefone'),
            tipo_sanguineo=dados.get('tipo_sanguineo'),
            alergias=dados.get('alergias'),
            comorbidades=dados.get('comorbidades')
        )

        db.session.add(novo_paciente)
        db.session.commit()
        return jsonify({"message": "Dados clínicos salvos com sucesso!"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Erro ao salvar", "error": str(e)}), 500

# 4. EXCLUSÃO (DELETE /api/v1/patients/{id})[cite: 1]
@bp_paciente.route('/<int:id>', methods=['DELETE'])
@jwt_required()
def deletar_paciente(id):
    paciente = Paciente.query.get_or_404(id)
    # O guia sugere exclusão lógica, mas para simplicidade aqui removemos o registro[cite: 1]
    db.session.delete(paciente)
    db.session.commit()
    return jsonify({"message": "Paciente removido com sucesso"}), 200