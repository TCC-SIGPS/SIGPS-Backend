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

@bp_admin.route('/users/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_user(id):
    user_id = int(get_jwt_identity())
    solicitante = User.query.get(user_id)
    if solicitante.perfil != 'Admin':
        return jsonify({"message": "Acesso negado"}), 403

    if user_id == id:
        return jsonify({"message": "Você não pode excluir sua própria conta"}), 400

    usuario = User.query.get_or_404(id)

    try:
        from app.models import ChatMessage, Paciente, Especialista, FilaAtendimento, Exame, Consulta, Agenda, ClinicaEspecialista, Clinica

        # Excluir mensagens de chat
        ChatMessage.query.filter((ChatMessage.sender_id == id) | (ChatMessage.receiver_id == id)).delete()

        # Se for paciente, excluir dependências do paciente
        paciente = Paciente.query.filter_by(user_id=id).first()
        if paciente:
            FilaAtendimento.query.filter_by(paciente_id=paciente.id).delete()
            Exame.query.filter_by(paciente_id=paciente.id).delete()
            db.session.delete(paciente)

        # Excluir consultas onde é paciente
        Consulta.query.filter_by(paciente_id=id).delete()

        # Se for especialista, excluir dependências
        ClinicaEspecialista.query.filter_by(especialista_id=id).delete()
        
        especialista = Especialista.query.filter_by(user_id=id).first()
        if especialista:
            db.session.delete(especialista)
        
        # Agendas e consultas da agenda (onde o usuário é o especialista)
        agendas = Agenda.query.filter_by(especialista_id=id).all()
        for agenda in agendas:
            Consulta.query.filter_by(agenda_id=agenda.id).delete()
            db.session.delete(agenda)

        # Se for admin de clinica
        clinicas = Clinica.query.filter_by(admin_id=id).all()
        for clinica in clinicas:
            ClinicaEspecialista.query.filter_by(clinica_id=clinica.id).delete()
            db.session.delete(clinica)

        db.session.delete(usuario)
        db.session.commit()
        return jsonify({"message": "Usuário excluído com sucesso"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"Erro ao excluir usuário: {str(e)}"}), 500

