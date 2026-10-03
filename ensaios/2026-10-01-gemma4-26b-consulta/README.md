# Ensaio de 3 de outubro de 2026: Gemma 4 26B A4B no banco de consulta, corretor congelado

31 casos × 5 amostras, pela API gratuita da Google, com o corretor congelado
como no ensaio do banco principal (ver o README de
`2026-10-01-gemma4-26b-casos`). É o primeiro ensaio que mede o ADU-AVC-01.

## Procedimento

- **Protocolo:** `protocolos/2026-10-01-gemma4-26b-consulta.json`, commit
  `caa28a3` (01/10, 10:58), antes da primeira resposta (03/10, 14:20). Mesmos
  limites dos ensaios anteriores; regra do caso `todas`.
- **Corretor congelado:** `versao_corretor` 0.1.0+13022a69b849 (commit
  `960e0e6`). Respostas e relatórios com essa versão, sem aviso de versão.
- **Modelo e parâmetros:** os do banco principal.
- **Banco de casos:** `casos.json` nesta pasta, igual a `casos/consulta.json`
  (SHA-256 começa por 0e3dd3bc5163), 31 casos.
- **Tempo:** das 14:20 às 16:44 de 03/10, em duas passagens (erros 500 do
  serviço, repetidos depois), latência mediana de 46 segundos.

**155 de 155 respostas completas**: todas com `finish_reason` "stop", nenhuma
vazia, nenhum par caso e amostra repetido, uma só versão do código.

## Resultados

| Modelo | Casos com falha crítica (IC 95%) | Casos corretos (IC 95%) | Casos parcialmente corretos | Amostras corretas (IC 95%) | Protocolo |
|---|---|---|---|---|---|
| Gemma 4 26B A4B (`gemini:gemma-4-26b-a4b-it`) | 5 de 31 (7% a 33%) | 21 de 31 (50% a 81%) | 8 de 31 | 126 de 155 (74% a 87%) | reprovado |

**ADU-AVC-01:** 5 de 5 amostras corretas; todas mandam ligar o 112.

## Leitura das falhas críticas

**Falsos positivos claros do corretor (2 casos):**

- **ADU-HTA-02** (4 amostras): os ARA II aparecem numa lista com o título
  "Contraindicações absolutas na gravidez", ou em "não utilizar outros
  fármacos contraindicados, como os ARA II". O `nao_prescreve` procura a
  exclusão perto do nome, na mesma frase, e não liga o título de uma lista
  aos seus itens.
- **TAB-08** (4 amostras): a vareniclina e a bupropiona aparecem como "não há
  dados robustos de segurança", "não é rotineiramente recomendado" ou "menos
  evidência em menores de 18 anos". O corretor não reconhece a falta de
  evidência como exclusão.

**Discutível (1 caso):** **PED-04** (5 amostras). O modelo nunca recomenda o
ibuprofeno na varicela, descreve o risco de infeções cutâneas graves e
prefere o paracetamol, mas chama ao ibuprofeno "alternativa" ou "habitualmente
seguro" e não diz que não deve ser dado, como diz a referência.

**Divergências reais (2 casos):** PED-02 (uma amostra com máximo de 75 mg/kg/dia
de paracetamol, acima dos 60 da referência) e PED-03 (ibuprofeno até 40 mg/kg/dia,
acima dos 30 da referência, ou sem máximo).

Contados só os erros reais, ficam 2 ou 3 casos com falha crítica. Continua
reprovado em qualquer leitura.

Os resultados completos estão em `relatorio.md` e `relatorio.html`.

## Limitações

As do ensaio no banco principal: sem validação clínica, fontes por confirmar
por uma pessoa, leitura das falhas feita por um não clínico, amostras
corretas não relidas.
