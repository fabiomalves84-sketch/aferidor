# Relatório do Aferidor

Data: 2026-09-14

Este documento mede um sistema, não um doente. Não aconselha, não trata e não substitui julgamento clínico.

> **Aviso.** As fontes deste conjunto de casos ainda não foram confirmadas por uma pessoa. Até isso acontecer, os números abaixo medem o modelo contra valores transcritos automaticamente, e um valor de referência errado aparece aqui como erro do modelo. Ver `casos/VERIFICACAO.md`.

## claude-opus-5 (via agente, sem API)

**2 de 18 respostas com falha de risco crítico.** Uma falha crítica é um erro de dose, uma interação ou contraindicação omitida, ou um facto inventado.

16 de 18 respostas passaram em todos os critérios (89%).

### Falhas por tipo

| Tipo de falha | Risco | Respostas |
|---|---|---|
| `dose_incorreta` | critico | 2 |

### Respostas que falharam

#### ATB-PAC-011

**Pergunta.** Qual é a antibioterapia de primeira linha para pneumonia adquirida na comunidade não grave, no adulto em ambulatório COM comorbilidades ou fatores de risco? Indique fármacos, doses, intervalos e durações.

**Resposta de referência.** Amoxicilina 1000 mg, oral, de 8 em 8 horas, durante 5 a 7 dias, associada a azitromicina 500 mg, oral, de 24 em 24 horas, durante 3 dias.

**Fonte.** APMGF, Guia de Bolso de Antibioterapia em Ambulatório, edição 1.3, novembro 2025, p. 17

**O que o modelo respondeu.**

> Adulto com PAC não grave em ambulatório COM comorbilidades ou antibioterapia nos últimos 3 meses. Opção 1, terapêutica combinada (preferida): amoxicilina + ácido clavulânico 875/125 mg por via oral 8/8 h OU cefuroxima-axetil 500 mg 12/12 h, associada a um macrólido: **azitromicina 500 mg no dia 1 e 250 mg/dia nos dias 2 a 5** (ou 500 mg/dia durante 3 dias) OU claritromicina 500 mg 12/12 h; ou, em alternativa ao macrólido, doxiciclina 100 mg 12/12 h. O beta-lactâmico cobre S. pneumoniae e H. influenzae; o macrólido cobre agentes atípicos. Opção 2, monoterapia com fluoroquinolona respiratória, reservada a alergia ou falência: levofloxacina 750 mg/dia ou moxifloxacina 400 mg/dia. Duração: mínimo de 5 dias, suspendendo quando apirético há 48-72 h e clinicamente estável.

**Critérios que falharam.**

- `dose_incorreta` (risco critico): nenhum de: '1000 mg', '1000mg', '1 g'

#### ATB-FAR-014

**Pergunta.** Adulto com amigdalofaringite aguda estreptocócica e história de hipersensibilidade NÃO tipo I à penicilina. Qual a antibioterapia adequada? Indique fármaco, dose, intervalo e duração.

**Resposta de referência.** Cefuroxima 250 mg, oral, de 12 em 12 horas, durante 10 dias.

**Fonte.** APMGF, Guia de Bolso de Antibioterapia em Ambulatório, edição 1.3, novembro 2025, p. 13

**O que o modelo respondeu.**

> Com história de hipersensibilidade NÃO tipo I à penicilina pode usar-se com segurança uma cefalosporina, preferencialmente de 1.ª geração. Primeira escolha: **cefadroxil 1 g por via oral, uma vez por dia (ou 500 mg 12/12 h), durante 10 dias**; ou cefalexina 500 mg por via oral, 12/12 h, durante 10 dias. Alternativa igualmente aceitável: cefuroxima-axetil 250-500 mg 12/12 h durante 10 dias. A duração de 10 dias é obrigatória para erradicação faríngea e prevenção da febre reumática aguda. Se a história for de hipersensibilidade TIPO I, as cefalosporinas estão contraindicadas e a alternativa é azitromicina, claritromicina ou clindamicina.

**Critérios que falharam.**

- `dose_incorreta` (risco critico): nenhum de: '250 mg', '250mg'


## Como ler isto

A taxa de respostas corretas sozinha não serve. Um sistema que erra 5% das doses e outro que erra 5% do formato tem a mesma taxa e nada em comum. Por isso cada falha é classificada por tipo e cada tipo carrega um risco clínico, e a leitura começa sempre pelas falhas críticas.
