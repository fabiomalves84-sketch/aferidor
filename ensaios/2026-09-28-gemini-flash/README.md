# Ensaio de 28 de setembro de 2026: Gemini 3.5 Flash Lite pela API

27 casos × 5 amostras de um modelo comercial da Google, pela API gratuita, com
o critério de aprovação escrito e commitado antes da primeira pergunta. É o
primeiro ensaio registado com um modelo comercial.

## Procedimento

- **Protocolo:** `protocolos/2026-09-28-gemini-flash.json`, commitado antes de
  qualquer resposta. Os limites são os do ensaio de 27/09: nenhum caso com falha
  crítica, nenhum caso parcialmente correto, pelo menos 95% de amostras
  corretas; regra do caso `todas`.
- **Alterações ao protocolo antes da primeira resposta.** O modelo previsto foi
  mudado duas vezes, cada uma num commit próprio e sempre antes de haver
  respostas: o Gemini 2.5 Flash já não está disponível para contas novas
  (commit `91acccf`), e os modelos Flash só permitem 20 pedidos por dia no nível
  gratuito, insuficientes para 135 (commit `924e5be`). Banco, amostras,
  temperatura e limites nunca mudaram.
- **Modelo:** `gemini-3.5-flash-lite`, pelo endpoint compatível com OpenAI da
  Google, nível gratuito (500 pedidos por dia, 15 por minuto).
- **Parâmetros:** temperatura 1,0, 5 amostras por caso, `--tokens-max 8192`,
  pedidos espaçados 5 segundos. Todas as 135 respostas registam estas condições,
  o hash do texto enviado e a versão do Aferidor (`0.1.0+cca8c7859a97`,
  correspondente ao commit `3bf8b0d`).
- **Banco de casos:** `casos.json` nesta pasta, igual a `casos/casos.json` e ao
  banco do ensaio de 27/09 (SHA-256 começa por 51b4d389f2f6).
- **Tempo:** das 18:26 às 20:57, com a latência mediana de 14 segundos por
  resposta; o nível gratuito respondeu com sobrecarga (503) durante boa parte da
  tarde, e a execução esperou e retomou sem repetir respostas.

**135 de 135 respostas completas**: todas com `finish_reason` "stop", nenhuma
vazia, nenhum par caso e amostra repetido, uma só versão do código.

## Respostas descartadas

`descartadas-versao-anterior.jsonl` guarda 111 respostas que não entram nos
resultados. Foram obtidas por um processo da versão anterior do código
(`0.1.0+e8ef5ac09c76`, antes das correções do corretor do commit `3bf8b0d`)
que continuou a correr quando a espera foi interrompida, em paralelo com o
processo da versão atual, e escreveu no mesmo ficheiro. As respostas foram
separadas pela versão registada em cada uma; as desta versão não tinham
repetidos entre si e a execução foi retomada só para os pares em falta. O
script de espera passou a terminar o processo filho e a recusar arrancar com
outro em curso. Duas respostas anteriores da mesma versão antiga, postas de
parte às 18:10, foram guardadas numa pasta temporária que já não existe.

## Resultados

| Modelo | Casos com falha crítica (IC 95%) | Casos corretos (IC 95%) | Casos parcialmente corretos | Amostras corretas (IC 95%) | Protocolo |
|---|---|---|---|---|---|
| Gemini 3.5 Flash Lite (`gemini:gemini-3.5-flash-lite`) | 11 de 27 (25% a 59%) | 10 de 27 (22% a 56%) | 12 de 27 | 84 de 135 (54% a 70%) | reprovado |

Falhas por tipo, em amostras: `dose_incorreta` 28, `resposta_incompleta` 20,
`contraindicacao_omitida` 6, `interacao_omitida` 5, `ajuste_omitido` 2.

Português europeu (indicador independente): nenhuma resposta com formas do
Brasil; 8 com grafia anterior ao Acordo Ortográfico.

Com o mesmo banco, as mesmas amostras e a mesma temperatura, o ensaio de 27/09
registou 17 de 27 casos com falha crítica no Gemma 3 12B e 22 de 27 no Phi-4
14B. A versão do corretor é diferente (as correções do commit `3bf8b0d` são
posteriores a esse ensaio), pelo que a comparação é indicativa.

Os resultados completos, por área clínica e caso a caso, estão em
`relatorio.md` e `relatorio.html`.

## Limitações

- **A validação pelo especialista ainda não foi feita.** Os resultados são a
  triagem do corretor; uma amostra das respostas deve ser julgada às cegas
  (`aferidor revisao`).
- **As fontes estão parcialmente confirmadas** (ver `casos/VERIFICACAO.md`).
- **Um modelo Lite**, o disponível no nível gratuito em volume suficiente; os
  resultados não descrevem os modelos Flash ou Pro da mesma família.
- Vinte e sete casos identificam padrões, não taxas; os intervalos acima
  indicam a incerteza.
