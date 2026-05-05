from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    senha = db.Column(db.String(255), nullable=False)
    # Perfis: Paciente, Visualizador, Gestor, Especialista, Admin
    perfil = db.Column(db.String(20), default='Paciente', nullable=False)

    def set_password(self, password):
        self.senha = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.senha, password)

class Paciente(db.Model):
    __tablename__ = 'pacientes'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    
    cpf = db.Column(db.String(14), unique=True, nullable=False)
    data_nascimento = db.Column(db.Date, nullable=False)
    telefone = db.Column(db.String(20))
    
    tipo_sanguineo = db.Column(db.String(3))
    alergias = db.Column(db.Text)
    comorbidades = db.Column(db.Text) 

    usuario = db.relationship('User', backref=db.backref('paciente_info', uselist=False))

    def __repr__(self):
        return f'<Paciente {self.cpf}>'

class FilaAtendimento(db.Model):
    __tablename__ = 'fila_atendimento'

    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey('pacientes.id'), nullable=False)
    
    # Níveis de prioridade (ex: 1: Verde, 2: Amarelo, 3: Vermelho)
    prioridade = db.Column(db.Integer, default=1)
    
    # Score de IA (0 a 100) exigido pelo Guia Técnico[cite: 1]
    score = db.Column(db.Integer, default=0)
    
    # Status: Aguardando, Em Atendimento, Finalizado[cite: 1]
    status = db.Column(db.String(20), default='Aguardando')
    
    data_chegada = db.Column(db.DateTime, default=db.func.current_timestamp())

    paciente = db.relationship('Paciente', backref='na_fila')

    def __repr__(self):
        return f'<Fila ID {self.id} - Paciente {self.paciente_id}>'

# --- NOVO MODELO PARA EXAMES ---
class Exame(db.Model):
    __tablename__ = 'exames'

    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey('pacientes.id'), nullable=False)
    
    nome_exame = db.Column(db.String(100), nullable=False)
    # Caminho onde o PDF/Imagem será salvo no servidor[cite: 1]
    arquivo_path = db.Column(db.String(255), nullable=False)
    data_upload = db.Column(db.DateTime, default=db.func.current_timestamp())

    paciente = db.relationship('Paciente', backref='meus_exames')

    def __repr__(self):
        return f'<Exame {self.nome_exame} - Paciente {self.paciente_id}>'

# --- NOVO MODELO PARA CHAT ---
class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'

    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True) # Pode ser null se for broadcast/sistema
    text = db.Column(db.Text, nullable=False)
    read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    sender = db.relationship('User', foreign_keys=[sender_id])
    receiver = db.relationship('User', foreign_keys=[receiver_id])

# --- NOVO MODELO PARA AGENDA ---
class Agenda(db.Model):
    __tablename__ = 'agendas'

    id = db.Column(db.Integer, primary_key=True)
    especialista_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    data = db.Column(db.Date, nullable=False)
    horarios_disponiveis = db.Column(db.String(255)) # Ex: "08:00,09:00,10:00"

    especialista = db.relationship('User', foreign_keys=[especialista_id])

class Consulta(db.Model):
    __tablename__ = 'consultas'

    id = db.Column(db.Integer, primary_key=True)
    agenda_id = db.Column(db.Integer, db.ForeignKey('agendas.id'), nullable=False)
    paciente_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    horario = db.Column(db.String(5), nullable=False)
    status = db.Column(db.String(20), default='Agendada') # Agendada, Cancelada, Concluída
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    agenda = db.relationship('Agenda', backref='consultas')
    paciente = db.relationship('User', foreign_keys=[paciente_id])