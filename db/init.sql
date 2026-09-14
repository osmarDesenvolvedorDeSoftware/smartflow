-- Tabela 1: usuarios
CREATE TABLE IF NOT EXISTS usuarios (
    documento VARCHAR(20) PRIMARY KEY,
    senha VARCHAR(255) NOT NULL,
    nome_estabelecimento VARCHAR(100) NOT NULL,
    is_admin BOOLEAN NOT NULL DEFAULT FALSE
);

-- Tabela 2: placas
CREATE TABLE IF NOT EXISTS placas (
    id_placa INT PRIMARY KEY,
    dono_documento VARCHAR(20) REFERENCES usuarios(documento) ON DELETE CASCADE,
    nome_exibicao VARCHAR(120),
    tipo_dispositivo VARCHAR(30),
    local_uso VARCHAR(120),
    loja_unidade VARCHAR(120),
    responsavel VARCHAR(120),
    observacao VARCHAR(500),
    link_frente VARCHAR(500),
    link_verso VARCHAR(500),
    pix_chave VARCHAR(100),
    pix_tipo_valor VARCHAR(10) CHECK (pix_tipo_valor IN ('fixo', 'aberto')),
    pix_valor_fixo NUMERIC(10, 2),
    status_ativa BOOLEAN NOT NULL DEFAULT TRUE
);

-- Tabela 3: historico_cliques
CREATE TABLE IF NOT EXISTS historico_cliques (
    id_clique SERIAL PRIMARY KEY,
    id_placa INT REFERENCES placas(id_placa) ON DELETE CASCADE,
    data_hora TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    lado VARCHAR(10) CHECK (lado IN ('Frente', 'Verso'))
);

-- Inserção de dados iniciais (Seed)
-- Somente o SuperAdmin é criado na instalação. Comerciantes e placas são cadastrados pelo painel
-- (id_placa começa em 1 para a operação real).
INSERT INTO usuarios (documento, senha, nome_estabelecimento, is_admin)
VALUES ('00000000000', '$2b$12$4d6HlWM7nWNdrGMH0mB.N.bWRtEEf5P3DA//BAb2nNc2OzSomEppS', 'Administrador do Sistema', TRUE)
ON CONFLICT (documento) DO NOTHING;
