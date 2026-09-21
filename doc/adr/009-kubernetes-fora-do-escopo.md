# ADR-009: Kubernetes fora do escopo

## Status
Aceito

## Decisão
Kubernetes não será provisionado no desafio. A imagem atende aos requisitos de migração separada, probes, usuário não-root, filesystem somente leitura e desligamento gracioso para permitir evolução futura.

## Gatilho de revisão
Adotar Kubernetes somente quando houver necessidade medida de scheduling, rollout canário ou escala que justifique EKS e sua operação.
