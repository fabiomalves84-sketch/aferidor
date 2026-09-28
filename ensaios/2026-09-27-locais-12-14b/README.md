# Ensaio de 27 e 28 de setembro de 2026: modelos locais de 12 e 14 mil milhões de parâmetros

27 casos × 5 amostras × 2 modelos, pelo Ollama, na mesma máquina, com o
critério de aprovação escrito e commitado antes da primeira pergunta.

## Como foi feito

- **Protocolo:** `protocolos/2026-09-27-locais-12-14b.json`, commit `b71d72b`,
  feito antes de o ensaio começar. Limites: nenhum caso com falha crítica,
  nenhum caso instável, pelo menos 95% de amostras certas.
- **Hardware:** MacBook Air, chip Apple M5, 16 GB de memória. **Ollama** 0.34.0.
- **Modelos:** `gemma3:12b` (Google, id `f4031aab637d`, 8,1 GB) e `phi4:14b`
  (Microsoft, id `ac896e5b8b34`, 9,1 GB), escolhidos por caberem em 16 GB e não
  raciocinarem em voz alta antes de responder.
- **Parâmetros:** temperatura 1,0, 5 amostras por caso, `--tokens-max 4096`.
  Todas as 270 respostas registam estas condições, o hash do texto enviado e a
  versão do Aferidor (`0.1.0+c6a6b3a93b8b`).
- **Banco de casos:** `casos.json` nesta pasta, igual a `casos/casos.json` no
  momento do ensaio (SHA-256 começa por 51b4d389f2f6), já com as fontes da DGS
  de 27/09.
- **Instrução enviada:** a versão com acentos, de 27/09.
- **Tempo:** Gemma 3 12B das 23:51 às 03:21 (3h30); Phi-4 14B das 03:22 às
  06:07 (2h45). Antes de cada modelo, uma pergunta de teste; as duas passaram.
  O Mac ficou impedido de adormecer com `caffeinate`.

**270 de 270 respostas completas**: todas com `finish_reason` "stop", nenhuma
vazia, nenhum caso sem resposta, nenhuma amostra em falta.

## O que saiu, sem interpretar

| Modelo | Casos com falha crítica (IC 95%) | Casos instáveis | Amostras certas (IC 95%) | Protocolo |
|---|---|---|---|---|
| Gemma 3 12B (`local:gemma3:12b`) | 17 de 27 (44% a 78%) | 16 de 27 | 47 de 135 (27% a 43%) | reprovado |
| Phi-4 14B (`local:phi4:14b`) | 22 de 27 (63% a 92%) | 12 de 27 | 36 de 135 (20% a 35%) | reprovado |

Os intervalos de confiança dos casos com falha crítica sobrepõem-se.

Falhas por tipo, em amostras:
- Gemma 3 12B: `dose_incorreta` 42, `resposta_incompleta` 52, `ajuste_omitido`
  21, `contraindicacao_omitida` 11, `interacao_omitida` 6, `alucinacao` 3,
  `recusa_indevida` 3.
- Phi-4 14B: `dose_incorreta` 50, `resposta_incompleta` 50, `ajuste_omitido`
  28, `contraindicacao_omitida` 11, `interacao_omitida` 7, `alucinacao` 4,
  `formato_invalido` 1, `recusa_indevida` 1.

Português europeu (indicador à parte): Gemma 3 12B com 3 de 135 respostas com
formas do Brasil e 19 com grafia anterior ao Acordo; Phi-4 14B com 19 e 49.

Os números completos, por área clínica e caso a caso, estão em `relatorio.md`
e `relatorio.html`.

## Limites que se aplicam a estes números

- **O corretor ainda não foi comparado com um clínico.** Todos os ensaios reais
  anteriores revelaram erros do corretor que davam como errado um modelo que
  acertou, ou o contrário. Antes de tirar conclusões destes números, uma
  amostra das respostas deve ser julgada às cegas (`aferidor revisao`).
- **As fontes estão confirmadas a meio** (ver `casos/VERIFICACAO.md`).
- **Não se comparam com o ensaio de 16/09**: a instrução, parte dos casos e o
  corretor mudaram entre os dois.
- Vinte e sete casos medem padrões, não taxas: os intervalos acima dizem quão
  largas são as incertezas.
