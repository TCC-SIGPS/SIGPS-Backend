FROM python:3.11-slim

# Define o diretório de trabalho dentro do container
WORKDIR /app

# Copia o arquivo de dependências
COPY requirements.txt .

# Instala as dependências
RUN pip install --no-cache-dir -r requirements.txt

# Instala o gunicorn para servir a aplicação em produção (opcional, mas recomendado)
RUN pip install gunicorn

# Copia todo o código do projeto para o container
COPY . .

# Cria o diretório de uploads se não existir
RUN mkdir -p uploads/exames

# Variáveis de ambiente padrão
ENV FLASK_APP=run.py
ENV FLASK_ENV=development
ENV PYTHONUNBUFFERED=1

# Expõe a porta que o Flask vai rodar
EXPOSE 5000

# Comando para iniciar a aplicação
# Em desenvolvimento, o docker-compose pode sobrescrever isso com 'flask run'
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "run:app"]
