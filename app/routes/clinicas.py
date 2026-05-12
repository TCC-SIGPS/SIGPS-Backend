import re
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import db, User, Clinica, ClinicaEspecialista

bp_clinicas = Blueprint('clinicas', __name__, url_prefix='/api/v1/clinicas')


def _validar_cnpj(cnpj: str) -> bool:
    """Validação matemática do dígito verificador do CNPJ."""
    c = re.sub(r'\D', '', cnpj)
    if len(c) != 14 or len(set(c)) == 1:
        return False
    def calc(c, n):
        s = sum(int(c[i]) * ((n - i) % 8 + 2) for i in range(n - 1))
        r = 11 - s % 11
        return 0 if r >= 10 else r
    return calc(c, 13) == int(c[12]) and calc(c, 14) == int(c[13])


def _endereco_formatado(c: Clinica) -> str:
    partes = [c.rua, c.numero, c.complemento, c.bairro]
    partes = [p for p in partes if p]
    linha1 = ', '.join(partes)
    linha2 = f"{c.cidade}/{c.estado}" if c.cidade and c.estado else ''
    return f"{linha1} — {linha2}" if linha2 else linha1


def _serializar_clinica(c, com_membros=False):
    data = {
        "id": c.id,
        "nome": c.nome,
        "tipo": c.tipo or 'Clínica',
        "cnpj": c.cnpj or '',
        "telefone": c.telefone or '',
        "emailContato": c.email_contato or '',
        "cep": c.cep or '',
        "rua": c.rua or '',
        "numero": c.numero or '',
        "complemento": c.complemento or '',
        "bairro": c.bairro or '',
        "cidade": c.cidade or '',
        "estado": c.estado or '',
        "enderecoFormatado": _endereco_formatado(c),
        "adminId": c.admin_id,
        "adminNome": c.admin.nome,
        "statusVerificacao": c.status_verificacao or 'pendente'
    }
    if com_membros:
        data['especialistas'] = [
            {
                "id": m.especialista_id,
                "nome": m.especialista.nome,
                "especialidade": m.especialista.especialidade or '',
                "crm": m.especialista.crm or '',
                "statusVerificacao": m.especialista.status_verificacao or 'nao_verificado'
            }
            for m in c.membros
        ]
    return data


@bp_clinicas.route('/', methods=['POST'])
@jwt_required()
def criar_clinica():
    user_id = int(get_jwt_identity())
    dados = request.get_json()

    nome = (dados.get('nome') or '').strip()
    cnpj_raw = re.sub(r'\D', '', dados.get('cnpj') or '')

    if not nome:
        return jsonify({"message": "Nome da clínica é obrigatório"}), 400

    if cnpj_raw and not _validar_cnpj(cnpj_raw):
        return jsonify({"message": "CNPJ inválido. Verifique os dígitos e tente novamente."}), 400

    # Verifica duplicidade de CNPJ
    if cnpj_raw:
        cnpj_fmt = f"{cnpj_raw[:2]}.{cnpj_raw[2:5]}.{cnpj_raw[5:8]}/{cnpj_raw[8:12]}-{cnpj_raw[12:]}"
        existente_cnpj = Clinica.query.filter_by(cnpj=cnpj_fmt).first()
        if existente_cnpj:
            return jsonify({"message": "Já existe uma clínica cadastrada com este CNPJ"}), 409
    else:
        cnpj_fmt = None

    # Verifica se já administra uma clínica
    existente = Clinica.query.filter_by(admin_id=user_id).first()
    if existente:
        return jsonify({"message": "Você já administra uma clínica", "clinica": _serializar_clinica(existente, True)}), 409

    nova = Clinica(
        nome=nome,
        tipo=dados.get('tipo', 'Clínica'),
        cnpj=cnpj_fmt,
        telefone=dados.get('telefone', ''),
        email_contato=dados.get('emailContato', ''),
        cep=dados.get('cep', ''),
        rua=dados.get('rua', ''),
        numero=dados.get('numero', ''),
        complemento=dados.get('complemento', ''),
        bairro=dados.get('bairro', ''),
        cidade=dados.get('cidade', ''),
        estado=dados.get('estado', ''),
        endereco=_endereco_formatado_dict(dados),
        admin_id=user_id,
        status_verificacao='pendente'
    )
    db.session.add(nova)

    admin = User.query.get(user_id)
    if admin.perfil == 'Especialista' and not admin.local_atendimento:
        admin.local_atendimento = nova.endereco

    db.session.commit()
    return jsonify(_serializar_clinica(nova, True)), 201


def _endereco_formatado_dict(d):
    partes = [d.get('rua', ''), d.get('numero', ''), d.get('complemento', ''), d.get('bairro', '')]
    partes = [p for p in partes if p]
    linha1 = ', '.join(partes)
    cidade = d.get('cidade', '')
    estado = d.get('estado', '')
    linha2 = f"{cidade}/{estado}" if cidade and estado else ''
    return f"{linha1} — {linha2}" if linha1 and linha2 else linha1 or linha2


@bp_clinicas.route('/minha', methods=['GET'])
@jwt_required()
def minha_clinica():
    user_id = int(get_jwt_identity())
    c = Clinica.query.filter_by(admin_id=user_id).first()
    if not c:
        return jsonify({"message": "Nenhuma clínica encontrada"}), 404
    return jsonify(_serializar_clinica(c, True)), 200


@bp_clinicas.route('/<int:id>', methods=['PATCH'])
@jwt_required()
def atualizar_clinica(id):
    user_id = int(get_jwt_identity())
    c = Clinica.query.get_or_404(id)
    if c.admin_id != user_id:
        return jsonify({"message": "Acesso negado"}), 403

    dados = request.get_json()
    campos = ['nome', 'tipo', 'telefone', 'email_contato', 'cep', 'rua',
              'numero', 'complemento', 'bairro', 'cidade', 'estado']
    mapa = {'emailContato': 'email_contato'}

    for campo_json in dados:
        campo_db = mapa.get(campo_json, campo_json)
        if campo_db in campos:
            setattr(c, campo_db, dados[campo_json])

    novo_endereco = _endereco_formatado(c)
    c.endereco = novo_endereco

    # Propaga o novo endereço para todos os especialistas vinculados
    for membro in c.membros:
        membro.especialista.local_atendimento = novo_endereco

    db.session.commit()
    return jsonify(_serializar_clinica(c, True)), 200


@bp_clinicas.route('/<int:id>/especialistas', methods=['POST'])
@jwt_required()
def adicionar_especialista(id):
    user_id = int(get_jwt_identity())
    c = Clinica.query.get_or_404(id)
    if c.admin_id != user_id:
        return jsonify({"message": "Acesso negado"}), 403

    dados = request.get_json()
    email = (dados.get('email') or '').strip().lower()
    if not email:
        return jsonify({"message": "E-mail do profissional é obrigatório"}), 400

    especialista = User.query.filter_by(email=email).first()
    if not especialista:
        return jsonify({"message": "Usuário não encontrado com este e-mail"}), 404
    if especialista.perfil != 'Especialista':
        return jsonify({"message": "Este usuário não possui perfil de especialista"}), 400

    if ClinicaEspecialista.query.filter_by(clinica_id=id, especialista_id=especialista.id).first():
        return jsonify({"message": "Profissional já faz parte desta clínica"}), 409

    vinculo = ClinicaEspecialista(clinica_id=id, especialista_id=especialista.id)
    db.session.add(vinculo)
    especialista.local_atendimento = c.endereco or _endereco_formatado(c)
    db.session.commit()

    return jsonify({
        "message": f"{especialista.nome} adicionado. Local de atendimento atualizado automaticamente.",
        "clinica": _serializar_clinica(c, True)
    }), 201


@bp_clinicas.route('/<int:id>/especialistas/<int:esp_id>', methods=['DELETE'])
@jwt_required()
def remover_especialista(id, esp_id):
    user_id = int(get_jwt_identity())
    c = Clinica.query.get_or_404(id)
    if c.admin_id != user_id:
        return jsonify({"message": "Acesso negado"}), 403

    vinculo = ClinicaEspecialista.query.filter_by(clinica_id=id, especialista_id=esp_id).first_or_404()
    db.session.delete(vinculo)
    db.session.commit()
    return jsonify({"message": "Profissional removido da clínica"}), 200
