# ADR-004: Rollback

## Status
Aceito

## Contexto
Uma versão pode falhar depois do deploy por erro de aplicação, migração incompatível ou falha de dependência externa.

## Decisão
O rollback de aplicação usa a imagem anterior e valida `/health/live`. Em produção AWS, o pipeline cria snapshot do RDS antes da troca e o rollback manual exige aprovação no environment. Migrações seguem expand/contract para manter compatibilidade entre versões N e N-1.

## Consequências
Rollback de código não desfaz migrações destrutivas. Mensagens da outbox/inbox devem permanecer legíveis por ambas as versões.
