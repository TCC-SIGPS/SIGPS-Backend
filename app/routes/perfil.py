import os, re
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from app.models import db, User, Especialista, Clinica, ClinicaEspecialista

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

    esp = u.especialista_info

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
                 "especialidade": m.especialista.especialista_info.especialidade if m.especialista.especialista_info else '', 
                 "crm": m.especialista.especialista_info.crm if m.especialista.especialista_info else '',
                 "statusVerificacao": m.especialista.especialista_info.status_verificacao if m.especialista.especialista_info else 'nao_verificado'}
                for m in c.membros
            ]
        return d

    return {
        "id": u.id,
        "nome": u.nome,
        "email": u.email,
        "perfil": u.perfil,
        "genero": u.genero,
        "tipoProfissional": esp.tipo_profissional if esp else None,
        "especialidade": esp.especialidade if esp else None,
        "conselho": esp.conselho_tipo if esp else None,
        "numeroRegistro": esp.numero_registro if esp else None,
        "uf": esp.uf if esp else None,
        "crm": esp.crm if esp else None,
        "foto": esp.foto if esp else None,
        "sobre": esp.sobre if esp else None,
        "localAtendimento": esp.local_atendimento if esp else None,
        "statusVerificacao": esp.status_verificacao if esp else 'nao_verificado',
        "documentoEnviado": bool(esp.documento_verificacao if esp else False),
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

    campos_usuario = {'nome': 'nome', 'genero': 'genero'}
    for campo_json, campo_db in campos_usuario.items():
        if campo_json in dados and dados[campo_json] is not None:
            setattr(u, campo_db, dados[campo_json])

    # Se tiver perfil de especialista, atualiza campos do especialista
    if u.perfil == 'Especialista' and u.especialista_info:
        campos_esp = {
            'especialidade': 'especialidade',
            'tipoProfissional': 'tipo_profissional', 'conselho': 'conselho_tipo',
            'numeroRegistro': 'numero_registro', 'uf': 'uf',
            'foto': 'foto', 'sobre': 'sobre', 'localAtendimento': 'local_atendimento'
        }
        for campo_json, campo_db in campos_esp.items():
            if campo_json in dados and dados[campo_json] is not None:
                setattr(u.especialista_info, campo_db, dados[campo_json])
        
        if u.especialista_info.conselho_tipo and u.especialista_info.numero_registro and u.especialista_info.uf:
            u.especialista_info.crm = _registro_completo(u.especialista_info.conselho_tipo, u.especialista_info.numero_registro, u.especialista_info.uf)

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
    
    if not u.especialista_info:
        esp = Especialista(user_id=u.id)
        db.session.add(esp)
    else:
        esp = u.especialista_info

    esp.tipo_profissional = tipo
    esp.conselho_tipo = conselho
    esp.numero_registro = numero
    esp.uf = uf
    esp.especialidade = especialidade
    esp.crm = _registro_completo(conselho, numero, uf)
    esp.sobre = dados.get('sobre', '')
    esp.local_atendimento = dados.get('localAtendimento', '')
    esp.status_verificacao = 'nao_verificado'

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

    if not u.especialista_info:
        return jsonify({"message": "Perfil de especialista não encontrado"}), 400

    u.especialista_info.documento_verificacao = caminho
    u.especialista_info.status_verificacao = 'em_analise'
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

    if not u.especialista_info:
        return jsonify({"message": "O usuário não é especialista"}), 400

    u.especialista_info.status_verificacao = novo_status
    db.session.commit()
    return jsonify({"message": f"Status atualizado para {novo_status}"}), 200
