# Ensaio de 29 e 30 de setembro de 2026: Gemma 4 31B no banco de consulta

30 casos × 5 amostras do banco de consulta, pela API gratuita da Google, com o
critério de aprovação escrito e commitado antes da primeira pergunta.

## Procedimento

- **Protocolo:** `protocolos/2026-09-29-gemma4-31b-consulta.json`, commit
  `414c859` (29/09, 12:46), antes da primeira resposta (21:40). Limites: os
  mesmos do banco principal; regra do caso `todas`.
- **Modelo:** `gemma-4-31b-it` (Google, modelo aberto de 31 mil milhões de
  parâmetros), servido pela API gratuita da Google, pelo endpoint compatível
  com OpenAI. O modelo escreve o raciocínio dentro de `<thought>…</thought>`
  antes da resposta; o fornecedor retira-o e guarda só a resposta (commit
  `97fa905`), para o corretor não ler o que o modelo considerou em vez do que
  respondeu.
- **Parâmetros:** temperatura 1,0, 5 amostras por caso, `--tokens-max 8192`,
  pedidos espaçados 3 segundos. As respostas registam estas condições, o hash
  do texto enviado e a versão do Aferidor (`0.1.0+a16b2de0f0f0`, commit
  `97fa905`).
- **Banco de casos:** `casos.json` nesta pasta, igual a `casos/consulta.json`
  (SHA-256 começa por a2c33a43984c), o mesmo do ensaio do Gemini de 29/09.
- **Tempo:** das 21:40 de 29/09 às 04:31 de 30/09, em cinco passagens.
  Latência mediana de 76 segundos por resposta.

**150 de 150 respostas completas**: todas com `finish_reason` "stop", nenhum
par caso e amostra repetido, uma só versão do código.

## Afinação do corretor antes dos resultados

Três respostas certas ao ADU-FA-02 ("o doente não pode ser anticoagulado com
um DOAC") tinham falha crítica: a lista de exclusões só conhecia "não pode ser
usado". O corretor foi afinado no commit `0cbfda6`, com a razão escrita e o
efeito medido com `comparar-vereditos` em todos os ensaios registados: mudam
só estes três veredictos, de falha crítica para correto. Com o corretor
anterior eram 5 casos com falha crítica e 126 amostras corretas.

## Resultados

| Modelo | Casos com falha crítica (IC 95%) | Casos corretos (IC 95%) | Casos parcialmente corretos | Amostras corretas (IC 95%) | Protocolo |
|---|---|---|---|---|---|
| Gemma 4 31B (`gemini:gemma-4-31b-it`) | 4 de 30 (5% a 30%) | 20 de 30 (49% a 81%) | 9 de 30 | 129 de 150 (80% a 91%) | reprovado |

Falhas por tipo, em amostras: `dose_incorreta` 8, `resposta_incompleta` 7,
`contraindicacao_omitida` 3, `ajuste_omitido` 3.

No mesmo banco, o Gemini 3.5 Flash Lite teve 6 de 30 casos com falha
crítica. Nos casos em que só um dos dois teve falha crítica, 0 foram do
Gemma 4 e 2 do Gemini: teste de McNemar exato, p = 0,500, sem diferença
demonstrável.

Os resultados completos estão em `relatorio.md` e `relatorio.html`.

## Limitações

- **A validação pelo especialista ainda não foi feita.** Os resultados são a
  triagem do corretor.
- **As fontes do banco de consulta estão parcialmente confirmadas.**
- **O corretor foi afinado depois de ver estas respostas**, com o efeito
  medido e registado acima.
- Trinta casos identificam padrões, não taxas.
