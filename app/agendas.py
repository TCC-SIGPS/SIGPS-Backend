from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import db, Agenda, Consulta, User
from datetime import datetime

bp_agendas = Blueprint('agendas', __name__, url_prefix='/api/v1/schedules')

@bp_agendas.route('/', methods=['GET'])
@jwt_required()
def listar_agendas():
    agendas = Agenda.query.all()
    resultado = []
    for a in agendas:
        resultado.append({
            "id": a.id,
            "especialista": a.especialista.nome,
            "especialidade": "Clínico Geral", # Hardcoded MVP
            "horarios": a.horarios_disponiveis.split(',') if a.horarios_disponiveis else [],
            "vagas": len(a.horarios_disponiveis.split(',')) if a.horarios_disponiveis else 0
        })
    return jsonify(resultado), 200

@bp_agendas.route('/', methods=['POST'])
@jwt_required()
def criar_agenda():
    user_id = int(get_jwt_identity())
    dados = request.get_json()
    nova_agenda = Agenda(
        especialista_id=user_id,
        data=datetime.strptime(dados.get('data', datetime.today().strftime('%Y-%m-%d')), '%Y-%m-%d').date(),
        horarios_disponiveis=",".join(dados.get('horarios', []))
    )
    db.session.add(nova_agenda)
    db.session.commit()
    return jsonify({
        "id": nova_agenda.id,
        "especialista": nova_agenda.especialista.nome,
        "especialidade": "Clínico Geral",
        "horarios": nova_agenda.horarios_disponiveis.split(','),
        "vagas": len(nova_agenda.horarios_disponiveis.split(','))
    }), 201

@bp_agendas.route('/<int:id>/', methods=['DELETE'])
@jwt_required()
def excluir_agenda(id):
    agenda = Agenda.query.get_or_404(id)
    db.session.delete(agenda)
    db.session.commit()
    return jsonify({"message": "Agenda removida"}), 200

@bp_agendas.route('/<int:id>/', methods=['PATCH'])
@jwt_required()
def atualizar_agenda(id):
    agenda = Agenda.query.get_or_404(id)
    dados = request.get_json()
    if 'horarios' in dados:
        agenda.horarios_disponiveis = ",".join(dados['horarios'])
    db.session.commit()
    return jsonify({
        "id": agenda.id,
        "especialista": agenda.especialista.nome,
        "especialidade": "Clínico Geral",
        "horarios": agenda.horarios_disponiveis.split(',') if agenda.horarios_disponiveis else [],
        "vagas": len(agenda.horarios_disponiveis.split(',')) if agenda.horarios_disponiveis else 0
    }), 200

# Consultas
@bp_agendas.route('/agendar', methods=['POST'])
@jwt_required()
def agendar_consulta():
    user_id = int(get_jwt_identity())
    dados = request.get_json()
    nova_consulta = Consulta(
        agenda_id=dados.get('agendaId'),
        paciente_id=user_id,
        horario=dados.get('horario')
    )
    db.session.add(nova_consulta)
    
    # Remove horario da agenda
    agenda = Agenda.query.get(dados.get('agendaId'))
    if agenda and agenda.horarios_disponiveis:
        horarios = agenda.horarios_disponiveis.split(',')
        if nova_consulta.horario in horarios:
            horarios.remove(nova_consulta.horario)
            agenda.horarios_disponiveis = ",".join(horarios)
            
    db.session.commit()
    return jsonify({"message": "Consulta agendada"}), 201

@bp_agendas.route('/consultas', methods=['GET'])
@jwt_required()
def listar_consultas():
    user_id = int(get_jwt_identity())
    usuario = User.query.get(user_id)
    if usuario.perfil == 'Paciente':
        consultas = Consulta.query.filter_by(paciente_id=user_id).all()
    else:
        # Especialista vê suas consultas
        consultas = Consulta.query.join(Agenda).filter(Agenda.especialista_id == user_id).all()
        
    resultado = []
    for c in consultas:
        resultado.append({
            "id": c.id,
            "pacienteId": c.paciente_id,
            "pacienteNome": c.paciente.nome,
            "especialista": c.agenda.especialista.nome,
            "especialidade": "Clínico Geral",
            "data": c.agenda.data.strftime('%Y-%m-%d'),
            "horario": c.horario,
            "local": "Consultório 1",
            "instrucoes": "Chegar 10 minutos antes",
            "recomendacoes": "",
            "status": c.status
        })
    return jsonify(resultado), 200

@bp_agendas.route('/consultas/<int:id>/status', methods=['PATCH'])
@jwt_required()
def atualizar_status_consulta(id):
    consulta = Consulta.query.get_or_404(id)
    dados = request.get_json()
    consulta.status = dados.get('status')
    db.session.commit()
    return jsonify({"message": "Status atualizado"}), 200
