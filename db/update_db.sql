-- Script para adicionar colunas do Pix à tabela 'placas' sem apagar dados existentes
ALTER TABLE placas ADD COLUMN IF NOT EXISTS pix_chave VARCHAR(100);
ALTER TABLE placas ADD COLUMN IF NOT EXISTS pix_tipo_valor VARCHAR(10);

-- Remove a restrição caso ela já exista para evitar erros e a recria de forma segura
ALTER TABLE placas DROP CONSTRAINT IF EXISTS chk_pix_tipo_valor;
ALTER TABLE placas ADD CONSTRAINT chk_pix_tipo_valor CHECK (pix_tipo_valor IN ('fixo', 'aberto'));

ALTER TABLE placas ADD COLUMN IF NOT EXISTS pix_valor_fixo NUMERIC(10, 2);
