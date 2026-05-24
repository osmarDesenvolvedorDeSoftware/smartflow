FROM python:3.11-slim

WORKDIR /code

# Instalar dependências de compilação necessárias para psycopg2, se aplicável,
# mas como usamos psycopg2-binary, a versão binária pré-compilada deve ser suficiente.
# Mantemos o slim leve.
COPY backend/requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt


COPY backend/app /code/app
COPY frontend /code/frontend

EXPOSE 8000
