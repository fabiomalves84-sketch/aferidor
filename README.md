# Aferidor

Banco de ensaio para respostas clínicas de modelos de linguagem em português
europeu. Mede, não aconselha.

## O problema

Um assistente clínico que responde a um médico sobre dose, interação ou
contraindicação está a participar numa decisão terapêutica. A pergunta que
importa não é se a resposta parece bem escrita. É com que frequência está
certa, em que é que erra quando erra, e quanto custa cada tipo de erro.

Um modelo que acerta em 92% das perguntas parece bom. Se os 8% que falha forem
todos doses pediátricas, não é bom, é perigoso. A média esconde exatamente
aquilo que precisa de ser visto.

Isto não se resolve lendo respostas à mão. Resolve-se com um conjunto de casos
de referência, critérios de aceitação explícitos e medição repetível.

## O que o Aferidor faz

1. Guarda um conjunto de casos clínicos de referência, cada um com a resposta
   correta e a fonte pública que a sustenta
2. Envia cada pergunta ao modelo em avaliação e recolhe a resposta
3. Classifica a resposta contra critérios de aceitação declarados
4. Categoriza cada falha por tipo e por risco clínico
5. Produz um relatório legível por quem não escreve código

## O que o Aferidor não é

**Não é um dispositivo médico.** Não aconselha ninguém, não trata ninguém e não
substitui julgamento clínico. É um instrumento de medida sobre um sistema, não
sobre um doente.

**Não contém dados de doentes.** Todos os casos são construídos a partir de
fontes públicas ou são sintéticos. Nenhum registo clínico real entra aqui.

**Não avalia nenhum produto comercial.** Os casos são genéricos. Se alguém o
apontar a um produto seu, é decisão sua e responsabilidade sua.

## Taxonomia de falhas

A pontuação global sozinha não serve. Cada resposta errada é classificada:

| Tipo | O que significa | Risco |
|---|---|---|
| `dose_incorreta` | Valor, unidade ou intervalo errados | Crítico |
| `interacao_omitida` | Não assinalou uma interação relevante | Crítico |
| `contraindicacao_omitida` | Não assinalou uma contraindicação | Crítico |
| `alucinacao` | Afirmou facto inexistente ou fonte inventada | Crítico |
| `ajuste_omitido` | Faltou ajuste renal, hepático ou pediátrico | Alto |
| `resposta_incompleta` | Certa mas insuficiente para decidir | Médio |
| `recusa_indevida` | Recusou uma pergunta legítima | Baixo |
| `formato_invalido` | Não respeitou o formato pedido | Baixo |

Um sistema com 5% de `dose_incorreta` e um com 5% de `formato_invalido` têm a
mesma exatidão e não têm nada a ver um com o outro.

## Fontes dos casos

Só fontes públicas e citáveis, com a referência guardada em cada caso:

- Resumos das Características do Medicamento e folhetos informativos do Infarmed
- Normas e orientações da Direção-Geral da Saúde
- Bases públicas de interações medicamentosas

Um caso sem fonte não entra. Uma referência que eu não consiga apontar é uma
referência que inventei.

## Enquadramento normativo

A ISO/IEC 42001:2023 exige que um sistema de gestão de IA demonstre avaliação
de desempenho documentada e tratamento de riscos identificados. A ISO 13485 e o
Regulamento de Dispositivos Médicos exigem verificação e validação com
critérios de aceitação definidos antes do ensaio, não depois.

Este projeto produz o tipo de evidência que essas normas pedem, à escala de uma
demonstração.

## Roteiro

- [ ] **Fase 1** Modelo de caso, critérios de aceitação e armazenamento
- [ ] **Fase 2** Conjunto inicial de casos com fontes verificadas
- [ ] **Fase 3** Executor: envia ao modelo, recolhe, guarda
- [ ] **Fase 4** Classificadores e taxonomia de falhas
- [ ] **Fase 5** Relatório e métricas por categoria de risco
- [ ] **Fase 6** Documentação e apresentação

## Estado

Fase 1 em curso.
