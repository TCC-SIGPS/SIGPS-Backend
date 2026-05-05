from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import db, ChatMessage, User
from datetime import datetime

bp_chat = Blueprint('chat', __name__, url_prefix='/api/v1/chat')

@bp_chat.route('/messages', methods=['GET'])
@jwt_required()
def get_messages():
    user_id = int(get_jwt_identity())
    # Para o MVP simples, vamos retornar mensagens onde o usuário logado é o remetente ou destinatário.
    # Em um sistema real, seria filtrado por canal/sessão.
    messages = ChatMessage.query.filter(
        db.or_(ChatMessage.sender_id == user_id, ChatMessage.receiver_id == user_id, ChatMessage.receiver_id.is_(None))
    ).order_by(ChatMessage.created_at.asc()).all()

    resultado = []
    for m in messages:
        sender_type = 'me' if m.sender_id == user_id else ('sistema' if m.sender.perfil == 'Admin' else 'user')
        resultado.append({
            "id": m.id,
            "sender": sender_type,
            "senderName": m.sender.nome,
            "text": m.text,
            "time": m.created_at.strftime('%H:%M'),
            "read": m.read
        })
    return jsonify(resultado), 200

@bp_chat.route('/messages', methods=['POST'])
@jwt_required()
def send_message():
    user_id = int(get_jwt_identity())
    dados = request.get_json()
    text = dados.get('text')
    
    if not text:
        return jsonify({"message": "Texto não pode ser vazio"}), 400

    nova_mensagem = ChatMessage(
        sender_id=user_id,
        text=text,
        receiver_id=None # Broadcast genérico pro MVP
    )
    db.session.add(nova_mensagem)
    db.session.commit()

    return jsonify({
        "id": nova_mensagem.id,
        "sender": 'me',
        "senderName": nova_mensagem.sender.nome,
        "text": nova_mensagem.text,
        "time": nova_mensagem.created_at.strftime('%H:%M'),
        "read": False
    }), 201

@bp_chat.route('/messages/read', methods=['POST'])
@jwt_required()
def mark_read():
    user_id = int(get_jwt_identity())
    # Marca as mensagens enviadas para este usuário como lidas
    mensagens = ChatMessage.query.filter(ChatMessage.receiver_id == user_id, ChatMessage.read == False).all()
    for m in mensagens:
        m.read = True
    db.session.commit()
    return jsonify({"message": "Marcadas como lidas"}), 200

@bp_chat.route('/messages/clear', methods=['DELETE'])
@jwt_required()
def clear_history():
    user_id = int(get_jwt_identity())
    # Por segurança, deleta apenas as mensagens do próprio usuário no MVP
    ChatMessage.query.filter(ChatMessage.sender_id == user_id).delete()
    db.session.commit()
    return jsonify({"message": "Histórico apagado"}), 200
