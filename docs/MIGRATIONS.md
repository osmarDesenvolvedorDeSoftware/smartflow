# MIGRATIONS.md

## Como aplicar a migration manualmente

Execute no banco de dados PostgreSQL conectado ao schema correto:

```
ALTER TABLE placas ADD COLUMN IF NOT EXISTS nome_exibicao VARCHAR(120);
ALTER TABLE placas ADD COLUMN IF NOT EXISTS tipo_dispositivo VARCHAR(30);
ALTER TABLE placas ADD COLUMN IF NOT EXISTS local_uso VARCHAR(120);
ALTER TABLE placas ADD COLUMN IF NOT EXISTS loja_unidade VARCHAR(120);
ALTER TABLE placas ADD COLUMN IF NOT EXISTS responsavel VARCHAR(120);
ALTER TABLE placas ADD COLUMN IF NOT EXISTS observacao VARCHAR(500);
```

Esses comandos são idempotentes e podem ser executados em produção sem risco de erro se a coluna já existir.

## Checklist de teste manual

1. Rode a migration acima no banco de dados.
2. Logue como SuperAdmin.
3. Cadastre comerciante com ID físico 1001.
4. Confirme que o SuperAdmin não exige nome/local/unidade/responsável.
5. Logue como comerciante.
6. Veja o dispositivo como `Dispositivo #1001`.
7. Edite:
   - Nome: Placa Caixa 1 - Loja Centro
   - Tipo: display
   - Local: Caixa 1
   - Unidade: Loja Centro
   - Responsável: Equipe Caixa
   - Observação: Display principal do caixa
8. Salve.
9. Recarregue o painel.
10. Confirme persistência.
11. Teste /r/1001/frente.
12. Teste /r/1001/verso.
13. Confirme registro de cliques.
14. Suspenda dispositivo pelo SuperAdmin.
15. Confirme tela de suspensão.
16. Reative.
17. Confirme funcionamento normal.
