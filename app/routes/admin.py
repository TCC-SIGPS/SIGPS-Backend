from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import db, User

bp_admin = Blueprint('admin', __name__, url_prefix='/api/v1/admin')

@bp_admin.route('/users', methods=['GET'])
@jwt_required()
def listar_usuarios():
    # Verifica se o solicitante é Admin
    user_id = int(get_jwt_identity())
    solicitante = User.query.get(user_id)
    if solicitante.perfil != 'Admin':
        return jsonify({"message": "Acesso negado"}), 403

    usuarios = User.query.all()
    resultado = []
    for u in usuarios:
        resultado.append({
            "id": u.id,
            "nome": u.nome,
            "email": u.email,
            "perfil": u.perfil
        })
    return jsonify(resultado), 200

@bp_admin.route('/users/<int:id>/role', methods=['PATCH'])
@jwt_required()
def alterar_perfil(id):
    user_id = int(get_jwt_identity())
    solicitante = User.query.get(user_id)
    if solicitante.perfil != 'Admin':
        return jsonify({"message": "Acesso negado"}), 403

    dados = request.get_json()
    novo_perfil = dados.get('perfil')
    
    if novo_perfil not in ['Paciente', 'Admin', 'Gestor', 'Especialista', 'Visualizador']:
        return jsonify({"message": "Perfil inválido"}), 400

    usuario = User.query.get_or_404(id)
    usuario.perfil = novo_perfil
    db.session.commit()
    
    return jsonify({"message": "Perfil atualizado com sucesso"}), 200
