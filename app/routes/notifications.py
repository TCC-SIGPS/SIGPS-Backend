from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import db, Notification

bp_notifications = Blueprint('notifications', __name__, url_prefix='/api/v1/notifications')

@bp_notifications.route('/', methods=['GET'])
@jwt_required()
def list_notifications():
    user_id = int(get_jwt_identity())
    notifs = Notification.query.filter_by(user_id=user_id).order_by(Notification.id.desc()).all()
    return jsonify([n.to_dict() for n in notifs]), 200

@bp_notifications.route('/mark-read', methods=['POST'])
@jwt_required()
def mark_read():
    user_id = int(get_jwt_identity())
    dados = request.get_json() or {}
    
    notification_id = dados.get('id')
    if notification_id:
        notif = Notification.query.filter_by(id=notification_id, user_id=user_id).first()
        if notif:
            notif.read = True
            db.session.commit()
    else:
        # Marcar todas como lidas
        Notification.query.filter_by(user_id=user_id, read=False).update({Notification.read: True})
        db.session.commit()
        
    return jsonify({"message": "Notificações marcadas como lidas"}), 200
