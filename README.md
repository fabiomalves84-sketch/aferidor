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

- [x] **Fase 1** Modelo de caso, critérios de aceitação e armazenamento
- [x] **Fase 2** Conjunto inicial de casos com fontes verificadas
- [x] **Fase 3** Executor: envia ao modelo, recolhe, guarda
- [x] **Fase 4** Classificadores e taxonomia de falhas
- [x] **Fase 5** Relatório e métricas por categoria de risco
- [x] **Fase 6** Documentação e apresentação

## Como correr

Sem dependências externas. Python 3.10 ou superior, biblioteca padrão apenas.

```
python -m unittest discover -s tests             # testes
python -m aferidor verificar                     # os casos passam nos proprios criterios?
python -m aferidor executar --fornecedor falso   # ensaio a seco, sem chave nem custo
python -m aferidor executar --fornecedor openai --modelo gpt-4o
python -m aferidor classificar                   # avalia as respostas guardadas
python -m aferidor relatorio                     # escreve relatorios/relatorio.md
```

As chaves vêm do ambiente, `OPENAI_API_KEY` e `ANTHROPIC_API_KEY`, e nunca do
repositório. As respostas são escritas em `data/respostas.jsonl`, uma por
linha, à medida que chegam: uma execução interrompida retoma onde ficou em vez
de voltar a pagar as perguntas já feitas. `--recomecar` força tudo de novo.

O prompt enviado ao modelo leva a pergunta e mais nada. A resposta de
referência, os critérios de aceitação e a fonte ficam deste lado da parede. Um
banco que mostra ao modelo o que conta como certo não está a medir o modelo.

## Correção

A correção é textual e determinista. Um banco de ensaio cujo corretor é ele
próprio um modelo de linguagem tem dois sistemas em avaliação e nenhuma forma
de saber qual deles errou. O preço é que cada critério tem de ser escrito com
cuidado, e esse preço paga-se uma vez, quando o caso é escrito.

Dois cuidados no confronto de texto: acentos e espaçamento são normalizados,
para `1000mg` valer o mesmo que `1000 mg`; e um termo que é só um número tem de
aparecer isolado, senão o termo `5` seria encontrado dentro de `500 mg` e uma
dose errada passaria por uma duração certa.

`python -m aferidor verificar` avalia a resposta de referência de cada caso
contra os critérios desse mesmo caso. Um caso cuja própria referência não passa
está errado, e está errado na direção que mais custa: dá como errado um modelo
que acertou. A verificação corre também na bateria de testes.

## Relatório

`python -m aferidor relatorio` escreve um documento em Markdown para quem não lê
código. A ordem do documento é uma decisão, não um acaso: o número de falhas
críticas vem primeiro e a percentagem de respostas certas vem depois, porque uma
percentagem sozinha é exatamente o número que esconde o que importa.

Cada resposta errada aparece com a pergunta, a resposta de referência, a fonte,
o que o modelo respondeu e o critério que falhou. Quem discordar de um veredito
tem de conseguir ver o que o corretor viu e contestá-lo.

Casos que ficaram sem resposta são nomeados e não entram em nenhuma contagem.
Enquanto as fontes não forem confirmadas por uma pessoa, o relatório diz isso
em aviso no topo.

## Limites conhecidos

O critério `nao_prescreve` distingue receitar um fármaco de o nomear para o
excluir, e fá-lo com uma heurística: procura uma expressão de exclusão explícita
a uma distância curta do nome do fármaco. Erra nas duas direções. Dá por excluído
um fármaco quando a expressão de exclusão ali perto pertence a outro, e dá por
receitado um fármaco quando a exclusão está escrita de uma forma que a lista não
contém. É melhor do que tratar toda a menção como prescrição, que era o
comportamento anterior e que marcava como errada uma resposta certa por ela
acrescentar um aviso. Não é compreensão de texto e não se apresenta como tal.

Nenhuma das catorze fontes foi ainda confirmada por uma pessoa. Até isso acontecer,
qualquer resultado deste banco mede o modelo contra valores transcritos por uma
ferramenta automática. Ver `casos/VERIFICACAO.md`.

## Documentos

- `docs/APRESENTACAO.md` o projeto em cinco minutos, para quem não abre o código
- `docs/ARQUITETURA.md` os módulos, as fronteiras entre eles e a razão de cada uma
- `casos/VERIFICACAO.md` a tabela de confirmação humana das fontes

## Estado

Roteiro concluído. 14 casos com fonte, executor com dois adaptadores reais e
um fornecedor falso, correção determinista por critérios com contagem separada
por tipo de falha e por risco, relatório legível e documentação. 108 testes,
todos a passar. Sem dependências externas.

Por fazer, e é o que falta para os números valerem alguma coisa: confirmar as
dez fontes com os olhos numa pessoa (`casos/VERIFICACAO.md`) e correr contra um
modelo real.
