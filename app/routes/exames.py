import os
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required
from werkzeug.utils import secure_filename
from app.models import db, Exame, Paciente

# Blueprint seguindo o padrão /api/v1/exams do guia técnico
bp_exames = Blueprint('exames', __name__, url_prefix='/api/v1/exams')

# 1. UPLOAD DE EXAME (POST /api/v1/exams/upload)
@bp_exames.route('/upload', methods=['POST'])
@jwt_required()
def upload_exame():
    # Verifica se o arquivo foi enviado na requisição
    if 'arquivo' not in request.files:
        return jsonify({"message": "Nenhum arquivo enviado"}), 400
    
    arquivo = request.files['arquivo']
    paciente_id = request.form.get('paciente_id')
    nome_exame = request.form.get('nome_exame')

    if arquivo.filename == '':
        return jsonify({"message": "Arquivo sem nome"}), 400

    if arquivo and paciente_id:
        # secure_filename limpa o nome do arquivo para evitar ataques de path traversal
        filename = secure_filename(f"paciente_{paciente_id}_{arquivo.filename}")
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        
        # Salva o arquivo na pasta configurada no run.py
        arquivo.save(filepath)

        # Registra o exame no banco de dados
        novo_exame = Exame(
            paciente_id=paciente_id,
            nome_exame=nome_exame if nome_exame else arquivo.filename,
            arquivo_path=filename # Guardamos apenas o nome para facilitar o acesso
        )

        db.session.add(novo_exame)
        db.session.commit()

        # Registrar notificação para o paciente
        from app.models import Notification
        paciente_obj = Paciente.query.get(paciente_id)
        if paciente_obj:
            Notification.create(
                user_id=paciente_obj.user_id,
                message=f"Seu Exame '{novo_exame.nome_exame}' está Disponível",
                route="/painel/exames"
            )

        return jsonify({"message": "Exame enviado com sucesso!", "caminho": filename}), 201

    return jsonify({"message": "Dados incompletos"}), 400

# 2. LISTAR EXAMES DE UM PACIENTE (GET /api/v1/exams/patient/{id})
@bp_exames.route('/patient/<int:paciente_id>', methods=['GET'])
@jwt_required()
def listar_exames(paciente_id):
    exames = Exame.query.filter_by(paciente_id=paciente_id).all()
    
    resultado = []
    for e in exames:
        resultado.append({
            "id": e.id,
            "nome_exame": e.nome_exame,
            "data_upload": e.data_upload.strftime('%d/%m/%Y %H:%M'),
            "arquivo": e.arquivo_path
        })
    
    return jsonify(resultado), 200

# 3. DELETAR EXAME (DELETE /api/v1/exams/{id})
@bp_exames.route('/<int:id>', methods=['DELETE'])
@jwt_required()
def deletar_exame(id):
    exame = Exame.query.get_or_404(id)
    
    # Tenta remover o arquivo físico do servidor
    try:
        path_completo = os.path.join(current_app.config['UPLOAD_FOLDER'], exame.arquivo_path)
        if os.path.exists(path_completo):
            os.remove(path_completo)
    except Exception as e:
        print(f"Erro ao deletar arquivo físico: {e}")

    db.session.delete(exame)
    db.session.commit()
    
    return jsonify({"message": "Exame removido com sucesso"}), 200