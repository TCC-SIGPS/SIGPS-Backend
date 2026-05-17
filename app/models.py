from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    senha = db.Column(db.String(255), nullable=False)
    # Perfis: Paciente, Visualizador, Gestor, Especialista, Admin
    perfil = db.Column(db.String(20), default='Paciente', nullable=False)

    # Campos adicionais para Especialistas
    especialidade = db.Column(db.String(100), nullable=True)
    tipo_profissional = db.Column(db.String(50), nullable=True)   # Médico, Dentista, Enfermeiro...
    conselho_tipo = db.Column(db.String(10), nullable=True)       # CRM, CRO, COREN, CRP...
    numero_registro = db.Column(db.String(30), nullable=True)     # Número sem UF
    crm = db.Column(db.String(30), nullable=True)                 # Mantido por compat. (conselho_tipo + numero)
    foto = db.Column(db.String(500), nullable=True)
    sobre = db.Column(db.Text, nullable=True)
    uf = db.Column(db.String(2), nullable=True)
    local_atendimento = db.Column(db.String(300), nullable=True)
    # Verificação profissional
    status_verificacao = db.Column(db.String(20), default='nao_verificado', nullable=True)
    documento_verificacao = db.Column(db.String(500), nullable=True)

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
    genero = db.Column(db.String(1), nullable=False) # <--- ADICIONADO AQUI PARA A IA
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
    
    # Score de IA (0 a 100) exigido pelo Guia Técnico
    score = db.Column(db.Integer, default=0)
    
    # Status: Aguardando, Em Atendimento, Finalizado
    status = db.Column(db.String(20), default='Aguardando')
    
    data_chegada = db.Column(db.DateTime, default=db.func.current_timestamp())

    paciente = db.relationship('Paciente', backref='na_fila')

    def __repr__(self):
        return f'<Fila ID {self.id} - Paciente {self.paciente_id}>'

class Exame(db.Model):
    __tablename__ = 'exames'

    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey('pacientes.id'), nullable=False)
    
    nome_exame = db.Column(db.String(100), nullable=False)
    arquivo_path = db.Column(db.String(255), nullable=False)
    data_upload = db.Column(db.DateTime, default=db.func.current_timestamp())

    paciente = db.relationship('Paciente', backref='meus_exames')

    def __repr__(self):
        return f'<Exame {self.nome_exame} - Paciente {self.paciente_id}>'

class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'

    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    text = db.Column(db.Text, nullable=False)
    read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    sender = db.relationship('User', foreign_keys=[sender_id])
    receiver = db.relationship('User', foreign_keys=[receiver_id])

class Clinica(db.Model):
    __tablename__ = 'clinicas'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), nullable=False)
    tipo = db.Column(db.String(50), default='Clínica')
    cnpj = db.Column(db.String(18), unique=True)
    telefone = db.Column(db.String(20))
    email_contato = db.Column(db.String(100))
    cep = db.Column(db.String(9))
    rua = db.Column(db.String(200))
    numero = db.Column(db.String(10))
    complemento = db.Column(db.String(100))
    bairro = db.Column(db.String(100))
    cidade = db.Column(db.String(100))
    estado = db.Column(db.String(2))
    endereco = db.Column(db.Text)
    status_verificacao = db.Column(db.String(20), default='pendente')
    admin_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    admin = db.relationship('User', foreign_keys=[admin_id], backref='clinicas_gerenciadas')

    def __repr__(self):
        return f'<Clinica {self.nome}>'

class ClinicaEspecialista(db.Model):
    __tablename__ = 'clinica_specialistas'

    id = db.Column(db.Integer, primary_key=True)
    clinica_id = db.Column(db.Integer, db.ForeignKey('clinicas.id'), nullable=False)
    especialista_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    clinica = db.relationship('Clinica', backref='membros')
    especialista = db.relationship('User', foreign_keys=[especialista_id], backref='clinicas_vinculadas')

    def __repr__(self):
        return f'<ClinicaEspecialista clinica={self.clinica_id} esp={self.especialista_id}>'

class Agenda(db.Model):
    __tablename__ = 'agendas'

    id = db.Column(db.Integer, primary_key=True)
    especialista_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    data = db.Column(db.Date, nullable=False)
    horarios_disponiveis = db.Column(db.String(255))

    especialista = db.relationship('User', foreign_keys=[especialista_id])

class Consulta(db.Model):
    __tablename__ = 'consultas'

    id = db.Column(db.Integer, primary_key=True)
    agenda_id = db.Column(db.Integer, db.ForeignKey('agendas.id'), nullable=False)
    paciente_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    horario = db.Column(db.String(5), nullable=False)
    status = db.Column(db.String(20), default='Agendada')
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    agenda = db.relationship('Agenda', backref='consultas')
    paciente = db.relationship('User', foreign_keys=[paciente_id])