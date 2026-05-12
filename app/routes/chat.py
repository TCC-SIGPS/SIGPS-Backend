from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import db, ChatMessage, User

bp_chat = Blueprint('chat', __name__, url_prefix='/api/v1/chat')


def _serializar_msg(m, user_id):
    return {
        "id": m.id,
        "sender": "me" if m.sender_id == user_id else "other",
        "senderId": m.sender_id,
        "senderName": m.sender.nome,
        "text": m.text,
        "time": m.created_at.strftime('%H:%M'),
        "read": m.read
    }


@bp_chat.route('/conversations', methods=['GET'])
@jwt_required()
def listar_conversas():
    """Retorna todos os parceiros com quem o usuário trocou mensagens."""
    user_id = int(get_jwt_identity())

    sent_ids = db.session.query(ChatMessage.receiver_id).filter(
        ChatMessage.sender_id == user_id,
        ChatMessage.receiver_id.isnot(None)
    ).distinct()

    received_ids = db.session.query(ChatMessage.sender_id).filter(
        ChatMessage.receiver_id == user_id
    ).distinct()

    partner_ids = {pid for (pid,) in sent_ids} | {pid for (pid,) in received_ids}

    resultado = []
    for pid in partner_ids:
        parceiro = User.query.get(pid)
        if not parceiro:
            continue

        ultima = (
            ChatMessage.query
            .filter(
                db.or_(
                    db.and_(ChatMessage.sender_id == user_id, ChatMessage.receiver_id == pid),
                    db.and_(ChatMessage.sender_id == pid,     ChatMessage.receiver_id == user_id)
                )
            )
            .order_by(ChatMessage.created_at.desc())
            .first()
        )

        nao_lidas = ChatMessage.query.filter_by(
            sender_id=pid, receiver_id=user_id, read=False
        ).count()

        resultado.append({
            "userId": pid,
            "userName": parceiro.nome,
            "userRole": parceiro.perfil,
            "userFoto": parceiro.foto or None,
            "lastMessage": ultima.text if ultima else "",
            "lastMessageTime": ultima.created_at.strftime('%H:%M') if ultima else "",
            "lastMessageDate": ultima.created_at.strftime('%d/%m/%Y') if ultima else "",
            "unreadCount": nao_lidas
        })

    resultado.sort(key=lambda x: x['lastMessageTime'], reverse=True)
    return jsonify(resultado), 200


@bp_chat.route('/messages/<int:other_id>', methods=['GET'])
@jwt_required()
def get_mensagens(other_id):
    """Retorna APENAS as mensagens entre o usuário logado e other_id."""
    user_id = int(get_jwt_identity())

    mensagens = (
        ChatMessage.query
        .filter(
            db.or_(
                db.and_(ChatMessage.sender_id == user_id, ChatMessage.receiver_id == other_id),
                db.and_(ChatMessage.sender_id == other_id, ChatMessage.receiver_id == user_id)
            )
        )
        .order_by(ChatMessage.created_at.asc())
        .all()
    )

    return jsonify([_serializar_msg(m, user_id) for m in mensagens]), 200


@bp_chat.route('/messages/<int:other_id>', methods=['POST'])
@jwt_required()
def enviar_mensagem(other_id):
    """Envia uma mensagem privada para other_id."""
    user_id = int(get_jwt_identity())
    dados = request.get_json()
    text = (dados.get('text') or '').strip()

    if not text:
        return jsonify({"message": "Texto não pode ser vazio"}), 400

    User.query.get_or_404(other_id)  # garante que o destinatário existe

    nova = ChatMessage(sender_id=user_id, receiver_id=other_id, text=text)
    db.session.add(nova)
    db.session.commit()

    return jsonify(_serializar_msg(nova, user_id)), 201


@bp_chat.route('/messages/<int:other_id>/read', methods=['PATCH'])
@jwt_required()
def marcar_lidas(other_id):
    """Marca como lidas todas as mensagens recebidas de other_id."""
    user_id = int(get_jwt_identity())
    ChatMessage.query.filter_by(
        sender_id=other_id, receiver_id=user_id, read=False
    ).update({'read': True})
    db.session.commit()
    return jsonify({"message": "Marcadas como lidas"}), 200


@bp_chat.route('/messages/<int:other_id>', methods=['DELETE'])
@jwt_required()
def apagar_conversa(other_id):
    """Apaga toda a conversa entre o usuário logado e other_id."""
    user_id = int(get_jwt_identity())
    ChatMessage.query.filter(
        db.or_(
            db.and_(ChatMessage.sender_id == user_id, ChatMessage.receiver_id == other_id),
            db.and_(ChatMessage.sender_id == other_id, ChatMessage.receiver_id == user_id)
        )
    ).delete(synchronize_session=False)
    db.session.commit()
    return jsonify({"message": "Conversa apagada"}), 200
