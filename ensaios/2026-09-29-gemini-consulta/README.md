# Ensaio de 29 de setembro de 2026: Gemini 3.5 Flash Lite no banco de consulta

30 casos × 5 amostras do banco de consulta (adulto, criança e cessação
tabágica), pela API gratuita da Google, com o critério de aprovação escrito e
commitado antes da primeira pergunta. É o primeiro ensaio deste banco contra
qualquer modelo.

## Procedimento

- **Protocolo:** `protocolos/2026-09-29-gemini-consulta.json`, commit `afbd43f`
  (11:06), antes da primeira resposta (11:07). Limites: nenhum caso com falha
  crítica, nenhum caso parcialmente correto, pelo menos 95% de amostras
  corretas; regra do caso `todas`.
- **Modelo:** `gemini-3.5-flash-lite`, nível gratuito, as mesmas condições do
  ensaio de 28/09 no banco principal.
- **Parâmetros:** temperatura 1,0, 5 amostras por caso, `--tokens-max 8192`,
  pedidos espaçados 5 segundos. As 150 respostas registam estas condições, o
  hash do texto enviado e a versão do Aferidor (`0.1.0+0bc1742fa9fc`, commit
  `c903c34`).
- **Banco de casos:** `casos.json` nesta pasta, igual a `casos/consulta.json`
  no momento do ensaio (SHA-256 começa por a2c33a43984c), com os critérios
  revistos em `0124ce6`.
- **Tempo:** das 11:07 às 11:20, latência mediana de 5 segundos.

**150 de 150 respostas completas**: todas com `finish_reason` "stop", nenhuma
vazia, nenhum par caso e amostra repetido, uma só versão do código.

## Correção do corretor antes dos resultados

A primeira correção destas respostas deu falha crítica a respostas certas. Uma
a uma, eram todas do corretor: o `nao_prescreve` não reconhecia a exclusão em
frases como "Os DOAC (…lista…) estão contraindicados", "nunca deve administrar
aspirina" ou uma segunda menção que explicava a exclusão. O corretor foi
afinado no commit `3fc49ba`, com a razão de cada regra, com testes nos dois
sentidos e sem perder nenhum controlo negativo; os resultados abaixo são com o
corretor afinado. Com o anterior, eram 7 casos com falha crítica e 108 amostras
corretas.

## Resultados

| Modelo | Casos com falha crítica (IC 95%) | Casos corretos (IC 95%) | Casos parcialmente corretos | Amostras corretas (IC 95%) | Protocolo |
|---|---|---|---|---|---|
| Gemini 3.5 Flash Lite (`gemini:gemini-3.5-flash-lite`) | 6 de 30 (10% a 37%) | 18 de 30 (42% a 75%) | 10 de 30 | 122 de 150 (74% a 87%) | reprovado |

Casos com falha crítica: ADU-HTA-02, PED-02, PED-03, PED-04, TAB-04, TAB-08.
Destes, PED-04 e TAB-04 têm cada um uma amostra que o corretor dá como
prescrição e que é, lida, uma exclusão mal reconhecida (descrita nos limites do
METODO).

Falhas por tipo, em amostras: `dose_incorreta` 6, `contraindicacao_omitida` 4,
`ajuste_omitido` 4, `resposta_incompleta` 15.

Português europeu (indicador independente): 5 de 150 respostas com formas do
Brasil e 2 com grafia anterior ao Acordo Ortográfico.

Os resultados completos estão em `relatorio.md` e `relatorio.html`.

## Limitações

- **A validação pelo especialista ainda não foi feita.** Os resultados são a
  triagem do corretor.
- **As fontes do banco de consulta estão parcialmente confirmadas** (ver
  `casos/VERIFICACAO.md`).
- **O corretor foi afinado depois de ver estas respostas.** Cada regra corrige
  uma forma de excluir o fármaco que o corretor não reconhecia, está justificada
  no commit e foi testada contra as inversões perigosas; mesmo assim, é uma
  alteração feita com os dados à vista, e fica registada como tal.
- Trinta casos identificam padrões, não taxas.
