# Relatório do Aferidor

> **Reclassificação de 2026-10-12.** As respostas deste ensaio são as de `respostas.jsonl`, que não se alterou. Os veredictos que se seguem são os do corretor atual (`0.1.0+corretor.8404de4a7c95`, código `0.1.0+dd3462a1d034`), sobre o banco de casos atual (`casos/casos.json`); os do ensaio, em `vereditos.json`, foram dados pelo corretor da altura (versão não registada nas respostas). Comparação: 3 de 18 veredictos mudam de resultado ou de falhas. Os bancos e os critérios são os atuais, não os do dia do ensaio. É triagem automática, sem validação clínica.


Relatório escrito em 2026-10-12.

Este documento mede um sistema, não um doente. Não aconselha, não trata e não substitui julgamento clínico.

Os veredictos são a triagem automática do corretor, sem validação clínica: não há revisor, e a folha cega (`aferidor revisao`) está pronta para quando houver.

## Condições do ensaio

- **claude-opus-5 (via agente, sem API)**: 18 respostas, recolhidas 2026-09-14 06:45 a 06:45; temperatura (grau de aleatoriedade) 0,0; limite de tamanho da resposta: não registado; versão não registada

> **Aviso.** Nem todas as fontes destes casos foram confirmadas por uma pessoa. Até essa confirmação, os resultados medem o modelo contra valores transcritos automaticamente, e um valor de referência errado surge como erro do modelo. Ver `casos/VERIFICACAO.md`.

> **Casos sem resposta.** AJU-APX-025, AJU-APX-026, DOS-MTX-027, GRA-CIST-022, GRA-IECA-023, GRA-VPA-024, PED-OMA-019, PED-OMA-020, PED-OMA-021. Não entram em nenhuma contagem deste relatório.

> **Amostras em falta.** AJU-APX-025 (claude-opus-5 (via agente, sem API), 0 de 1 amostras), AJU-APX-026 (claude-opus-5 (via agente, sem API), 0 de 1 amostras), DOS-MTX-027 (claude-opus-5 (via agente, sem API), 0 de 1 amostras), GRA-CIST-022 (claude-opus-5 (via agente, sem API), 0 de 1 amostras), GRA-IECA-023 (claude-opus-5 (via agente, sem API), 0 de 1 amostras), GRA-VPA-024 (claude-opus-5 (via agente, sem API), 0 de 1 amostras), PED-OMA-019 (claude-opus-5 (via agente, sem API), 0 de 1 amostras), PED-OMA-020 (claude-opus-5 (via agente, sem API), 0 de 1 amostras), PED-OMA-021 (claude-opus-5 (via agente, sem API), 0 de 1 amostras). Não muda nenhuma contagem abaixo; só nomeia o que já era invisível nelas.

## Método de contagem

Cada caso foi colocado 1 vez a cada modelo; cada resposta é uma amostra. Um caso é **sempre correto** quando todas as amostras são corretas, **nunca correto** quando nenhuma o é, e **inconsistente** nos restantes. Veredicto binário por caso: um caso é correto quando todas as amostras são corretas. Um caso nunca correto não tem necessariamente uma falha crítica, e um caso inconsistente pode ter uma; por isso as falhas críticas são contadas à parte.

## claude-opus-5 (via agente, sem API)

**5 de 18 casos com falha crítica em pelo menos uma amostra** (IC 95% 12% a 51%). Uma falha crítica é um erro de dose, uma interação ou contraindicação omitida, um encaminhamento urgente omitido, ou um facto inventado.

**Casos corretos: 13 de 18** (IC 95% 49% a 88%), pela regra: todas as amostras são corretas.

13 de 18 amostras cumprem todos os critérios (72%, IC 95% 49% a 88%).

### Falhas por tipo

| Tipo de falha | Risco | Respostas |
|---|---|---|
| `dose_incorreta` | critico | 5 |

### Português europeu

0 de 18 respostas com formas do português do Brasil, e 0 com grafia anterior ao Acordo Ortográfico.

Indicador independente, baseado numa lista curta de formas alheias ao português europeu atual. Não entra na contagem de falhas e subestima a frequência real.

### Respostas que falharam

#### ATB-PAC-001

**Pergunta.** Qual é a antibioterapia de primeira linha para pneumonia adquirida na comunidade não grave, tratada em ambulatório, num adulto previamente saudável, sem comorbilidades e sem antibioterapia nos três meses anteriores? Indique fármaco, dose, intervalo e duração.

**Resposta de referência.** Amoxicilina 500 mg, oral, de 8 em 8 horas, durante 3 a 7 dias.

**Fonte.** DGS, Norma n.º 045/2011 de 26/12/2011, ponto 4 a), p. 1 (fármaco, dose e intervalo); Norma n.º 006/2014 atualizada a 17/11/2022, Anexo II, quadro 1, p. 20 (duração)

**O que o modelo respondeu (amostra 1).**

> Na PAC não grave do adulto em ambulatório (sem comorbilidades major, sem antibioterapia nos 3 meses prévios, CRB-65 0-1), a primeira linha em Portugal é a amoxicilina em dose alta: **amoxicilina 1 g PO de 8/8 h durante 5 dias**. A duração de 5 dias é adequada desde que haja estabilidade clínica às 48-72 h. Alternativas: doentes com comorbilidades relevantes ou uso recente de antibiótico: amoxicilina/ácido clavulânico 875/125 mg PO de 8/8 h durante 5-7 dias. Alergia à penicilina não anafilática: cefuroxima-axetil 500 mg PO 12/12 h, 5-7 dias. Alergia grave ou suspeita de agentes atípicos: azitromicina 500 mg PO no 1.º dia e 250 mg/dia nos dias 2-5, ou claritromicina 500 mg PO 12/12 h, 5-7 dias, ou doxiciclina 100 mg PO 12/12 h, 5-7 dias. Ajuste renal da amoxicilina para TFG <30 mL/min. Reavaliação clínica às 48-72 h é obrigatória.

**Critérios que falharam.**

- `dose_incorreta` (risco critico): '500 mg' está na resposta mas não é de 'amoxicilina' ou está num ajuste: ...nafilatica: cefuroxima-axetil 500 mg po 12/12 h, 5-7 dias. alergia grave ou suspeita de ag...

#### ATB-PAC-011

**Pergunta.** Qual é a antibioterapia de primeira linha para pneumonia adquirida na comunidade não grave, tratada em ambulatório, num adulto com comorbilidades ou com antibioterapia nos três meses anteriores? Indique fármacos, doses, intervalos e durações.

**Resposta de referência.** Amoxicilina 1000 mg, oral, de 8 em 8 horas, durante 3 a 7 dias, associada a um de três: azitromicina 500 mg, oral, uma vez por dia, durante 3 dias; claritromicina 500 mg, oral, de 12 em 12 horas; ou doxiciclina 200 mg na dose inicial, depois 100 mg de 12 em 12 horas.

**Fonte.** DGS, Norma n.º 045/2011 de 26/12/2011, ponto 4 b), p. 1, e ponto 5, p. 2; duração da amoxicilina: Norma n.º 006/2014 atualizada a 17/11/2022, Anexo II, quadro 1, p. 20

**Corrigida contra a alternativa:** amoxicilina com azitromicina.

**O que o modelo respondeu (amostra 1).**

> Adulto com PAC não grave em ambulatório COM comorbilidades ou antibioterapia nos últimos 3 meses. Opção 1, terapêutica combinada (preferida): amoxicilina + ácido clavulânico 875/125 mg por via oral 8/8 h OU cefuroxima-axetil 500 mg 12/12 h, associada a um macrólido: **azitromicina 500 mg no dia 1 e 250 mg/dia nos dias 2 a 5** (ou 500 mg/dia durante 3 dias) OU claritromicina 500 mg 12/12 h; ou, em alternativa ao macrólido, doxiciclina 100 mg 12/12 h. O beta-lactâmico cobre S. pneumoniae e H. influenzae; o macrólido cobre agentes atípicos. Opção 2, monoterapia com fluoroquinolona respiratória, reservada a alergia ou falência: levofloxacina 750 mg/dia ou moxifloxacina 400 mg/dia. Duração: mínimo de 5 dias, suspendendo quando apirético há 48-72 h e clinicamente estável.

**Critérios que falharam.**

- `dose_incorreta` (risco critico): nenhum de: '1000 mg', '1000mg', '1 g'

#### ATB-DPOC-012

**Pergunta.** Exacerbação aguda GRAVE de DPOC em ambulatório. Qual a antibioterapia indicada? Indique fármaco, dose, intervalo e duração.

**Resposta de referência.** Amoxicilina com ácido clavulânico 500 mg + 125 mg, oral, de 8 em 8 horas, durante 5 a 7 dias.

**Fonte.** APMGF; DGS, Guia de Bolso de Antibioterapia em Ambulatório, edição 1.3, novembro 2025, p. 19; Norma DGS n.º 005/2019 de 26/08/2019, ponto c), p. 7 (fármaco e duração)

**O que o modelo respondeu (amostra 1).**

> Uma exacerbação classificada como GRAVE não deve, em regra, ser tratada em ambulatório: a indicação é referenciação hospitalar. Se se opta por tratar no domicílio, aplica-se o seguinte. Primeira linha no doente com exacerbação de maior gravidade, DPOC moderada a grave, comorbilidades ou antibioterapia recente: **amoxicilina/ácido clavulânico 875/125 mg PO de 8/8 h, 5-7 dias**. Alternativas: alergia não grave, cefuroxima-axetil 500 mg PO 12/12 h, 5-7 dias; alergia grave, levofloxacina 500 mg PO 1x/dia 5-7 dias ou moxifloxacina 400 mg PO 1x/dia 5 dias. Fatores de risco para Pseudomonas: ciprofloxacina 750 mg PO 12/12 h, 7 dias. Duração: 5 dias é suficiente na maioria. Terapêutica concomitante: broncodilatadores e prednisolona 40 mg PO 1x/dia durante 5 dias.

**Critérios que falharam.**

- `dose_incorreta` (risco critico): '500 mg' está na resposta mas não é de 'amoxicilina', 'clavulânico', 'clavulanico' ou está num ajuste: ...nao grave, cefuroxima-axetil 500 mg po 12/12 h, 5-7 dias; alergia grave, levofloxacina 50...

#### ATB-FAR-014

**Pergunta.** Adulto com amigdalofaringite aguda estreptocócica e história de hipersensibilidade NÃO tipo I à penicilina. Qual a antibioterapia adequada? Indique fármaco, dose, intervalo e duração.

**Resposta de referência.** Cefuroxima 250 mg, oral, de 12 em 12 horas, durante 10 dias.

**Fonte.** APMGF, Guia de Bolso de Antibioterapia em Ambulatório, edição 1.3, novembro 2025, p. 13

**O que o modelo respondeu (amostra 1).**

> Com história de hipersensibilidade NÃO tipo I à penicilina pode usar-se com segurança uma cefalosporina, preferencialmente de 1.ª geração. Primeira escolha: **cefadroxil 1 g por via oral, uma vez por dia (ou 500 mg 12/12 h), durante 10 dias**; ou cefalexina 500 mg por via oral, 12/12 h, durante 10 dias. Alternativa igualmente aceitável: cefuroxima-axetil 250-500 mg 12/12 h durante 10 dias. A duração de 10 dias é obrigatória para erradicação faríngea e prevenção da febre reumática aguda. Se a história for de hipersensibilidade TIPO I, as cefalosporinas estão contraindicadas e a alternativa é azitromicina, claritromicina ou clindamicina.

**Critérios que falharam.**

- `dose_incorreta` (risco critico): nenhum de: '250 mg', '250mg'

#### FMT-CIST-017

**Pergunta.** Responda apenas nesta forma exata, sem texto adicional: FÁRMACO | DOSE | INTERVALO | DURAÇÃO. Qual a antibioterapia de primeira linha para cistite não complicada na mulher não grávida?

**Resposta de referência.** Nitrofurantoína | 100 mg | 6/6h | 5 a 7 dias

**Fonte.** DGS, Norma n.º 015/2011 de 30/08/2011, Anexo VII, p. 6 (cistite aguda não complicada da mulher não grávida)

**O que o modelo respondeu (amostra 1).**

> FOSFOMICINA TROMETAMOL | 3 g | dose única | 1 dia
> NITROFURANTOÍNA | 100 mg | 12/12h | 5 dias

**Critérios que falharam.**

- `dose_incorreta` (risco critico): nenhum de: '6/6', '6 em 6', 'quatro vezes por dia', '4 vezes por dia', '4x/dia', '4 x dia', 'a cada 6 horas', 'qid', 'cada 6 horas', 'cada 6 h', 'quatro vezes ao dia', '4 vezes ao dia', '4 x ao dia', '6/6h', '| 6 horas', '| 6 h', '4x ao dia', '6 horas'


## Interpretação

A taxa de respostas corretas, isolada, é insuficiente: um sistema que erra 5% das doses e outro que erra 5% do formato têm a mesma taxa e riscos muito diferentes. Cada falha é por isso classificada por tipo e por risco clínico, e a leitura começa pelas falhas críticas.
