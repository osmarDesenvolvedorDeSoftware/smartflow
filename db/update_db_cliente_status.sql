-- Adiciona o flag ativo na tabela de usuarios para inativar o acesso ao painel de um comerciante
-- (apenas o login é bloqueado; as placas continuam redirecionando normalmente)
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS ativo BOOLEAN NOT NULL DEFAULT TRUE;