# Relatório do Aferidor

> **Reclassificação de 2026-10-13.** As respostas deste ensaio são as de `respostas.jsonl`, que não se alterou. Os veredictos que se seguem são os do corretor atual (`0.1.0+corretor.be194b638f32`, código `0.1.0+ee4ed520aee1`), sobre o banco de casos atual (`casos/casos.json`); os do ensaio, em `vereditos.json`, foram dados pelo corretor da altura (código 0.1.0+a16b2de0f0f0). Comparação: 26 de 135 veredictos mudam de resultado ou de falhas. Os bancos e os critérios são os atuais, não os do dia do ensaio. É triagem automática, sem validação clínica.


Relatório escrito em 2026-10-13.

Este documento mede um sistema, não um doente. Não aconselha, não trata e não substitui julgamento clínico.

Os veredictos são a triagem automática do corretor, sem validação clínica: não há revisor, e a folha cega (`aferidor revisao`) está pronta para quando houver.

## Condições do ensaio

- **gemini:gemma-4-31b-it**: 135 respostas, recolhidas 2026-09-29 12:54 a 21:37; temperatura (grau de aleatoriedade) 1,0; limite de tamanho da resposta: 8192 tokens; versão 0.1.0+a16b2de0f0f0

> **Aviso.** Nem todas as fontes destes casos foram confirmadas por uma pessoa. Até essa confirmação, os resultados medem o modelo contra valores transcritos automaticamente, e um valor de referência errado surge como erro do modelo. Ver `casos/VERIFICACAO.md`.

## Método de contagem

Cada caso foi colocado 5 vezes a cada modelo; cada resposta é uma amostra. Um caso é **sempre correto** quando todas as amostras são corretas, **nunca correto** quando nenhuma o é, e **inconsistente** nos restantes. Veredicto binário por caso: um caso é correto quando todas as amostras são corretas. Um caso nunca correto não tem necessariamente uma falha crítica, e um caso inconsistente pode ter uma; por isso as falhas críticas são contadas à parte.

## gemini:gemma-4-31b-it

**10 de 27 casos com falha crítica em pelo menos uma amostra** (IC 95% 22% a 56%). Uma falha crítica é um erro de dose, uma interação ou contraindicação omitida, um encaminhamento urgente omitido, ou um facto inventado.

**Casos corretos: 14 de 27** (IC 95% 34% a 69%), pela regra: todas as amostras são corretas.

76 de 135 amostras cumprem todos os critérios (56%, IC 95% 48% a 64%).

4 de 27 casos inconsistentes: o resultado variou entre amostras.

### Falhas por tipo

| Tipo de falha | Risco | Respostas |
|---|---|---|
| `dose_incorreta` | critico | 44 |
| `interacao_omitida` | critico | 3 |
| `contraindicacao_omitida` | critico | 2 |
| `ajuste_omitido` | alto | 4 |
| `resposta_incompleta` | medio | 28 |

### Português europeu

5 de 135 respostas com formas do português do Brasil, e 2 com grafia anterior ao Acordo Ortográfico. Mais frequentes: ô antes de m ou n (PT: ó, como em crónico): 5; contracepção (PT: contraceção): 2.

Indicador independente, baseado numa lista curta de formas alheias ao português europeu atual. Não entra na contagem de falhas e subestima a frequência real.

### Respostas que falharam

#### ATB-PAC-001

**Pergunta.** Qual é a antibioterapia de primeira linha para pneumonia adquirida na comunidade não grave, tratada em ambulatório, num adulto previamente saudável, sem comorbilidades e sem antibioterapia nos três meses anteriores? Indique fármaco, dose, intervalo e duração.

**Resposta de referência.** Amoxicilina 500 mg, oral, de 8 em 8 horas, durante 3 a 7 dias.

**Fonte.** DGS, Norma n.º 045/2011 de 26/12/2011, ponto 4 a), p. 1 (fármaco, dose e intervalo); Norma n.º 006/2014 atualizada a 17/11/2022, Anexo II, quadro 1, p. 20 (duração)

**O que o modelo respondeu (amostra 4).**

> Para um adulto previamente saudável, sem comorbilidades e sem exposição a antibióticos nos últimos três meses, com pneumonia adquirida na comunidade (PAC) não grave para tratamento em ambulatório, a antibioterapia de primeira linha é a seguinte:
> 
> **Fármaco:** Amoxicilina
> **Dose:** 1 g
> **Intervalo:** De 8 em 8 horas
> **Duração:** 5 dias (podendo estender-se até 7 dias, dependendo da resposta clínica, mas a evidência atual suporta regimes curtos em casos não complicados).
> 
> ---
> 
> ### Interações, Contraindicações e Ajustes
> 
> **Contraindicações:**
> *   **Hipersensibilidade:** Contraindicado em doentes com historial de reações anafiláticas ou hipersensibilidade grave a penicilinas ou a outros beta-lactâmicos (ex: cefalosporinas, devido ao risco de reatividade cruzada).
> 
> **Interações:**
> *   **Alopurinol:** Pode aumentar a incidência de erupções cutâneas (rash).
> *   **Contracecionais Orais:** Existe a possibilidade teórica de redução da eficácia dos contracecionais orais, embora seja menos frequente com a amoxicilina do que com outros antibióticos. Recomenda-se cautela ou método adjuvante.
> 
> **Ajustes Relevantes:**
> *   **Insuficiência Renal:**
>     *   ClCr > 30 mL/min: Sem necessidade de ajuste.
>     *   ClCr 10-30 mL/min: Ajustar a dose para 500 mg a 888 mg de 12 em 12 horas.
>     *   ClCr < 10 mL/min: Ajustar a dose para 250 mg a 500 mg de 24 em 24 horas.
> 
> **Nota clínica:** Em regiões com elevada prevalência de *S. pneumoniae* resistente à penicilina ou se houver suspeita de agentes atípicos, as diretrizes podem sugerir a utilização de doxicliclina ou um macrólido (se a resistência local for <25%), mas a amoxicilina permanece a escolha preferencial para a cobertura do pneumococo em doentes saudáveis.

**Critérios que falharam.**

- `dose_incorreta` (risco critico): '500 mg' está na resposta mas não é de 'amoxicilina' ou está num ajuste: ...0 ml/min: ajustar a dose para 500 mg a 888 mg de 12 em 12 horas.     *   clcr < 10 ml/min:...

#### ATB-PIEL-006

**Pergunta.** Pielonefrite aguda em ambulatório no adulto. Qual o esquema de primeira linha?

**Resposta de referência.** Ceftriaxona 1000 mg IV ou IM em toma única, seguida de cefuroxima 500 mg, oral, de 12 em 12 horas, durante 7 dias.

**Fonte.** DGS, Norma n.º 015/2011 de 30/08/2011, Anexo VII, p. 6 (esquema); Norma n.º 006/2014 atualizada a 17/11/2022, Anexo II, quadro 1, p. 20 (duração de 7 dias)

**O que o modelo respondeu (amostra 1).**

> Esta resposta assume que estamos perante um quadro de **pielonefrite aguda não complicada no adulto**, apto para tratamento ambulatório (estável hemodinamicamente, sem falência renal aguda, sem sintomas de sépsis e com tolerância oral).
> 
> O esquema de primeira linha depende da prevalência local de resistência da *Escherichia coli* às fluoroquinolonas (se for $<10\%$, estas continuam a ser a primeira escolha).
> 
> ### 1. Primeira Linha (Preferencial)
> 
> **Ciprofloxacina**
> *   **Dose:** 500 mg
> *   **Intervalo:** de 12 em 12 horas
> *   **Duração:** 7 dias
> 
> *Alternativa (se preferir dose única diária):*
> **Levofloxacina**
> *   **Dose:** 750 mg
> *   **Intervalo:** de 24 em 24 horas
> *   **Duração:** 5 dias
> 
> ---
> 
> ### 2. Alternativas (em caso de resistência a quinolonas ou contraindicações)
> 
> Se a resistência local às quinolonas for elevada ($>10\%$), recomenda-se a administração de uma dose inicial de um cefalosporina de 3ª geração parenteral antes de iniciar a terapia oral:
> *   **Ceftriaxone:** 1g IM ou IV (dose única inicial).
> 
> **Seguida de terapia oral (ajustada ao antibiograma):**
> *   **Trimetoprima-Sulfametoxazol (TMP-SMX):** 160/800 mg de 12 em 12 horas durante 14 dias (apenas se a sensibilidade for confirmada).
> *   **Amoxicilina + Ácido Clavulânico:** 1g de 8 em 8 horas durante 10 a 14 dias.
> 
> ---
> 
> ### 3. Contraindicações, Interações e Ajustes
> 
> #### Fluoroquinolonas (Ciprofloxacina/Levofloxacina)
> *   **Contraindicações:** 
>     *   Hipersensibilidade a quinolonas.
>     *   Grávidas e lactantes.
>     *   Histórico de rotura de tendão associada ao uso de quinolonas.
> *   **Interações:** 
>     *   **Antiácidos, suplementos de Cálcio, Ferro, Magnésio ou Alumínio:** Reduzem significativamente a absorção (devem ser administrados com intervalo de $\ge 2$ horas).
>     *   **Varfarina:** Podem potenciar o efeito anticoagulante.
>     *   **Teofilina:** Aumento dos níveis plasmáticos de teofilina.
> *   **Ajustes:** 
>     *   **Renais:** Ajustar dose se $ClCr < 30\text{ ml/min}$ (especialmente para Levofloxacina e Ciprofloxacina).
> 
> #### Trimetoprima-Sulfametoxazol
> *   **Contraindicações:** 
>     *   Alergia a sulfonamidas.
>     *   Insuficiência hepática grave.
> *   **Interações:** 
>     *   **Metotrexato:** Aumenta a toxicidade do metotrexato.
>     *   **Varfarina:** Potencia o efeito anticoagulante.
> *   **Ajustes:** 
>     *   **Renais:** Redução da dose necessária se $ClCr < 30\text{ ml/min}$.
> 
> #### Amoxicilina + Ácido Clavulânico
> *   **Contraindicações:** 
>     *   Hipersensibilidade a penicilinas ou cefalosporinas (risumo de anafilaxia).
>     *   Histórico de icterícia colestática associada a este fármaco.
> *   **Ajustes:** 
>     *   **Renais:** Ajustar dose se $ClCr < 30\text{ ml/min}$.
> 
> ### Notas Adicionais
> 1.  **Urocultura:** Deve ser colhida **sempre** antes do início da antibioterapia.
> 2.  **Reavaliação:** O paciente deve ser reavaliado em 48-72 horas. Se não houver melhoria clínica, deve considerar-se a internamento para terapia IV e investigação de complicações (ex: abcesso renal).
> 3.  **Referências:** Baseado nas diretrizes gerais de infeção urinária (IDSA e consensos europeus de urologia/nefrologia). Não foram consultadas referências específicas de guidelines nacionais portuguesas atualizadas para este caso concreto, seguindo a prática clínica corrente.

**Critérios que falharam.**

- `resposta_incompleta` (risco medio): faltou: 'ceftriaxona', 'cefuroxima'
- `dose_incorreta` (risco critico): 'de 12 em 12 horas' está na resposta mas não é de 'cefuroxima' ou está num ajuste: ...:** 500 mg *   **intervalo:** de 12 em 12 horas *   **duracao:** 7 dias  *alternativa (se...

#### ATB-PAC-011

**Pergunta.** Qual é a antibioterapia de primeira linha para pneumonia adquirida na comunidade não grave, tratada em ambulatório, num adulto com comorbilidades ou com antibioterapia nos três meses anteriores? Indique fármacos, doses, intervalos e durações.

**Resposta de referência.** Amoxicilina 1000 mg, oral, de 8 em 8 horas, durante 3 a 7 dias, associada a um de três: azitromicina 500 mg, oral, uma vez por dia, durante 3 dias; claritromicina 500 mg, oral, de 12 em 12 horas; ou doxiciclina 200 mg na dose inicial, depois 100 mg de 12 em 12 horas.

**Fonte.** DGS, Norma n.º 045/2011 de 26/12/2011, ponto 4 b), p. 1, e ponto 5, p. 2; duração da amoxicilina: Norma n.º 006/2014 atualizada a 17/11/2022, Anexo II, quadro 1, p. 20

**Corrigida contra a alternativa:** amoxicilina com claritromicina.

**O que o modelo respondeu (amostra 1).**

> Para um adulto com pneumonia adquirida na comunidade (PAC) não grave, a ser tratada em regime ambulatório, mas que apresenta fatores de risco (comorbilidades como insuficiência cardíaca, DPOC, diabetes, doença renal ou hepática, alcoolismo, neoplasias, ou uso de antibióticos nos últimos três meses), as recomendações guidelines (como as da ATS/IDSA e a prática clínica corrente em Portugal) sugerem a cobertura de patógenos típicos e atípicos.
> 
> Existem duas opções principais de primeira linha: a terapia combinada ou a monoterapia com uma fluoroquinolona respiratória.
> 
> ### 1. Terapia Combinada (Beta-lactamina + Macrolídeo ou Doxiciclina)
> 
> Esta é frequentemente a opção preferencial para evitar a pressão seletiva de fluoroquinolonas.
> 
> **Opção A: Amoxicilina + Ácido Clavulânico e Azitromicina**
> *   **Amoxicilina + Ácido Clavulânico:** 875 mg / 125 mg de 12 em 12 horas.
> *   **Azitromicina:** 500 mg no 1.º dia, seguido de 250 mg uma vez por dia (ou 500 mg em dias alternados).
> *   **Duração:** 5 a 7 dias (dependendo da resposta clínica).
> 
> **Opção B: Amoxicilina + Ácido Clavulânico e Claritromicina**
> *   **Amoxicilina + Ácido Clavulânico:** 875 mg / 125 mg de 12 em 12 horas.
> *   **Claritromicina:** 500 mg de 12 em 12 horas.
> *   **Duração:** 5 a 7 dias.
> 
> **Opção C: Amoxicilina + Ácido Clavulânico e Doxiciclina**
> *   **Amoxicilina + Ácido Clavulânico:** 875 mg / 125 mg de 12 em 12 horas.
> *   **Doxiciclina:** 100 mg de 12 em 12 horas.
> *   **Duração:** 5 a 7 dias.
> 
> ---
> 
> ### 2. Monoterapia (Fluoroquinolona Respiratória)
> 
> Reservada para doentes com alergias graves a beta-lactaminas ou quando a terapia combinada não é viável.
> 
> **Levofloxacina**
> *   **Dose:** 750 mg.
> *   **Intervalo:** Uma vez por dia (24h).
> *   **Duração:** 5 a 7 dias.
> 
> *(Alternativa: Moxifloxacina 400 mg, uma vez por dia, durante 5 a 7 dias).*
> 
> ---
> 
> ### Interações, Contraindicações e Ajustes
> 
> #### Beta-lactaminas (Amoxicilina/Clavulanate)
> *   **Contraindicações:** Hipersensibilidade grave (anafilaxia) a penicilinas ou cefalosporinas.
> *   **Ajustes:** Necessário ajuste de dose em doentes com insuficiência renal grave ($\text{ClCr} < 30 \text{ ml/min}$).
> 
> #### Macrolídeos (Azitromicina/Claritromicina)
> *   **Interações:** Cuidado com fármacos que prolongam o intervalo QT (ex: antiarrítmicos, alguns antidepressivos). A Claritromicina é um inibidor potente do CYP3A4, interagindo com estatinas (simvastatina) e varfarina.
> *   **Contraindicações:** Hipersensibilidade a macrolídeos.
> *   **Ajustes:** A azitromicina geralmente não requer ajuste renal.
> 
> #### Doxiciclina
> *   **Contraindicações:** Hipersensibilidade; contraindicado na gravidez e em crianças menores de 8 anos (risco de coloração dentária).
> *   **Interações:** Redução da absorção se tomada com antiácidos, ferro ou cálcio (espaçar a toma).
> 
> #### Fluoroquinolonas (Levofloxacina/Moxifloxacina)
> *   **Contraindicações:** Hipersensibilidade; histórico de rotura de tendão associada a quinolonas.
> *   **Interações:** Aumentam o efeito de anticoagulantes orais; interagem com antiácidos e quelantes (tomar afastado das refeições/suplementos).
> *   **Precauções:** Risco de prolongamento do intervalo QT, tendinites/rotura tendinosa, aneurisma da aorta e flutuações glicémicas (especialmente em diabéticos).
> *   **Ajustes:** A **Levofloxacina** requer ajuste rigoroso da dose conforme a função renal ($\text{ClCr}$). A Moxifloxacina não requer ajuste renal significativo.
> 
> **Nota Final:** A duração de 5 dias é considerada adequada se o doente estiver clinicamente estável (afebril há 48-72h e com estabilidade hemodinâmica). Se a evolução for lenta, prolongar para 7 ou 10 dias.

**Critérios que falharam.**

- `dose_incorreta` (risco critico): nenhum de: '1000 mg', '1000mg', '1 g'

#### ATB-DPOC-012

**Pergunta.** Exacerbação aguda GRAVE de DPOC em ambulatório. Qual a antibioterapia indicada? Indique fármaco, dose, intervalo e duração.

**Resposta de referência.** Amoxicilina com ácido clavulânico 500 mg + 125 mg, oral, de 8 em 8 horas, durante 5 a 7 dias.

**Fonte.** APMGF; DGS, Guia de Bolso de Antibioterapia em Ambulatório, edição 1.3, novembro 2025, p. 19; Norma DGS n.º 005/2019 de 26/08/2019, ponto c), p. 7 (fármaco e duração)

**O que o modelo respondeu (amostra 1).**

> Esta resposta baseia-se nas recomendações gerais do GOLD (*Global Initiative for Chronic Obstructive Lung Disease*).
> 
> Numa exacerbação aguda **GRAVE** de DPOC, mesmo que gerida em ambulatório (embora a gravidade geralmente indique internamento), a escolha do antibiótico deve cobrir os patógenos mais comuns (*H. influenzae, S. pneumoniae, M. catarrhalis*) e, dependendo dos fatores de risco do doente, considerar a possibilidade de *Pseudomonas aeruginosa*.
> 
> Para um doente com exacerbação grave, recomenda-se a utilização de um antibiótico de largo espetro.
> 
> ### Antibioticoterapia Indicada (Primeira Linha)
> 
> **Fármaco:** Amoxicilina + Ácido Clavulânico (Co-amoxiclav)
> *   **Dose:** 875 mg / 125 mg
> *   **Intervalo:** De 12 em 12 horas (BID)
> *   **Duração:** 5 a 7 dias
> 
> ---
> 
> ### Alternativa (em caso de alergia a penicilinas ou falha terapêutica/fatores de risco)
> 
> Se o doente apresentar comorbilidades graves, idade avançada ou tiver utilizado antibióticos recentemente, pode optar-se por uma fluoroquinolona respiratória:
> 
> **Fármaco:** Levofloxacino
> *   **Dose:** 500 mg
> *   **Intervalo:** De 24 em 24 horas (QD)
> *   **Duração:** 5 dias
> 
> ---
> 
> ### Interações, Contraindicações e Ajustes
> 
> #### 1. Amoxicilina + Ácido Clavulânico
> *   **Contraindicações:**
>     *   Hipersensibilidade conhecida a penicilinas ou a qualquer beta-lactama.
>     *   Histórico de icterícia colestática ou disfunção hepática associada a amoxicilina/clavulanato.
> *   **Interações:**
>     *   **Alopurinol:** Aumenta o risco de erupções cutâneas.
>     *   **Anticoagulantes orais:** Pode potenciar o efeito da varfarina (monitorizar INR).
>     *   **Contracecionais orais:** Possível redução da eficácia (embora clinicamente raro).
> *   **Ajustes:**
>     *   **Insuficiência Renal:** Ajustar dose se o ClCr < 30 mL/min.
>         *   ClCr 10-30 mL/min: Dose máxima de 500/125 mg de 12 em 12h.
>         *   ClCr < 10 mL/min: Dose máxima de 500/125 mg de 24 em 24h.
> 
> #### 2. Levofloxacino
> *   **Contraindicações:**
>     *   Hipersensibilidade a quinolonas.
>     *   Histórico de tendinites ou rotura de tendão associadas a quinolonas.
> *   **Interações:**
>     *   **Antiácidos/Suplementos de Cálcio, Magnésio, Alumínio ou Ferro:** Reduzem significativamente a absorção (administrar com intervalo de 2 horas).
>     *   **Teofilina:** Pode aumentar os níveis plasmáticos de teofilina (risco de toxicidade).
>     *   **Warfarina:** Potencia o efeito anticoagulante.
> *   **Ajustes:**
>     *   **Insuficiência Renal:** Ajuste rigoroso obrigatório com base no ClCr.
>         *   ClCr 50-80 mL/min: Dose total reduzida ou intervalo alargado.
>         *   ClCr < 50 mL/min: Requer redução da dose diária (ex: 250 mg/dia ou 500 mg a cada 48h, dependendo do grau de falência).
> 
> **Nota Clínica:** Uma exacerbação classificada como "GRAVE" requer reavaliação imediata. Se houver sinais de insuficiência respiratória aguda, instabilidade hemodinâmica ou falha na resposta inicial ao tratamento ambulatorio, o doente deve ser transferido urgentemente para o meio hospitalar.

**Critérios que falharam.**

- `dose_incorreta` (risco critico): '500 mg' está na resposta mas não é de 'amoxicilina', 'clavulânico', 'clavulanico' ou está num ajuste: ...* levofloxacino *   **dose:** 500 mg *   **intervalo:** de 24 em 24 horas (qd) *   **durac...
- `dose_incorreta` (risco critico): nenhum de: '8/8', '8 em 8', 'tres vezes por dia', '3 vezes por dia', '3x/dia', '3 x dia', 'a cada 8 horas', 'tid', 'cada 8 horas', 'cada 8 h', 'tres vezes ao dia', '3 vezes ao dia', '3 x ao dia', '8/8h', '3x ao dia'

#### ATB-FAR-014

**Pergunta.** Adulto com amigdalofaringite aguda estreptocócica e história de hipersensibilidade NÃO tipo I à penicilina. Qual a antibioterapia adequada? Indique fármaco, dose, intervalo e duração.

**Resposta de referência.** Cefuroxima 250 mg, oral, de 12 em 12 horas, durante 10 dias.

**Fonte.** APMGF, Guia de Bolso de Antibioterapia em Ambulatório, edição 1.3, novembro 2025, p. 13

**O que o modelo respondeu (amostra 2).**

> Para um adulto com amigdalofaringite aguda estreptocócica (Grupo A) e história de hipersensibilidade **NÃO tipo I** (ou seja, reação não anafilática, como exantema maculopapular) à penicilina, as cefalosporinas de primeira geração são clinicamente aceitáveis, dado o baixo risco de reatividade cruzada nestes casos.
> 
> A opção terapêutica adequada é:
> 
> **Fármaco:** Cefadroxila
> *   **Dose:** 1 g
> *   **Intervalo:** De 24 em 24 horas (dose única diária)
> *   **Duração:** 10 dias
> 
> ---
> 
> ### Considerações Clínicas
> 
> **1. Interações:**
> *   **Probenecida:** Pode aumentar os níveis séricos de cefadroxila ao diminuir a sua excreção renal.
> *   **Diuréticos de asa:** O uso concomitante de cefalosporinas e diuréticos potentes pode aumentar o risco de neurotoxicidade (convulsões).
> 
> **2. Contraindicações:**
> *   Hipersensibilidade grave (anafilaxia) a qualquer cefalosporina.
> *   Hipersensibilidade tipo I à penicilina (embora o caso especifique ser NÃO tipo I, qualquer sinal de angioedema ou choque anafilático prévio contraindicaria esta classe).
> 
> **3. Ajustes Relevantes:**
> *   **Função Renal:** É necessário ajustar a dose em doentes com insuficiência renal. Se a depuração da creatinina (ClCr) for inferior a 50 ml/min, a dose deve ser reduzida ou o intervalo alargado.
> *   **Alternativa em caso de preferência por evitar Beta-lactamas:** Se o médico optar por evitar totalmente as beta-lactamas (apesar da reação não ser tipo I) ou se houver contraindicação às cefalosporinas, a alternativa seria a **Claritromicina** (500 mg de 12 em 12 horas durante 10 dias) ou a **Clindamicina** (300 mg de 8 em 8 horas durante 10 dias).
> 
> **Nota:** A duração de 10 dias é fundamental para garantir a erradicação do *Streptococcus pyogenes* e a prevenção da febre reumática.

**Critérios que falharam.**

- `resposta_incompleta` (risco medio): nenhum de: 'cefuroxima'
- `dose_incorreta` (risco critico): nenhum de: '250 mg', '250mg'
- `dose_incorreta` (risco critico): 'de 12 em 12 horas' está na resposta mas não é de 'cefuroxima' ou está num ajuste: ...a **claritromicina** (500 mg de 12 em 12 horas durante 10 dias) ou a **clindamicina** (30...

#### INT-COL-016

**Pergunta.** Doente idoso com gota, medicado com colquicina. Precisa de claritromicina. Pode fazer os dois?

**Resposta de referência.** Não. A claritromicina não deve ser administrada concomitantemente com colquicina, por risco de toxicidade por colquicina, sobretudo no idoso.

**Fonte.** Infarmed / RCM, Resumo das Características do Medicamento, Claritromicina 500 mg, aprovado em julho de 2022, secções 4.3 e 4.4

**O que o modelo respondeu (amostra 1).**

> Caro colega,
> 
> A resposta curta é **não**. A associação de colquicina com claritromicina é **contraindicada**, especialmente num doente idoso.
> 
> ### Justificação Clínica e Interação
> A claritromicina é um potente inibidor do **CYP3A4** e da **glicoproteína-P (P-gp)**. A colquicina é metabolizada pelo CYP3A4 e é um substrato da P-gp. 
> 
> A inibição destes transportadores e enzimas leva a um aumento significativo das concentrações plasmáticas de colquicina, o que potencia drasticamente o risco de **toxicidade sistémica grave**.
> 
> ### Riscos Associados
> A toxicidade por colquicina pode manifestar-se através de:
> *   **Toxicidade gastrointestinal:** Diarreia grave, náuseas e vómitos.
> *   **Miopatia e Rabdomiólise:** Particularmente perigosa em idosos ou doentes com função renal comprometida.
> *   **Toxicidade Hematológica:** Pancitopenia e supressão da medula óssea.
> *   **Falência Multiorgânica:** Pode evoluir para choque e óbito.
> 
> ### Contraindicações e Ajustes
> *   **Contraindicação:** A administração concomitante de colquicina e claritromicina (ou outros inibidores fortes do CYP3A4, como o itraconazol ou o ritonavir) deve ser evitada.
> *   **Ajuste Recomendado:**
>     1.  **Substituição do Antibiótico:** Recomenda-se a substituição da claritromicina por um antibiótico que não interfira com o CYP3A4/P-gp (dependendo do foco infeccioso e da sensibilidade bacteriana, avaliar alternativas como a amoxicilina ou cefalosporinas).
>     2.  **Suspensão da Colquicina:** Se a claritromicina for absolutamente indispensável e não houver alternativa terapêutica, a colquicina deve ser **suspensa** durante todo o tratamento antibiótico e por alguns dias após a sua conclusão.
> 
> ### Dosagem
> Dado que a interação é grave e potencialmente fatal, **não existe uma dose segura de colquicina para ser administrada concomitantemente com claritromicina.**
> 
> Se, após a suspensão da claritromicina e normalização da função renal, o doente for retomar a colquicina para profilaxia de gota, a dose habitual em idosos é geralmente:
> *   **Dose:** 0,5 mg a 1 mg.
> *   **Intervalo:** 1 a 2 vezes por semana (ou conforme a necessidade clínica).
> *   **Duração:** Manutenção crónica.
> 
> **Nota importante:** Verifique sempre a função renal (estágio do Doença Renal Crónica) do doente, pois a insuficiência renal agrava significativamente o risco de toxicidade da colquicina.

**Critérios que falharam.**

- `interacao_omitida` (risco critico): prescreve 'claritromicina' em: ...ecomenda-se a substituicao da claritromicina por um antibiotico que nao interfira com o cy...

#### FMT-CIST-017

**Pergunta.** Responda apenas nesta forma exata, sem texto adicional: FÁRMACO | DOSE | INTERVALO | DURAÇÃO. Qual a antibioterapia de primeira linha para cistite não complicada na mulher não grávida?

**Resposta de referência.** Nitrofurantoína | 100 mg | 6/6h | 5 a 7 dias

**Fonte.** DGS, Norma n.º 015/2011 de 30/08/2011, Anexo VII, p. 6 (cistite aguda não complicada da mulher não grávida)

**O que o modelo respondeu (amostra 2).**

> FOSFOMICINA TROMETAMOL | 3g | Dose única | 1 dia

**Critérios que falharam.**

- `resposta_incompleta` (risco medio): nenhum de: 'nitrofurantoína', 'nitrofurantoina'
- `dose_incorreta` (risco critico): nenhum de: '100 mg', '100mg'
- `resposta_incompleta` (risco medio): nenhum de: '5 dias', '6 dias', '7 dias', 'cinco dias', 'sete dias'
- `dose_incorreta` (risco critico): nenhum de: '6/6', '6 em 6', 'quatro vezes por dia', '4 vezes por dia', '4x/dia', '4 x dia', 'a cada 6 horas', 'qid', 'cada 6 horas', 'cada 6 h', 'quatro vezes ao dia', '4 vezes ao dia', '4 x ao dia', '6/6h', '| 6 horas', '| 6 h', '4x ao dia', '6 horas'

#### PED-OMA-019

**Pergunta.** Criança de 3 anos, 15 kg, com otite média aguda, sem alergias e sem antibioterapia nos últimos 30 dias. Qual a antibioterapia de primeira linha? Indique dose por peso, dose máxima diária, intervalo e duração.

**Resposta de referência.** Amoxicilina 80 a 90 mg/kg/dia, até ao máximo de 3000 mg/dia, oral, de 12 em 12 horas, durante 5 dias, por a criança ter 2 ou mais anos.

**Fonte.** DGS, Norma n.º 007/2012 de 16/12/2012 atualizada a 28/10/2014, ponto 7, p. 2, ponto 11 c), p. 3, e Anexo I, quadro 2, p. 17

**O que o modelo respondeu (amostra 1).**

> Para a situação clínica descrita (criança de 3 anos, 15 kg, com otite média aguda, sem alergias e sem exposição recente a antibióticos), a antibioterapia de primeira linha é a **Amoxicilina**.
> 
> A dose elevada é preferida para garantir a eficácia contra pneumococos com sensibilidade reduzida à penicilina.
> 
> ### Esquema Posológico
> 
> *   **Fármaco:** Amoxicilina.
> *   **Dose por peso:** 80 a 90 mg/kg/dia.
> *   **Cálculo para 15 kg:** 1200 mg a 1350 mg por dia.
> *   **Intervalo:** Dividido em 2 ou 3 toma(s) diárias (de 12 em 12 horas ou de 8 em 8 horas).
> *   **Dose máxima diária:** 3 g/dia (limite do adulto).
> *   **Duração:** 7 a 10 dias (em crianças $\ge$ 2 anos, 7 dias podem ser suficientes para casos não graves, mas 10 dias é a recomendação clássica para garantir a erradicação).
> 
> ### Contraindicações
> *   Hipersensibilidade conhecida às penicilinas ou a outros fármacos beta-lactâmicos (ex: cefalosporinas, embora a reatividade cruzada seja baixa).
> 
> ### Interações
> *   **Alopurinol:** Pode aumentar a incidência de erupções cutâneas (rash).
> *   **Anticoagulantes orais:** Pode potenciar o efeito anticoagulante (menos relevante nesta faixa etária).
> *   **Metotrexato:** Pode reduzir a excreção renal do metotrexato, aumentando a sua toxicidade.
> 
> ### Ajustes Relevantes
> *   **Insuficiência Renal:** Em caso de insuficiência renal grave (ClCr < 30 mL/min), a dose deve ser reduzida ou o intervalo alargado.
> *   **Mononucleose Infecciosa:** Deve evitar-se a amoxicilina se houver suspeita de mononucleose, devido ao risco elevado de desenvolvimento de um exantema maculopapular não alérgico.
> 
> ***
> 
> **Nota:** Esta resposta baseia-se nas diretrizes pediátricas standard para o tratamento de otite média aguda (ex: AAP - American Academy of Pediatrics). Deve sempre validar a prescrição com a bula do medicamento disponível no serviço e a situação clínica atual do doente.

**Critérios que falharam.**

- `dose_incorreta` (risco critico): nenhum de: '5 dias'

#### PED-OMA-020

**Pergunta.** Criança de 18 meses, 11 kg, com otite média aguda, sem alergias e sem antibioterapia nos últimos 30 dias. Qual a antibioterapia de primeira linha? Indique dose por peso, dose máxima diária, intervalo e duração.

**Resposta de referência.** Amoxicilina 80 a 90 mg/kg/dia, até ao máximo de 3000 mg/dia, oral, de 12 em 12 horas, durante 7 dias, porque a criança tem menos de 2 anos.

**Fonte.** DGS, Norma n.º 007/2012 de 16/12/2012 atualizada a 28/10/2014, ponto 7, p. 2, ponto 11 a), p. 3, e Anexo I, quadro 2, p. 17

**O que o modelo respondeu (amostra 1).**

> Para a situação clínica descrita (criança de 18 meses com otite média aguda, sem alergias e sem exposição recente a antibióticos), a antibioticoterapia de primeira linha é a **Amoxicilina**.
> 
> Abaixo seguem os detalhes terapêuticos:
> 
> ### Esquema Posológico
> *   **Fármaco:** Amoxicilina (suspensão oral).
> *   **Dose por peso:** 80 a 90 mg/kg/dia (dose elevada para garantir a eficácia contra pneumococos com sensibilidade reduzida).
> *   **Cálculo para 11 kg:** 880 mg a 990 mg por dia.
> *   **Dose máxima diária:** 3 g/dia (não atingida neste caso).
> *   **Intervalo:** Dividido em 2 ou 3 doses diárias (a cada 12 ou 8 horas). 
>     *   *Exemplo (8h):* Aproximadamente 300 mg a cada 8 horas.
> *   **Duração:** 10 dias (recomendado para crianças com menos de 2 anos).
> 
> ### Contraindicações
> *   Hipersensibilidade conhecida à amoxicilina ou a qualquer outro beta-lactâmico (penicilinas, cefalosporinas, carbapenemes).
> 
> ### Interações Medicamentosas
> *   **Alopurinol:** Aumenta a incidência de exantemas cutâneos.
> *   **Metotrexato:** Pode reduzir a excreção renal do metotrexato, aumentando a sua toxicidade.
> *   **Anticoagulantes orais:** Pode potenciar o efeito de alguns anticoagulantes (embora irrelevante nesta faixa etária).
> 
> ### Ajustes Relevantes
> *   **Insuficiência Renal:** Se a depuração da creatinina for inferior a 30 mL/min, a dose deve ser reduzida ou o intervalo prolongado.
> *   **Mononucleose Infecciosa:** Deve ter-se cautela, pois a administração de amoxicilina em doentes com mononucleose induz frequentemente a appearance de um exantema maculopapular não alérgico.
> 
> **Referências:** Baseado nas recomendações gerais de pediatria (AAP e guidelines europeias de otite média aguda).

**Critérios que falharam.**

- `resposta_incompleta` (risco medio): nenhum de: '12/12', '12 em 12', 'duas vezes por dia', '2 vezes por dia'
- `dose_incorreta` (risco critico): nenhum de: '7 dias'

#### PED-OMA-021

**Pergunta.** Criança de 4 anos, 16 kg, com otite média aguda e antecedente de anafilaxia à amoxicilina. Qual a antibioterapia? Indique dose por peso, dose máxima diária, intervalo e duração.

**Resposta de referência.** Um macrólido: azitromicina 10 mg/kg/dia, até ao máximo de 500 mg/dia, de 24 em 24 horas, durante 3 dias; claritromicina 15 mg/kg/dia, até ao máximo de 1 g/dia, de 12 em 12 horas, durante 5 dias; ou eritromicina 50 mg/kg/dia, até ao máximo de 2 g/dia, de 6 em 6 ou de 8 em 8 horas, durante 5 dias. A amoxicilina, com ou sem ácido clavulânico, e a cefuroxima não devem ser usadas: a cefuroxima só é alternativa na hipersensibilidade não tipo I.

**Fonte.** DGS, Norma n.º 007/2012 de 16/12/2012 atualizada a 28/10/2014, ponto 10 a), p. 2-3, ponto 11 c), p. 3, e Anexo I, quadro 2, p. 17

**Corrigida contra a alternativa:** claritromicina.

**O que o modelo respondeu (amostra 3).**

> Considerando que a criança apresenta um antecedente de **anafilaxia** à amoxicilina (hipersensibilidade do Tipo I), todos os beta-lactâmicos, incluindo as cefalosporinas, devem ser evitados devido ao risco de reatividade cruzada.
> 
> Neste cenário, a escolha terapêutica recai sobre macrólidos ou lincosamidas. A claritromicina é uma opção adequada para o tratamento da Otite Média Aguda (OMA) nestes casos.
> 
> ### Opção Terapêutica: Claritromicina
> 
> **1. Posologia e Administração:**
> *   **Dose por peso:** 15 mg/kg/dia.
> *   **Cálculo para 16 kg:** $16 \text{ kg} \times 15 \text{ mg/kg} = 240 \text{ mg/dia}$.
> *   **Intervalo:** Administrar em duas doses iguais (dividido de 12 em 12 horas).
>     *   **Dose por toma:** 120 mg a cada 12 horas.
> *   **Dose máxima diária:** 500 mg/dia (dose de adulto).
> *   **Duração:** 7 a 10 dias.
> 
> **2. Contraindicações:**
> *   Hipersensibilidade conhecida a macrólidos.
> *   Insuficiência hepática grave.
> *   Uso concomitante de ergotamina ou dihidroergotamina.
> 
> **3. Interações Relevantes:**
> *   **Inibidores/Indutores do CYP3A4:** A claritromicina é um potente inibidor do CYP3A4, podendo aumentar os níveis plasmáticos de fármacos metabolizados por esta via (ex: certas estatinas, tecaflur).
> *   **Prolongamento do intervalo QT:** Evitar a associação com outros fármacos que prolonguem o intervalo QT (ex: alguns antiarrítmicos ou antipsicóticos), devido ao risco de *Torsades de Pointes*.
> 
> **4. Ajustes:**
> *   **Ajuste Renal:** Em caso de insuficiência renal grave (ClCr < 30 mL/min), a dose deve ser reduzida para metade da dose habitual. No caso desta criança, presumindo-se função renal normal, não é necessário ajuste.
> 
> ---
> **Nota clínica:** Dada a crescente resistência de *Streptococcus pneumoniae* e *Haemophilus influenzae* aos macrólidos, deve ser efetuado um acompanhamento rigoroso da evolução clínica. Caso não haja melhoria em 48-72 horas, deve ser reconsiderada a terapêutica (ex: Clindamicina, dependendo da epidemiologia local e sensibilidades).

**Critérios que falharam.**

- `ajuste_omitido` (risco alto): nenhum de: '1000 mg', '1000mg', '1 g'
- `dose_incorreta` (risco critico): nenhum de: '5 dias', 'cinco dias'

#### AJU-MET-018

**Pergunta.** Doente de 78 anos com diabetes tipo 2, medicado com metformina, com depuração da creatinina de 40 ml/min. Pode manter a metformina? Que ajuste é necessário e porquê?

**Resposta de referência.** Pode, com dose reduzida. Com TFG entre 45 e 59 ml/min a dose máxima diária é de 2000 mg; entre 30 e 44 ml/min a dose máxima diária é de 1000 mg. Abaixo de 30 ml/min a metformina está contraindicada. A restrição justifica-se pelo risco de acidose láctica. A função renal deve ser vigiada com maior frequência no idoso.

**Fonte.** Comissão Europeia / RCM harmonizado, Resumo das Características do Medicamento, metformina, secções 4.2 e 4.3, após a revisão europeia de 2016

**O que o modelo respondeu (amostra 4).**

> Sim, o doente pode manter a metformina, mas é necessário realizar um ajuste posológico.
> 
> ### Ajuste e Justificação
> Com uma depuração da creatinina ($\text{ClCr}$) de $40 \text{ ml/min}$, o doente encontra-se no intervalo de função renal moderadamente diminuída (estágio 3b da Doença Renal Crónica).
> 
> **Ajuste necessário:** Deve ser reduzida a dose para, no máximo, **$1000 \text{ mg/dia}$**.
> 
> **Justificação:** A metformina é eliminada quase exclusivamente por via renal. A diminuição da depuração aumenta a concentração plasmática do fármaco, elevando significativamente o risco de **acidose láctica**, uma complicação rara, mas com elevada mortalidade.
> 
> ---
> 
> ### Esquema Terapêutico Sugerido
> *   **Fármaco:** Metformina.
> *   **Dose:** $500 \text{ mg}$ (se a dose anterior for superior).
> *   **Intervalo:** Duas vezes ao dia (ex: $500 \text{ mg}$ ao pequeno-almoço e $500 \text{ mg}$ ao jantar), para minimizar efeitos gastrointestinais.
> *   **Duração:** Manutenção crónica, condicionado à função renal.
> 
> ---
> 
> ### Interações e Precauções Relevantes
> 
> **1. Interações Críticas:**
> *   **Contrastes Iodados:** O fármaco deve ser **suspenso** antes ou no momento da administração de contrastes iodados endovenosos (especialmente com $\text{ClCr} < 60 \text{ ml/min}$), devido ao risco de insuficiência renal aguda precipitante e consequente acidose láctica. A metformina deve ser reiniciada apenas 48 horas após o procedimento, após confirmação de que a função renal permanece estável.
> *   **Outros Nefrotóxicos:** Cautela redobrada com a utilização de IECA, ARA II ou diuréticos, que podem alterar a função renal e predispor à acumulação de metformina.
> 
> **2. Contraindicações:**
> *   **$\text{ClCr} < 30 \text{ ml/min}$:** A metformina é absolutamente contraindicada.
> *   **Insuficiência Cardíaca Descompensada:** Risco aumentado de hipoperfusão renal e acidose láctica.
> *   **Acidose Metabólica:** Incluindo a cetoacidose diabética.
> 
> **3. Monitorização:**
> *   Recomenda-se a monitorização da função renal (creatinina e $\text{ClCr}$) a cada 3 a 6 meses neste doente, dada a idade e a fragilidade da função renal.
> *   Suspender a medicação em caso de desidratação grave, infeções sistémicas ou episódios de choque.

**Critérios que falharam.**

- `ajuste_omitido` (risco alto): nenhum de: '1000 mg', '1000mg', '1 g'

#### GRA-VPA-024

**Pergunta.** Mulher de 26 anos, sem contraceção, com perturbação bipolar. O psiquiatra pondera iniciar valproato. Pode? Em que condições?

**Resposta de referência.** Na perturbação bipolar o valproato está contraindicado na gravidez e, em mulheres em idade fértil, só pode ser usado se forem cumpridas as condições do programa de prevenção da gravidez: contraceção eficaz sem interrupção, teste de gravidez antes de iniciar e durante o tratamento, informação sobre o risco de malformações congénitas e de perturbações do neurodesenvolvimento, e revisão pelo menos anual por especialista. Sem contraceção, não deve iniciar.

**Fonte.** EMA / RCM harmonizado, Valproato, arbitragem do artigo 31.º (2018), Anexo III, alterações às secções 4.3, 4.4 e 4.6 do RCM, pp. 77-79 e 82

**O que o modelo respondeu (amostra 2).**

> Esta é uma questão crítica de segurança farmacológica e ética clínica. A resposta curta é: **O valproato está contraindicado em mulheres em idade fértil, a menos que não existam alternativas terapêuticas eficazes ou toleradas.**
> 
> Abaixo detalho as condições e a gestão clínica necessária.
> 
> ### 1. Pode iniciar valproato?
> **Apenas em última instância.** Devido ao elevado risco de teratogenia (defeitos do tubo neural, malformações congénitas) e de prejuízo do desenvolvimento cognitivo na descendência, a Agência Europeia de Medicamentos (EMA) e o Infarmed impuseram restrições severas.
> 
> **Condições obrigatórias para a prescrição:**
> 1. **Exaustão de Alternativas:** O psiquiatra deve documentar que outras terapias (ex: Lítio, Quetiapina, Olanzapina, Lamotrigina) foram testadas e falharam ou são contraindicadas.
> 2. **Contraceção Eficaz:** A doente **não pode** iniciar o fármaco sem contraceção. Deve utilizar um método altamente eficaz (ex: DIU, implante ou pílula combinada).
> 3. **Programa de Prevenção de Gravidez:** A doente deve assinar um termo de consentimento informado, declarando compreender os riscos e comprometendo-se a utilizar contraceção rigorosa.
> 4. **Vigilância:** Realização regular de testes de gravidez.
> 
> ---
> 
> ### 2. Plano Terapêutico (se indicado e consentido)
> 
> Se, após a análise rigorosa, for decidido iniciar o fármaco:
> 
> *   **Fármaco:** Valproato de Sódio (ou Ácido Valproico).
> *   **Dose Inicial:** 500 mg a 750 mg por dia.
> *   **Intervalo:** Dividido em 2 a 3 tomas diárias (ou dose única se for a formulação de libertação prolongada).
> *   **Titulação:** Aumentar gradualmente (ex: 250-500 mg a cada semana) até à resposta clínica ou atingir a janela terapéutica plasmática.
> *   **Dose de Manutenção:** Geralmente entre 15 mg/kg/dia e 30 mg/kg/dia.
> *   **Duração:** Tratamento crónico/longo prazo (estabilizador do humor).
> *   **Monitorização:** Determinação da valproemia (níveis plasmáticos ideais: 50–100 $\mu$g/mL).
> 
> ---
> 
> ### 3. Contraindicações, Interações e Ajustes
> 
> #### Contraindicações
> *   **Gravidez ou planeamento de gravidez:** Contraindicação absoluta.
> *   **Insuficiência Hepática Grave:** Risco de hepatotoxicidade grave.
> *   **Perturbações do Ciclo da Ureia:** Contraindicado devido ao risco de hiperamonemia.
> *   **Doença Mitocondrial:** Especialmente se houver antecedentes familiares de síndrome de Alport ou Polinosoma.
> 
> #### Interações Relevantes
> *   **Lamotrigina:** O valproato inibe a glucuronidação da lamotrigina, **duplicando a sua meia-vida**. Se forem usados em conjunto, a dose de lamotrigina deve ser reduzida drasticamente para evitar o risco de Síndrome de Stevens-Johnson.
> *   **Indutores Enzimáticos (ex: Carbamazepina, Fenitoína):** Reduzem a concentração plasmática do valproato.
> *   **Inibidores Enzimáticos:** Podem aumentar a toxicidade do valproato.
> 
> #### Ajustes e Monitorização
> *   **Função Hepática:** Monitorizar transaminases (TGO/TGP) regularmente, especialmente nos primeiros 6 meses.
> *   **Hemograma:** Monitorizar plaquetas (risco de trombocitopenia).
> *   **Peso:** O valproato está associado a ganho ponderal significativo e síndrome metabólica; requer monitorização do IMC e glicémia.
> *   **Ajuste Renal:** Geralmente não requer ajuste de dose, mas deve monitorizar-se a função renal em tratamentos prolongados.
> 
> **Nota Final:** Se a doente não utiliza contraceção e não há uma justificação clínica imperativa para o valproato, a sua prescrição nesta fase seria considerada negligente face às normas de segurança atuais.

**Critérios que falharam.**

- `resposta_incompleta` (risco medio): nenhum de: 'teste de gravidez'

#### DOS-MTX-027

**Pergunta.** Doente de 55 anos com artrite reumatoide vai iniciar metotrexato oral. Qual a posologia?

**Resposta de referência.** Metotrexato oral uma vez por semana, nunca diariamente: 7,5 a 20 mg por semana, ajustado à resposta, sem ultrapassar a dose máxima recomendada de 20 mg por semana. O dia da toma deve ficar escrito na receita. A toma diária por engano tem causado toxicidade fatal. O ácido fólico ou o ácido folínico reduzem a toxicidade.

**Fonte.** Infarmed / RCM, Ledertrexato 2,5 mg comprimidos, Resumo das Características do Medicamento, secção 4.2, revisão de 03/2025, pp. 2-3

**O que o modelo respondeu (amostra 2).**

> Esta é a resposta clínica para a gestão do metotrexato no contexto da artrite reumatoide (AR), redigida em português europeu e direcionada a um profissional de saúde.
> 
> ### Posologia do Metotrexato (Via Oral)
> 
> No tratamento da artrite reumatoide, o metotrexato é administrado em regime de dose baixa e **estritamente semanal**.
> 
> *   **Dose Inicial:** Geralmente inicia-se com **7,5 mg a 15 mg, uma vez por semana**.
> *   **Intervalo:** Uma única dose semanal (é crítico reforçar ao doente que o fármaco **não** é diário).
> *   **Titulação:** A dose pode ser aumentada progressivamente (em incrementos de 2,5 mg a 5 mg a cada 2 a 4 semanas) com base na resposta clínica e tolerância do doente.
> *   **Dose de Manutenção:** A dose habitual varia entre **15 mg e 25 mg por semana**. Doses acima de 25 mg/semana apresentam frequentemente menor eficácia e maior toxicidade.
> *   **Duração:** O tratamento é crónico, mantendo-se enquanto houver atividade da doença ou até que se atinja a remissão/baixa atividade, podendo ser reduzido para a dose mínima eficaz.
> 
> **Suplementação Obrigatória:**
> Para reduzir a toxicidade (especialmente gastrointestinal e hematológica), deve ser prescrito **Ácido Fólico**:
> *   **Dose:** 5 mg.
> *   **Intervalo:** Uma vez por semana (administrado 24 a 48 horas após a dose de metotrexato).
> 
> ---
> 
> ### Contraindicações
> 
> *   **Gravidez e Amamentação:** Contraindicado (teratogénico e abortivo). É obrigatório o uso de contraceceção eficaz em mulheres em idade fértil e em homens (embora o risco masculino seja menor).
> *   **Insuficiência Renal Grave:** ClCr < 30 mL/min (devido à excreção renal do fármaco).
> *   **Insuficiência Hepática Grave** ou alcoolismo ativo.
> *   **Mielossupressão:** Leucopenia, trombocitopenia ou anemia grave pré-existente.
> *   **Infeções Graves** ou ativas (ex: tuberculose ativa não tratada).
> 
> ---
> 
> ### Interações Medicamentosas
> 
> *   **AINEs e Salicilatos:** Podem reduzir a excreção renal do metotrexato, aumentando o risco de toxicidade hematológica e gastrointestinal. Embora sejam frequentemente usados em conjunto na AR, requerem monitorização rigorosa.
> *   **Trimetoprima/Sulfametoxazol (TMP-SMX):** Potenciam significativamente a mielossupressão (sinergismo no bloqueio do folato). Deve evitar-se a combinação.
> *   **Inibidores da Bomba de Protões (IBP):** Podem retardar a depuração do metotrexato, aumentando os níveis plasmáticos.
> *   **Outros Imunossupressores:** Risco acrescido de infeções e citopenias.
> 
> ---
> 
> ### Ajustes e Monitorização
> 
> **Ajustes:**
> *   **Função Renal:** Se a depuração da creatinina estiver diminuída (mas acima de 30 mL/min), deve-se reduzir a dose inicial e a velocidade de titulação.
> *   **Função Hepática:** Se houver elevação significativa das transaminases (ALT/AST), deve-se reduzir a dose ou suspender temporariamente o fármaco.
> 
> **Monitorização Recomendada:**
> *   **Hemograma completo e Provas de Função Hepática (TGO/TGP) e Renal (Creatinina):**
>     *   Antes do início do tratamento.
>     *   A cada 2 a 4 semanas durante a fase de titulação.
>     *   A cada 8 a 12 semanas após estabilização da dose.

**Critérios que falharam.**

- `resposta_incompleta` (risco medio): nenhum de: '20 mg', '20mg'


## Interpretação

A taxa de respostas corretas, isolada, é insuficiente: um sistema que erra 5% das doses e outro que erra 5% do formato têm a mesma taxa e riscos muito diferentes. Cada falha é por isso classificada por tipo e por risco clínico, e a leitura começa pelas falhas críticas.
