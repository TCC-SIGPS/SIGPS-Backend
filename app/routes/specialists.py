from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import db, User, Agenda
from datetime import date

bp_specialists = Blueprint('specialists', __name__, url_prefix='/api/v1/specialists')

DIAS_SEMANA = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']


def _foto_padrao(nome):
    nome_url = nome.replace(' ', '+')
    return f"https://ui-avatars.com/api/?name={nome_url}&background=419640&color=fff&size=200"


def _serializar_especialista(u, com_agenda=False):
    esp = u.especialista_info
    data = {
        "id": u.id,
        "nome": u.nome,
        "especialidade": esp.especialidade if esp else 'Clínico Geral',
        "crm": esp.crm if esp else '',
        "foto": esp.foto if esp else _foto_padrao(u.nome),
        "sobre": esp.sobre if esp else '',
        "uf": esp.uf if esp else '',
        "localAtendimento": esp.local_atendimento if esp else '',
        "situacao": "Ativo",
        "avaliacao": 5.0,
        "avaliacoesCount": 0,
        "proximaVaga": None,
        "last_seen": None,
        "status": "online",
        "formacao": [],
        "servicos": [],
        "avaliacoes": [],
        "agendaHoje": []
    }

    today = date.today()
    agendas_futuras = (
        Agenda.query
        .filter(
            Agenda.especialista_id == u.id,
            Agenda.data >= today,
            Agenda.horarios_disponiveis.isnot(None),
            Agenda.horarios_disponiveis != ''
        )
        .order_by(Agenda.data)
        .all()
    )

    if agendas_futuras:
        a = agendas_futuras[0]
        horarios = [h for h in a.horarios_disponiveis.split(',') if h]
        if horarios:
            data["proximaVaga"] = f"{a.data.strftime('%d/%m')}, {horarios[0]}"

    if com_agenda:
        dias_disponiveis = []
        for a in agendas_futuras[:7]:
            horarios = [h for h in a.horarios_disponiveis.split(',') if h]
            if horarios:
                dias_disponiveis.append({
                    "agendaId": a.id,
                    "data": a.data.strftime('%d/%m'),
                    "diasemana": DIAS_SEMANA[a.data.weekday()],
                    "slots": horarios
                })
        data["diasDisponiveis"] = dias_disponiveis

    return data


@bp_specialists.route('/', methods=['GET'])
@jwt_required()
def listar_especialistas():
    especialistas = User.query.filter_by(perfil='Especialista').all()
    return jsonify([_serializar_especialista(u) for u in especialistas]), 200


@bp_specialists.route('/<int:id>', methods=['GET'])
@jwt_required()
def get_especialista(id):
    u = User.query.get_or_404(id)
    if u.perfil != 'Especialista':
        return jsonify({"message": "Profissional não encontrado"}), 404
    return jsonify(_serializar_especialista(u, com_agenda=True)), 200


@bp_specialists.route('/me', methods=['PATCH'])
@jwt_required()
def atualizar_perfil():
    user_id = int(get_jwt_identity())
    u = User.query.get_or_404(user_id)
    dados = request.get_json()
    if not u.especialista_info:
        return jsonify({"message": "Perfil de especialista não encontrado"}), 400

    campos = ['especialidade', 'crm', 'foto', 'sobre', 'uf', 'local_atendimento']
    for campo in campos:
        if campo in dados:
            setattr(u.especialista_info, campo, dados[campo])
    db.session.commit()
    return jsonify({"message": "Perfil atualizado", "especialista": _serializar_especialista(u)}), 200
