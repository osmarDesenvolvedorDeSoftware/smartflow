-- Adiciona coluna is_admin na tabela de usuarios para identificar administradores
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE;

-- Adiciona coluna status_ativa na tabela de placas para suspensão temporária
ALTER TABLE placas ADD COLUMN IF NOT EXISTS status_ativa BOOLEAN NOT NULL DEFAULT TRUE;

-- Insere o usuário SuperAdmin padrão (documento: '00000000000', senha: 'senha123')
INSERT INTO usuarios (documento, senha, nome_estabelecimento, is_admin)
VALUES ('00000000000', '$2b$12$4d6HlWM7nWNdrGMH0mB.N.bWRtEEf5P3DA//BAb2nNc2OzSomEppS', 'Administrador do Sistema', TRUE)
ON CONFLICT (documento) DO NOTHING;
