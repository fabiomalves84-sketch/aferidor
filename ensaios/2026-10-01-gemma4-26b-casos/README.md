# Ensaio de 1 a 3 de outubro de 2026: Gemma 4 26B A4B no banco principal, corretor congelado

27 casos × 5 amostras, pela API gratuita da Google. É o primeiro ensaio com o
corretor congelado: o protocolo fixou a versão do código antes da primeira
pergunta, e o resultado é publicado tal como saiu, falsos positivos incluídos.

## Procedimento

- **Protocolo:** `protocolos/2026-10-01-gemma4-26b-casos.json`, commit
  `caa28a3` (01/10, 10:58), antes da primeira resposta (11:22). Limites:
  nenhum caso com falha crítica, nenhum caso parcialmente correto, pelo menos
  95% de amostras corretas; regra do caso `todas`.
- **Corretor congelado:** `versao_corretor` 0.1.0+13022a69b849, a do commit
  `960e0e6`. As 135 respostas foram obtidas com essa versão, e os relatórios
  foram escritos com ela; o relatório não tem nenhum aviso de versão. O
  corretor não foi alterado durante nem depois do ensaio.
- **Modelo:** `gemma-4-26b-a4b-it` (Google, modelo aberto com 26 mil milhões de
  parâmetros, dos quais cerca de 4 ativos por token), pela API gratuita, pelo
  endpoint compatível com OpenAI.
- **Parâmetros:** temperatura 1,0, 5 amostras por caso, `--tokens-max 8192`,
  pedidos espaçados 3 segundos.
- **Banco de casos:** `casos.json` nesta pasta, igual a `casos/casos.json`
  (SHA-256 começa por 89ac69b77168).
- **Tempo:** de 01/10 às 11:22 a 03/10 às 14:20, em cinco passagens, latência
  mediana de 45 segundos. O serviço Gemma da Google esteve em erro interno
  (500) durante longos períodos: 182 pedidos falharam nos dois bancos e foram
  repetidos mais tarde. Um pedido ficou preso numa ligação aberta das 20:10 de
  01/10 às 09:30 de 02/10, provavelmente com o computador em repouso; o
  processo foi terminado à mão e a execução retomou sem repetir respostas.
  Nenhum código foi alterado nessa intervenção.

**135 de 135 respostas completas**: todas com `finish_reason` "stop", nenhuma
vazia, nenhum par caso e amostra repetido, uma só versão do código.

## Resultados

| Modelo | Casos com falha crítica (IC 95%) | Casos corretos (IC 95%) | Casos parcialmente corretos | Amostras corretas (IC 95%) | Protocolo |
|---|---|---|---|---|---|
| Gemma 4 26B A4B (`gemini:gemma-4-26b-a4b-it`) | 12 de 27 (28% a 63%) | 11 de 27 (25% a 59%) | 9 de 27 | 79 de 135 (50% a 66%) | reprovado |

Comparação emparelhada com o Gemma 4 31B (ensaio de 29/09, corrigido com o
banco atual, 9 casos com falha crítica): só o 26B falhou em 3 casos, só o 31B
em nenhum; McNemar exato p = 0,250, a diferença pode dever-se ao acaso.

Falhas por tipo, em amostras: `dose_incorreta` 34, `contraindicacao_omitida`
5, `interacao_omitida` 3, `ajuste_omitido` 15, `resposta_incompleta` 16.

## Leitura das falhas críticas

Todas as amostras com falha crítica foram lidas. A leitura não muda os
números acima; serve para saber quanto deles é do modelo e quanto é do
corretor, e fica para a validação clínica decidir os casos discutíveis.

**Falsos positivos claros do corretor (2 casos):**

- **GRA-IECA-023** (2 amostras): o modelo escreve "o ramipril deve ser
  suspenso imediatamente". O critério procura "suspender", "suspensão" e
  formas próximas, mas não o particípio "suspenso".
- **INT-COL-016** (2 amostras): "deve ser evitada" falha um critério que tem
  "evitar" mas não "evitada"; na outra amostra, a claritromicina aparece numa
  condição ("se for absolutamente inevitável… suspensão temporária da
  colquicina"), que o `nao_prescreve` lê como prescrição.

**Discutíveis (3 casos), para o clínico decidir:**

- **PED-OMA-021**: duas amostras são falsos positivos (a amoxicilina aparece
  em "histórico de anafilaxia à amoxicilina", fora de uma recusa, onde o
  corretor não aplica os marcadores de antecedentes). A terceira dá
  azitromicina "3 a 5 dias", e o critério exige "3 dias".
- **GRA-VPA-024** (1 amostra): descreve contraceção eficaz, teste de gravidez
  e plano de gestão de risco, sem usar a expressão "programa de prevenção da
  gravidez".
- **INT-CLA-015** (1 amostra): "não é recomendado manter a sinvastatina" e
  "suspender", sem dizer que a associação está contraindicada, que é o que o
  RCM diz.

**Divergências reais da referência (7 casos):** o modelo responde com outro
esquema ou outra dose. Alguns desses esquemas existem noutras diretrizes, mas
não são o que a fonte portuguesa citada indica:

- ATB-PAC-011 e ATB-DPOC-012: amoxicilina com ácido clavulânico 875/125 mg de
  12 em 12 horas, em vez do esquema de 8 em 8 horas da referência.
- FMT-CIST-017: nitrofurantoína de 12 em 12 horas (a norma da DGS diz 6/6h;
  decisão de 30/09).
- PED-OMA-019 e PED-OMA-020: durações de 7 a 10 dias, ou "5 a 7 dias", onde a
  norma dá 5 dias (≥ 2 anos) ou 7 dias (< 2 anos).
- ATB-PAC-001: amoxicilina 1 g, que é a dose do guia da APMGF mas não a da
  norma da DGS que o caso cita (500 mg). As duas fontes divergem, como
  `casos/VERIFICACAO.md` regista.
- ATB-FAR-014: cefalexina 500 mg de 6/6h em vez de cefuroxima.

Contados só os erros reais, o modelo fica entre 7 e 10 casos com falha
crítica, conforme a decisão sobre os discutíveis. Continua reprovado em
qualquer leitura. As amostras corretas não foram relidas: um falso negativo
do corretor não aparece nesta leitura.

Os resultados completos estão em `relatorio.md` e `relatorio.html`.

## Limitações

- **A validação pelo especialista ainda não foi feita.** Os resultados são a
  triagem do corretor, e a leitura acima é de um não clínico.
- **As fontes estão lidas, mas não confirmadas por uma pessoa** (ver
  `casos/VERIFICACAO.md`).
- Vinte e sete casos identificam padrões, não taxas.
