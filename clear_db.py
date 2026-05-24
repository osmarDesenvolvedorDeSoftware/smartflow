import os
from sqlalchemy import create_engine, text

# Use the same DATABASE_URL as the application
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/plaquinhas")
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    # Remove all data and reset auto-increment counters
    conn.execute(text("TRUNCATE TABLE historico_cliques, placas, usuarios RESTART IDENTITY CASCADE;"))
    conn.commit()

print("✅ Banco de dados 'plaquinhas' limpado com sucesso.")
