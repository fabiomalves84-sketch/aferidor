# Aferidor, em cinco minutos

Documento de apresentação do projeto. Para leitura por quem não vai abrir o
código.

## A pergunta que está por trás

Um assistente de inteligência artificial que responde a um médico sobre dose,
interação ou contraindicação está a participar numa decisão terapêutica. A
pergunta que importa sobre esse assistente não é se escreve bem. É com que
frequência está certo, em que erra quando erra, e quanto custa cada tipo de
erro.

Um sistema que acerta 92% das perguntas parece bom. Se os 8% que falha forem
todos doses pediátricas, não é bom, é perigoso. A média esconde exatamente
aquilo que precisa de ser visto.

## O que este projeto é

Um instrumento de medida. Guarda perguntas clínicas cuja resposta correta é
conhecida e citável, envia-as a um modelo de linguagem, classifica cada
resposta contra critérios escritos de antemão, e categoriza cada falha por tipo
e por risco clínico.

O resultado é um documento que diz, antes de qualquer percentagem, quantas
respostas continham uma falha de risco crítico, e mostra cada uma delas com a
pergunta, a resposta de referência, a fonte e o texto que o modelo escreveu.

## O que este projeto não é

**Não é um dispositivo médico.** Não aconselha, não trata, não substitui
julgamento clínico. Mede um sistema, não um doente.

**Não contém dados de doentes.** Todos os casos vêm de documentos públicos
portugueses ou são sintéticos. Nenhum registo clínico real entra aqui.

**Não avalia nenhum produto comercial.** Os casos são genéricos.

## Estado honesto, hoje

- 18 casos clínicos, cada um com fonte pública identificada até à página, vários
  deles em pares que medem uma distinção que um modelo pode não fazer: pneumonia
  com e sem comorbilidades, exacerbação de DPOC ligeira e grave, faringite com
  hipersensibilidade tipo I e não tipo I
- Executor com adaptadores para OpenAI e Anthropic, e um fornecedor falso
- Correção determinista por critérios, com taxonomia de oito tipos de falha, e
  pelo menos um caso a medir cada um deles
- Relatório legível, com as falhas críticas antes da percentagem
- 138 testes automáticos, todos a passar
- Sem dependências externas, só biblioteca padrão do Python

E o que falta, dito com a mesma clareza:

- **As dezoito fontes ainda não foram confirmadas por uma pessoa.** Foram lidas por
  ferramenta automática, e uma ferramenta automática transcreve mal um número.
  Até essa confirmação, qualquer resultado mede o modelo contra valores não
  verificados. A tabela de confirmação está em `casos/VERIFICACAO.md`.
- **Só houve uma execução real, e limitada.** Dezoito perguntas a um modelo, sem
  API, sem controlo de temperatura e com uma amostra por pergunta. Deu 16 em 18 e
  apanhou uma referência desatualizada no banco. Está registada em
  `ensaios/2026-09-14-agente/`, com os limites escritos. Ainda não houve uma
  execução pela API com repetição.
- **A distinção entre receitar um fármaco e o nomear para o excluir é feita por
  heurística, não por compreensão de texto.** Erra nas duas direções, e o README
  diz como e porquê, em Limites conhecidos.

Estas três linhas estão aqui de propósito. Um instrumento de medida que esconde
os seus próprios limites não serve como instrumento de medida.

## O que demonstra sobre método

A ISO/IEC 42001 exige que um sistema de gestão de IA demonstre avaliação de
desempenho documentada e tratamento dos riscos identificados. A ISO 13485 e o
Regulamento de Dispositivos Médicos exigem verificação e validação com
critérios de aceitação definidos **antes** do ensaio.

Este projeto produz, à escala de uma demonstração, o tipo de evidência que
essas normas pedem:

| Exigência | Onde está |
|---|---|
| Critérios de aceitação definidos antes do ensaio | `casos/casos.json`, escritos antes de qualquer execução |
| Rastreabilidade à fonte | cada caso guarda documento e página |
| Verificação dos dados de origem | `casos/VERIFICACAO.md` e o comando `verificar` |
| Classificação de falhas por risco | `aferidor/risk.py` |
| Registo íntegro dos resultados | `data/respostas.jsonl`, escrito à medida que chega |
| Relatório para revisão humana | `relatorios/relatorio.md` |

O comando `verificar` merece nota. Avalia a resposta de referência de cada caso
contra os critérios desse mesmo caso. Quando foi escrito, apanhou logo dois
casos partidos em dez, ambos na direção que mais custa: dariam como errado um
modelo que tinha acertado. Um banco de ensaio precisa de ser ensaiado a si
próprio.

## Como ver em cinco minutos

```
python -m unittest discover -s tests   # 138 testes
python -m aferidor verificar           # 18/18 casos coerentes
python -m aferidor executar --fornecedor falso
python -m aferidor relatorio           # escreve relatorios/relatorio.md
```

Nada disto precisa de chave de API nem de ligação à internet.

Para ler o código, por ordem: `risk.py`, `models.py`, `checks.py`. São os três
que carregam as decisões. `docs/ARQUITETURA.md` explica as fronteiras entre
módulos e a razão de cada uma.
