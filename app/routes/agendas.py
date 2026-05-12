from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import db, Agenda, Consulta, User
from datetime import datetime

bp_agendas = Blueprint('agendas', __name__, url_prefix='/api/v1/schedules')


def _serializar_agenda(a):
    horarios = [h for h in a.horarios_disponiveis.split(',') if h] if a.horarios_disponiveis else []
    return {
        "id": a.id,
        "especialistaId": a.especialista_id,
        "especialista": a.especialista.nome,
        "especialidade": a.especialista.especialidade or 'Clínico Geral',
        "data": a.data.strftime('%d/%m/%Y'),
        "horarios": horarios,
        "vagas": len(horarios)
    }


def _serializar_consulta(c):
    return {
        "id": c.id,
        "pacienteId": c.paciente_id,
        "pacienteNome": c.paciente.nome,
        "especialista": c.agenda.especialista.nome,
        "especialidade": c.agenda.especialista.especialidade or 'Clínico Geral',
        "data": c.agenda.data.strftime('%d/%m/%Y'),
        "horario": c.horario,
        "local": c.agenda.especialista.local_atendimento or '',
        "instrucoes": "",
        "recomendacoes": "",
        "status": c.status.lower().replace('í', 'i')  # normaliza para minúsculas
    }


@bp_agendas.route('/', methods=['GET'])
@jwt_required()
def listar_agendas():
    especialista_id = request.args.get('especialista_id', type=int)
    query = Agenda.query
    if especialista_id:
        query = query.filter_by(especialista_id=especialista_id)
    agendas = query.all()
    return jsonify([_serializar_agenda(a) for a in agendas]), 200


@bp_agendas.route('/', methods=['POST'])
@jwt_required()
def criar_agenda():
    user_id = int(get_jwt_identity())
    usuario = User.query.get(user_id)
    dados = request.get_json()

    # Gestor/Admin pode criar agenda para outro especialista
    if usuario.perfil in ('Gestor', 'Admin') and dados.get('especialistaId'):
        especialista_id = dados['especialistaId']
    else:
        especialista_id = user_id

    nova_agenda = Agenda(
        especialista_id=especialista_id,
        data=datetime.strptime(dados.get('data', datetime.today().strftime('%Y-%m-%d')), '%Y-%m-%d').date(),
        horarios_disponiveis=",".join(dados.get('horarios', []))
    )
    db.session.add(nova_agenda)
    db.session.commit()
    return jsonify(_serializar_agenda(nova_agenda)), 201


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
    if 'data' in dados:
        agenda.data = datetime.strptime(dados['data'], '%Y-%m-%d').date()
    db.session.commit()
    return jsonify(_serializar_agenda(agenda)), 200


@bp_agendas.route('/agendar', methods=['POST'])
@jwt_required()
def agendar_consulta():
    user_id = int(get_jwt_identity())
    dados = request.get_json()
    agenda = Agenda.query.get_or_404(dados.get('agendaId'))
    horario = dados.get('horario')

    nova_consulta = Consulta(
        agenda_id=agenda.id,
        paciente_id=user_id,
        horario=horario,
        status='Agendada'
    )
    db.session.add(nova_consulta)

    # Remove o horário da agenda após o agendamento
    if agenda.horarios_disponiveis:
        horarios = [h for h in agenda.horarios_disponiveis.split(',') if h]
        if horario in horarios:
            horarios.remove(horario)
            agenda.horarios_disponiveis = ",".join(horarios)

    db.session.commit()
    return jsonify(_serializar_consulta(nova_consulta)), 201


@bp_agendas.route('/consultas', methods=['GET'])
@jwt_required()
def listar_consultas():
    user_id = int(get_jwt_identity())
    usuario = User.query.get(user_id)

    if usuario.perfil == 'Paciente':
        consultas = Consulta.query.filter_by(paciente_id=user_id).all()
    else:
        consultas = Consulta.query.join(Agenda).filter(Agenda.especialista_id == user_id).all()

    return jsonify([_serializar_consulta(c) for c in consultas]), 200


@bp_agendas.route('/consultas/<int:id>/status', methods=['PATCH'])
@jwt_required()
def atualizar_status_consulta(id):
    consulta = Consulta.query.get_or_404(id)
    dados = request.get_json()
    novo_status = dados.get('status', '').capitalize()
    # Normaliza valores aceitos
    mapa = {'Agendada': 'Agendada', 'Cancelada': 'Cancelada', 'Concluida': 'Concluída', 'Concluída': 'Concluída'}
    consulta.status = mapa.get(novo_status, novo_status)
    db.session.commit()
    return jsonify({"message": "Status atualizado", "consulta": _serializar_consulta(consulta)}), 200
