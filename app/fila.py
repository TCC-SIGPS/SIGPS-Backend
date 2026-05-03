from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import db, Paciente, FilaAtendimento, User

# Ajustado para o prefixo /api/v1/queue conforme o guia técnico
bp_fila = Blueprint('fila', __name__, url_prefix='/api/v1/queue')

# 1. INSERIR NA FILA COM CÁLCULO DE SCORE (POST /api/v1/queue/check-in)
@bp_fila.route('/check-in', methods=['POST'])
@jwt_required()
def check_in():
    usuario_id = get_jwt_identity()
    paciente = Paciente.query.filter_by(user_id=usuario_id).first()
    
    if not paciente:
        return jsonify({"message": "Paciente não encontrado. Complete seu cadastro."}), 404

    ja_esta_na_fila = FilaAtendimento.query.filter_by(paciente_id=paciente.id, status='Aguardando').first()
    if ja_esta_na_fila:
        return jsonify({"message": "Você já está na fila de espera."}), 400

    # LÓGICA DE SCORE E PRIORIDADE (O núcleo da IA do SIGPS)
    score = 20  # Score base
    nivel_prioridade = 1  # 1: Normal, 2: Alta, 3: Extrema
    comorbidades = paciente.comorbidades.lower() if paciente.comorbidades else ""
    
    # Simulação de análise de risco por IA[cite: 1]
    if any(doenca in comorbidades for doenca in ["diabetes", "hipertensão", "hipertensao", "cancer"]):
        score = 85
        nivel_prioridade = 3 # Extrema[cite: 1]

    nova_entrada = FilaAtendimento(
        paciente_id=paciente.id,
        prioridade=nivel_prioridade,
        score=score,
        status='Aguardando'
    )

    db.session.add(nova_entrada)
    db.session.commit()

    return jsonify({
        "message": "Check-in realizado!",
        "score": score,
        "prioridade": "Extrema" if nivel_prioridade == 3 else "Normal"
    }), 201

# 2. LISTA A FILA ORDENADA (GET /api/v1/queue/)[cite: 1]
@bp_fila.route('/', methods=['GET'])
def listar_fila():
    # Ordenação automática: scores mais altos e categorias de prioridade ('Extrema' > 'Alta')[cite: 1]
    fila = FilaAtendimento.query.filter_by(status='Aguardando').order_by(
        FilaAtendimento.prioridade.desc(), 
        FilaAtendimento.score.desc(),
        FilaAtendimento.data_chegada.asc()
    ).all()
    
    resultado = []
    for item in fila:
        resultado.append({
            "posicao": len(resultado) + 1,
            "paciente": item.paciente.usuario.nome,
            "score": item.score,
            "prioridade": item.prioridade,
            "chegada": item.data_chegada.strftime('%H:%M'),
            "id": item.id
        })
        
    return jsonify(resultado), 200

# 3. ALTERA STATUS - CHAMAR/FINALIZAR (PATCH /api/v1/queue/{id}/status)[cite: 1]
@bp_fila.route('/<int:id>/status', methods=['PATCH'])
@jwt_required()
def alterar_status(id):
    usuario_id = get_jwt_identity()
    usuario_logado = User.query.get(usuario_id)
    
    if usuario_logado.perfil not in ['Especialista', 'Admin']:
        return jsonify({"message": "Acesso negado."}), 403

    atendimento = FilaAtendimento.query.get_or_404(id)
    dados = request.get_json()
    
    # Altera status (Ex: 'Aguardando' para 'Em Atendimento' ou 'Finalizado')[cite: 1]
    novo_status = dados.get('status')
    if novo_status:
        atendimento.status = novo_status
        db.session.commit()

    return jsonify({"message": f"Status atualizado para {atendimento.status}"}), 200

# 4. ANÁLISE PREDITIVA DE RISCO (GET /api/v1/queue/ai-analysis)[cite: 1]
@bp_fila.route('/ai-analysis', methods=['GET'])
@jwt_required()
def ai_analysis():
    # Retorna uma visão geral baseada nos scores da IA[cite: 1]
    total_aguardando = FilaAtendimento.query.filter_by(status='Aguardando').count()
    criticos = FilaAtendimento.query.filter(FilaAtendimento.score >= 80, FilaAtendimento.status == 'Aguardando').count()
    
    return jsonify({
        "analise": "Alerta de alta demanda" if criticos > 3 else "Fluxo normal",
        "pacientes_criticos": criticos,
        "total_na_fila": total_aguardando
    }), 200