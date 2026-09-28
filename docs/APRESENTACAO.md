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
(normas portuguesas e diretrizes internacionais) ou são sintéticos. Nenhum registo clínico real entra aqui.

**Não avalia nenhum produto comercial.** Os casos são genéricos.

## Estado honesto, hoje

- **Dois bancos de casos, 57 ao todo**, cada um com fonte pública identificada:
  27 de antibioterapia, interações, gravidez e ajuste de dose, e 30 de consulta
  de adulto, criança e cessação tabágica. Muitos em pares que medem uma
  distinção que um modelo pode não fazer (pneumonia com e sem comorbilidades,
  hipersensibilidade tipo I e não tipo I, um só critério de ajuste de
  apixabano contra dois). Os casos de infeção seguem as normas da DGS; onde duas
  fontes reconhecidas divergem de forma defensável, o caso aceita as duas.
- **Um corretor que se ensaia a si próprio nos dois sentidos.** A resposta de
  referência de cada caso tem de passar, e uma resposta errada construída para
  cada critério tem de falhar: 206 e 83 destes controlos, todos apanhados.
- **Rastreabilidade.** Cada resposta guarda o texto exato enviado (por hash), a
  temperatura, o limite de tokens e a versão do código; uma retoma recusa
  misturar condições; o relatório diz o que mediu, com que banco e quando.
- **Critério de aprovação escrito antes**, num protocolo, e um relatório que
  diz aprovado ou reprovado e avisa quando o protocolo foi escrito depois.
- **Uma folha cega para um clínico julgar o corretor**, e a medida da
  concordância entre os dois, com as passagens falsas primeiro.
- Intervalos de confiança nos números principais, e um indicador de português
  europeu à parte das falhas clínicas.
- Adaptadores para OpenAI, Anthropic e modelos locais pelo Ollama.
- 389 testes automáticos, todos a passar, sem dependências externas.

E o que falta, dito com a mesma clareza:

- **O corretor ainda não foi comparado com um clínico.** A ferramenta existe
  (`revisao` e `concordancia`); falta alguém julgar a folha. Até lá, não se sabe
  com que frequência o corretor deixa passar uma resposta errada.
- **As fontes estão confirmadas a meio.** 10 casos foram confirmados nos PDF da
  DGS, um a um; 24 foram declarados confirmados por grupo; dos 23 restantes,
  16 foram lidos no documento original por ferramenta e batem, e 7 (ESC e ADA)
  esperam leitura humana. `casos/VERIFICACAO.md` diz qual é qual.
- **Ainda não houve um ensaio pela API.** Houve uma execução limitada com um
  modelo por uma sessão de assistente (18 perguntas) e uma comparação de dois
  modelos locais de 8 mil milhões de parâmetros, com 5 amostras por caso. Os
  casos mudaram depois dessa comparação, e os números dela não servem para
  comparar com um ensaio novo.
- **A correção é textual.** Numa só revisão apareceram oito erros do corretor,
  todos corrigidos e fixados em testes; cada ensaio real vai trazer mais. A
  distinção entre receitar um fármaco e o nomear para o excluir é heurística, e
  `docs/METODO.md` diz onde erra.

Estas linhas estão aqui de propósito. Um instrumento de medida que esconde os
seus próprios limites não serve como instrumento de medida.

## O que demonstra sobre método

A ISO/IEC 42001 exige que um sistema de gestão de IA demonstre avaliação de
desempenho documentada e tratamento dos riscos identificados. A ISO 13485 e o
Regulamento de Dispositivos Médicos exigem verificação e validação com
critérios de aceitação definidos **antes** do ensaio.

Este projeto produz, à escala de uma demonstração, o tipo de evidência que
essas normas pedem:

| Exigência | Onde está |
|---|---|
| Critérios de aceitação definidos antes do ensaio | os critérios de cada caso, escritos antes da primeira execução e alterados depois só com a razão no commit; o protocolo de aprovação do sistema (`aferidor protocolo`) |
| Rastreabilidade à fonte | cada caso guarda documento e página |
| Verificação dos dados de origem | `casos/VERIFICACAO.md` e o comando `verificar` |
| Classificação de falhas por risco | `aferidor/risk.py` |
| Registo íntegro dos resultados | `data/respostas.jsonl`, escrito à medida que chega |
| Relatório para revisão humana | `relatorios/relatorio.md` e `.html`, com as condições do ensaio e intervalos de confiança |
| Validação do método de medida | `aferidor revisao` e `concordancia`: o corretor contra um clínico, às cegas |

O comando `verificar` merece nota. Avalia a resposta de referência de cada caso
contra os critérios desse mesmo caso. Quando foi escrito, apanhou logo dois
casos partidos em dez, ambos na direção que mais custa: dariam como errado um
modelo que tinha acertado. Um banco de ensaio precisa de ser ensaiado a si
próprio.

Desde setembro de 2026 ensaia-se também no sentido contrário. Para cada
critério, o `verificar` estraga a resposta de referência exatamente no que o
critério vê e exige que ele a apanhe. Da primeira vez que correu, dez destas
respostas erradas passaram: um fármaco proibido, receitado na frase a seguir a
uma contraindicação, era dado como excluído. Foi corrigido no corretor, não nos
casos.

## Como ver em cinco minutos

```
python -m unittest discover -s tests   # 389 testes
python -m aferidor verificar           # 27/27 casos, 206/206 controlos negativos
python -m aferidor verificar --casos casos/consulta.json   # 30/30, 83/83
python -m aferidor executar --fornecedor falso
python -m aferidor relatorio           # escreve relatorios/relatorio.md
```

Nada disto precisa de chave de API nem de ligação à internet.

Para ler o código, por ordem: `risk.py`, `models.py`, `checks.py`. São os três
que carregam as decisões. `docs/ARQUITETURA.md` explica as fronteiras entre
módulos e a razão de cada uma.
