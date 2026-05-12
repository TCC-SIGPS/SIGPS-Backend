import os, re
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from app.models import db, User, Clinica, ClinicaEspecialista

bp_perfil = Blueprint('perfil', __name__, url_prefix='/api/v1/perfil')

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'uploads', 'documentos')
ALLOWED_EXT = {'pdf', 'jpg', 'jpeg', 'png'}

STATUS_VERIFICACAO = ['nao_verificado', 'em_analise', 'verificado', 'rejeitado']


def _allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT


def _registro_completo(conselho, numero, uf):
    """Monta o campo legado crm: 'CRM 12345-SP'"""
    return f"{conselho} {numero}-{uf}" if conselho and numero and uf else None


def _serializar_usuario(u):
    clinica_admin = Clinica.query.filter_by(admin_id=u.id).first()
    membro = ClinicaEspecialista.query.filter_by(especialista_id=u.id).first()
    clinica_membro = membro.clinica if membro else None

    def _clinica_dict(c, com_membros=False):
        d = {
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
            "endereco": c.endereco or '',
            "statusVerificacao": c.status_verificacao or 'pendente'
        }
        if com_membros:
            d['especialistas'] = [
                {"id": m.especialista_id, "nome": m.especialista.nome,
                 "especialidade": m.especialista.especialidade or '', "crm": m.especialista.crm or '',
                 "statusVerificacao": m.especialista.status_verificacao or 'nao_verificado'}
                for m in c.membros
            ]
        return d

    return {
        "id": u.id,
        "nome": u.nome,
        "email": u.email,
        "perfil": u.perfil,
        "tipoProfissional": u.tipo_profissional,
        "especialidade": u.especialidade,
        "conselho": u.conselho_tipo,
        "numeroRegistro": u.numero_registro,
        "uf": u.uf,
        "crm": u.crm,
        "foto": u.foto,
        "sobre": u.sobre,
        "localAtendimento": u.local_atendimento,
        "statusVerificacao": u.status_verificacao or 'nao_verificado',
        "documentoEnviado": bool(u.documento_verificacao),
        "clinicaAdmin": _clinica_dict(clinica_admin, com_membros=True) if clinica_admin else None,
        "clinicaVinculada": _clinica_dict(clinica_membro) if clinica_membro else None
    }


@bp_perfil.route('/me', methods=['GET'])
@jwt_required()
def get_perfil():
    user_id = int(get_jwt_identity())
    u = User.query.get_or_404(user_id)
    return jsonify(_serializar_usuario(u)), 200


@bp_perfil.route('/me', methods=['PATCH'])
@jwt_required()
def atualizar_perfil():
    user_id = int(get_jwt_identity())
    u = User.query.get_or_404(user_id)
    dados = request.get_json()

    campos = {
        'nome': 'nome', 'especialidade': 'especialidade',
        'tipoProfissional': 'tipo_profissional', 'conselho': 'conselho_tipo',
        'numeroRegistro': 'numero_registro', 'uf': 'uf',
        'foto': 'foto', 'sobre': 'sobre', 'localAtendimento': 'local_atendimento'
    }
    for campo_json, campo_db in campos.items():
        if campo_json in dados and dados[campo_json] is not None:
            setattr(u, campo_db, dados[campo_json])

    # Atualiza campo legado crm
    if u.conselho_tipo and u.numero_registro and u.uf:
        u.crm = _registro_completo(u.conselho_tipo, u.numero_registro, u.uf)

    db.session.commit()
    return jsonify({"message": "Perfil atualizado", "perfil": _serializar_usuario(u)}), 200


@bp_perfil.route('/tornar-especialista', methods=['POST'])
@jwt_required()
def tornar_especialista():
    user_id = int(get_jwt_identity())
    u = User.query.get_or_404(user_id)
    dados = request.get_json()

    conselho = (dados.get('conselho') or '').strip().upper()
    numero = (dados.get('numeroRegistro') or '').strip()
    uf = (dados.get('uf') or '').strip().upper()
    especialidade = (dados.get('especialidade') or '').strip()
    tipo = (dados.get('tipoProfissional') or '').strip()

    if not all([conselho, numero, uf, especialidade, tipo]):
        return jsonify({"message": "Tipo, conselho, número, UF e especialidade são obrigatórios"}), 400

    u.perfil = 'Especialista'
    u.tipo_profissional = tipo
    u.conselho_tipo = conselho
    u.numero_registro = numero
    u.uf = uf
    u.especialidade = especialidade
    u.crm = _registro_completo(conselho, numero, uf)
    u.sobre = dados.get('sobre', '')
    u.local_atendimento = dados.get('localAtendimento', '')
    u.status_verificacao = 'nao_verificado'

    db.session.commit()
    return jsonify({"message": "Perfil profissional criado!", "perfil": _serializar_usuario(u)}), 200


@bp_perfil.route('/documento', methods=['POST'])
@jwt_required()
def enviar_documento():
    """Recebe upload do documento de verificação e muda status para em_analise."""
    user_id = int(get_jwt_identity())
    u = User.query.get_or_404(user_id)

    if 'documento' not in request.files:
        return jsonify({"message": "Nenhum arquivo enviado"}), 400

    arquivo = request.files['documento']
    if not arquivo.filename or not _allowed_file(arquivo.filename):
        return jsonify({"message": "Formato inválido. Use PDF, JPG ou PNG"}), 400

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    nome_seguro = f"user_{user_id}_{secure_filename(arquivo.filename)}"
    caminho = os.path.join(UPLOAD_FOLDER, nome_seguro)
    arquivo.save(caminho)

    u.documento_verificacao = caminho
    u.status_verificacao = 'em_analise'
    db.session.commit()

    return jsonify({"message": "Documento enviado. Aguarde análise em até 2 dias úteis.", "status": "em_analise"}), 200


@bp_perfil.route('/verificacao/<int:user_id>', methods=['PATCH'])
@jwt_required()
def atualizar_verificacao(user_id):
    """Admin atualiza status de verificação de um profissional."""
    admin_id = int(get_jwt_identity())
    admin = User.query.get_or_404(admin_id)
    if admin.perfil != 'Admin':
        return jsonify({"message": "Acesso negado"}), 403

    u = User.query.get_or_404(user_id)
    dados = request.get_json()
    novo_status = dados.get('status')

    if novo_status not in STATUS_VERIFICACAO:
        return jsonify({"message": f"Status inválido. Use: {STATUS_VERIFICACAO}"}), 400

    u.status_verificacao = novo_status
    db.session.commit()
    return jsonify({"message": f"Status atualizado para {novo_status}"}), 200
