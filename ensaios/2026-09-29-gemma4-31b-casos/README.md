# Ensaio de 29 de setembro de 2026: Gemma 4 31B no banco principal

27 casos × 5 amostras de um modelo aberto grande, pela API gratuita da
Google, com o critério de aprovação escrito e commitado antes da primeira
pergunta.

## Procedimento

- **Protocolo:** `protocolos/2026-09-29-gemma4-31b-casos.json`, commit
  `414c859` (12:46), antes da primeira resposta (12:54). Limites: nenhum caso
  com falha crítica, nenhum caso parcialmente correto, pelo menos 95% de
  amostras corretas; regra do caso `todas`.
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
- **Banco de casos:** `casos.json` nesta pasta, igual a `casos/casos.json`
  (SHA-256 começa por 4f7581c3d72d). **Correção:** a mensagem do commit
  `414c859` diz, por engano, que o banco é o mesmo dos ensaios de 27 e 28/09
  (51b4d389f2f6). Não é: entre esses ensaios e este, três critérios foram
  revistos (commit `0124ce6`, INT-CLA-015, FMT-CIST-017 e GRA-VPA-024). As
  perguntas são as mesmas, pelo que as respostas dos ensaios anteriores se
  podem corrigir com este banco para comparação; o protocolo regista o SHA-256
  correto.
- **Tempo:** das 12:54 às 21:37, em quatro passagens; o serviço respondeu com
  erro interno (500) durante parte da tarde e a execução retomou sem repetir
  respostas. Latência mediana de 76 segundos por resposta.

**135 de 135 respostas completas**: todas com `finish_reason` "stop", nenhum
par caso e amostra repetido, uma só versão do código.

## Resultados

| Modelo | Casos com falha crítica (IC 95%) | Casos corretos (IC 95%) | Casos parcialmente corretos | Amostras corretas (IC 95%) | Protocolo |
|---|---|---|---|---|---|
| Gemma 4 31B (`gemini:gemma-4-31b-it`) | 10 de 27 (22% a 56%) | 14 de 27 (34% a 69%) | 6 de 27 | 84 de 135 (54% a 70%) | reprovado |

Falhas por tipo, em amostras: `dose_incorreta` 31, `resposta_incompleta` 26,
`contraindicacao_omitida` 5, `ajuste_omitido` 4, `interacao_omitida` 3.

Com o mesmo banco e as respostas dos ensaios anteriores corrigidas com ele: o
Gemini 3.5 Flash Lite tem 11 de 27 casos com falha crítica, o Gemma 3 12B 17
e o Phi-4 14B 22. Contra o Gemini, o teste de McNemar exato sobre os casos
discordantes dá 2 contra 3, p = 1,000; contra o Gemma 3 12B, 2 contra 9,
p = 0,065.

**A confirmar pelo Fábio:** no DOS-MTX-027 (metotrexato), quatro amostras dão
a posologia semanal correta (7,5 a 15 mg, uma vez por semana) mas não indicam
a dose máxima de 20 mg, e o critério classifica essa omissão como
`dose_incorreta`, de risco crítico. Se omitir a dose máxima deve ser
`resposta_incompleta` é uma decisão clínica sobre a taxonomia, não uma
correção do corretor.

Os resultados completos estão em `relatorio.md` e `relatorio.html`.

## Limitações

- **A validação pelo especialista ainda não foi feita.** Os resultados são a
  triagem do corretor.
- **As fontes estão parcialmente confirmadas** (ver `casos/VERIFICACAO.md`).
- Vinte e sete casos identificam padrões, não taxas.
