# Uso de IA

## Princípios

- Nenhum segredo, CPF real, token ou dado de saúde real é enviado a ferramentas de IA.
- A pessoa responsável pelo repositório revisa toda sugestão antes de incorporá-la.
- A decisão final precisa ser explicável sem depender da ferramenta.

## Verificação

Toda alteração deve passar por:

```bash
make pre-push
```

O pipeline também executa Ruff, import-linter, testes PostgreSQL, cobertura, pip-audit, build e Trivy conforme o ambiente do PR.

## Registro

Uso relevante de IA e correções de propostas ficam registrados em `doc/DIARIO.md`. Dados externos sobre AWS, Asaas e segurança devem ser confirmados na documentação oficial.
