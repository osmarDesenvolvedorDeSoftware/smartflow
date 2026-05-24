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
-- O documento de teste será '12345678901' (pode representar CPF) e a senha hash do bcrypt para 'senha123'
-- Hash gerado de 'senha123': $2b$12$eImi/A8FzSsk.xO2BvO.v.mC9g2z/tT6F/mN3wzT8i4R7W1xMzeK. (vamos garantir que o backend também aceite ou atualize)
INSERT INTO usuarios (documento, senha, nome_estabelecimento, is_admin)
VALUES
('12345678901', '$2b$12$4d6HlWM7nWNdrGMH0mB.N.bWRtEEf5P3DA//BAb2nNc2OzSomEppS', 'Barbearia do Pedro', FALSE),
('00000000000', '$2b$12$4d6HlWM7nWNdrGMH0mB.N.bWRtEEf5P3DA//BAb2nNc2OzSomEppS', 'Administrador do Sistema', TRUE)
ON CONFLICT (documento) DO NOTHING;

-- Placas iniciais para o cliente '12345678901'
INSERT INTO placas (id_placa, dono_documento, link_frente, link_verso)
VALUES
(1001, '12345678901', 'https://goo.gl/maps/example1', 'https://cardapio.example.com/pedro'),
(1002, '12345678901', 'https://goo.gl/maps/example2', 'https://pix.example.com/pedro')
ON CONFLICT (id_placa) DO NOTHING;

-- Histórico de cliques simulado para gerar gráficos iniciais interessantes
-- Cliques na placa 1001 nos últimos dias
INSERT INTO historico_cliques (id_placa, data_hora, lado) VALUES
(1001, NOW() - INTERVAL '5 days', 'Frente'),
(1001, NOW() - INTERVAL '5 days', 'Verso'),
(1001, NOW() - INTERVAL '4 days', 'Frente'),
(1001, NOW() - INTERVAL '4 days', 'Frente'),
(1001, NOW() - INTERVAL '3 days', 'Verso'),
(1001, NOW() - INTERVAL '3 days', 'Verso'),
(1001, NOW() - INTERVAL '2 days', 'Frente'),
(1001, NOW() - INTERVAL '2 days', 'Verso'),
(1001, NOW() - INTERVAL '2 days', 'Frente'),
(1001, NOW() - INTERVAL '1 day', 'Frente'),
(1001, NOW() - INTERVAL '1 day', 'Frente'),
(1001, NOW() - INTERVAL '1 day', 'Verso'),
(1001, NOW(), 'Frente'),
(1001, NOW(), 'Verso'),
(1001, NOW(), 'Frente'),
(1002, NOW() - INTERVAL '2 days', 'Frente'),
(1002, NOW() - INTERVAL '1 day', 'Verso'),
(1002, NOW(), 'Frente');
