# Relatório do Aferidor

Relatório escrito em 2026-10-03.

Este documento mede um sistema, não um doente. Não aconselha, não trata e não substitui julgamento clínico.

Os veredictos são a triagem automática do corretor; a validação por um especialista faz-se à parte, numa folha cega (`aferidor revisao`).

## Condições do ensaio

- **Banco de casos**: casos/casos.json (SHA-256 89ac69b77168)
- **gemini:gemma-4-26b-a4b-it**: 135 respostas, recolhidas 2026-10-01 11:22 a 2026-10-03 14:20; temperatura 1,0; tokens_max 8192; versão 0.1.0+13022a69b849

> **Aviso.** Nem todas as fontes destes casos foram confirmadas por uma pessoa. Até essa confirmação, os resultados medem o modelo contra valores transcritos automaticamente, e um valor de referência errado surge como erro do modelo. Ver `casos/VERIFICACAO.md`.

## Critério de aprovação

Protocolo **Gemma 4 26B A4B pela API gratuita, banco principal, 27 casos, corretor congelado**, escrito a 2026-10-01 (`protocolos/2026-10-01-gemma4-26b-casos.json`, SHA-256 4d51aabf6118).

| Modelo | Resultado | casos com as 5 amostras | casos com falha crítica em alguma amostra | casos parcialmente corretos | taxa de amostras corretas |
|---|---|---|---|---|---|
| `gemini:gemma-4-26b-a4b-it` | **reprovado** | 27 de 27 (todos os 27) | 12 de 27 (no máximo 0), **não cumpre** | 9 de 27 (no máximo 0), **não cumpre** | 59% (pelo menos 95%), **não cumpre** |

## Método de contagem

Cada caso foi colocado 5 vezes a cada modelo; cada resposta é uma amostra. Um caso é **sempre correto** quando todas as amostras são corretas, **nunca correto** quando nenhuma o é, e **parcialmente correto** nos restantes. Veredicto binário por caso: um caso é correto quando todas as amostras são corretas. Um caso nunca correto não tem necessariamente uma falha crítica, e um caso parcialmente correto pode ter uma; por isso as falhas críticas são contadas à parte.

## gemini:gemma-4-26b-a4b-it

**12 de 27 casos com falha de risco crítico em pelo menos uma amostra** (IC 95% 28% a 63%). Uma falha crítica é um erro de dose, uma interação ou contraindicação omitida, um encaminhamento urgente omitido, ou um facto inventado.

**Casos corretos: 11 de 27** (IC 95% 25% a 59%), pela regra: todas as amostras são corretas.

79 de 135 amostras cumprem todos os critérios (59%, IC 95% 50% a 66%).

9 de 27 casos parcialmente corretos: o resultado variou entre amostras.

### Falhas por tipo

| Tipo de falha | Risco | Respostas |
|---|---|---|
| `dose_incorreta` | critico | 34 |
| `contraindicacao_omitida` | critico | 5 |
| `interacao_omitida` | critico | 3 |
| `ajuste_omitido` | alto | 15 |
| `resposta_incompleta` | medio | 16 |

### Português europeu

3 de 135 respostas com formas do português do Brasil, e 9 com grafia anterior ao Acordo Ortográfico. Mais frequentes: contracepção (PT: contraceção): 9; ô antes de m ou n (PT: ó, como em crónico): 3.

Indicador independente, baseado numa lista curta de formas alheias ao português europeu atual. Não entra na contagem de falhas e subestima a frequência real.

### Respostas que falharam

#### ATB-PAC-011

**Pergunta.** Qual é a antibioterapia de primeira linha para pneumonia adquirida na comunidade não grave, tratada em ambulatório, num adulto com comorbilidades ou com antibioterapia nos três meses anteriores? Indique fármacos, doses, intervalos e durações.

**Resposta de referência.** Amoxicilina 1000 mg, oral, de 8 em 8 horas, durante 3 a 7 dias, associada a um de três: azitromicina 500 mg, oral, uma vez por dia, durante 3 dias; claritromicina 500 mg, oral, de 12 em 12 horas; ou doxiciclina 200 mg na dose inicial, depois 100 mg de 12 em 12 horas.

**Fonte.** DGS, Norma n.º 045/2011 de 26/12/2011, ponto 4 b), p. 1, e ponto 5, p. 2; duração da amoxicilina: Norma n.º 006/2014 atualizada a 17/11/2022, Anexo II, quadro 1, p. 20

**Corrigida contra a alternativa:** amoxicilina com claritromicina.

**O que o modelo respondeu (amostra 1).**

> Para um adulto com pneumonia adquirida na comunidade (PAC) não grave, em regime de ambulatório, que apresenta comorbilidades (doença cardíaca, pulmonar, hepática ou renal crónica, diabetes mellitus ou alcoholismo) ou que utilizou antibioterapia nos últimos três meses, o risco de infeção por patógenos com resistência aumentada (como o *Streptococcus pneumoniae* resistente à penicilina) é maior.
> 
> Segundo as diretrizes da *European Respiratory Society* (ERS) e da *European Society of Clinical Microbiology and Infectious Diseases* (ESCMID), a estratégia de primeira linha baseia-se na cobertura de patógenos típicos e atípicos.
> 
> Existem duas abordagens principais recomendadas:
> 
> ### 1. Terapia Combinada (Recomendada)
> Consiste na associação de um beta-lactâmico com cobertura para germes típicos e um macrolídeo ou uma tetraciclina para cobertura de germes atípicos.
> 
> **Opção A: Amoxicilina/Ácido Clavulânico + Macrolídeo**
> *   **Amoxicilina/Ácido Clavulânico:** 875/125 mg, por via oral, de 12 em 12 horas.
> *   **Claritromicina:** 500 mg, por via oral, de 12 em 12 horas.
> *   **Duração:** 5 a 7 dias (ajustável conforme a resposta clínica e estabilidade hemodinâmica).
> 
> **Opção B: Amoxicilina/Ácido Clavulânico + Doxiciclina**
> *   **Amoxicilina/Ácido Clavulânico:** 875/125 mg, por via oral, de 12 em 12 horas.
> *   **Doxiciclina:** 100 mg, por via oral, de 12 em 12 horas.
> *   **Duração:** 5 a 7 dias.
> 
> ---
> 
> ### 2. Monoterapia com Fluoroquinolona Respiratória
> Caso a terapia combinada não seja preferível ou seja necessária uma abordagem simplificada.
> 
> *   **Levofloxacina:** 750 mg, por via oral, uma vez ao dia.
> *   **Moxifloxacina:** 400 mg, por via oral, uma vez ao dia.
> *   **Duração:** 5 a 7 dias.
> 
> ---
> 
> ### Interações, Contraindicações e Ajustes
> 
> #### **Amoxicilina/Ácido Clavulânico**
> *   **Contraindicações:** Hipersensibilidade conhecida a penicilinas ou cefalosporinas. História de icterícia ou disfunção hepática associada ao uso de ácido clavulânico.
> *   **Interações:** Pode reduzir a eficácia de certos anticonceptivos orais.
> *   **Ajustes:** Requer ajuste da dose em doentes com insuficiência renal grave (ClCr < 30 mL/min).
> 
> #### **Macrolídeos (ex: Claritromicina)**
> *   **Contraindicações:** Hipersensibilidade aos macrolídeos. Prolongamento do intervalo QT no ECG.
> *   **Interações:** Elevado potencial de interações via citocromo P450 (CYP3A4). Interage com estatinas (risco de rabdomiólise), varfarina (aumento do INR), teofilina e ciclosporina.
> *   **Ajustes:** Ajustar dose em insuficiência renal ou hepática moderada a grave.
> 
> #### **Doxiciclina**
> *   **Contraindicações:** Gravidez e amamentação. Crianças com ossos em crescimento (devido ao risco de coloração dentária).
> *   **Interações:** Diminuição da eficácia de anticonceptivos orais. Redução da absorção com sais de cálcio, magnésio, alumínio e ferro (deve ser administrada com intervalo de 2 horas).
> 
> #### **Fluoroquinolonas (Levofloxacina/Moxifloxacina)**
> *   **Contraindicações:** Hipersensibilidade a quinolonas. Histórico de tendinopatia ou rutura tendinosa. Pacientes com prolongamento do intervalo QT.
> *   **Interações:** Interação com antiácidos e suplementos que contenham iões bivalentes (Ca²⁺, Mg²⁺, Al³⁺), que reduzem a absorção. Potencial aumento dos efeitos de varfarina.
> *   **Riscos Associados:** Risco aumentado de efeitos adversos no Sistema Nervoso Central (delirium, convulsões) e risco de rotura de tendão (especialmente em idosos ou quem usa corticosteroides).
> *   **Ajustes:** A levofloxacina requer ajuste rigoroso da dose em doentes com insuficiência renal.
> 
> **Nota clínica:** A escolha final deve sempre considerar o perfil de resistência local e o histórico de alergias do paciente.

**Critérios que falharam.**

- `dose_incorreta` (risco critico): nenhum de: '1000 mg', '1000mg', '1 g'

#### ATB-DPOC-012

**Pergunta.** Exacerbação aguda GRAVE de DPOC em ambulatório. Qual a antibioterapia indicada? Indique fármaco, dose, intervalo e duração.

**Resposta de referência.** Amoxicilina com ácido clavulânico 500 mg + 125 mg, oral, de 8 em 8 horas, durante 5 a 7 dias.

**Fonte.** APMGF; DGS, Guia de Bolso de Antibioterapia em Ambulatório, edição 1.3, novembro 2025, p. 19; Norma DGS n.º 005/2019 de 26/08/2019, ponto c), p. 7 (fármaco e duração)

**O que o modelo respondeu (amostra 2).**

> **Nota clínica preliminar:** De acordo com as diretrizes internacionais (GOLD - *Global Initiative for Chronic Obstructive Lung Disease*), uma exacerbação de DPOC classificada como **GRAVE** (caracterizada por agravamento severo dos sintomas respiratórios, insuficiência respiratória aguda ou instabilidade cardiovascular) é, por definição, uma indicação de **hospitalização**. O tratamento em ambulatório deve ser reservado para casos moderados ou pacientes com fatores de risco muito específicos e estabilidade clínica aparente.
> 
> Se a decisão clínica for manter o tratamento em ambulatório, a escolha do antibiótico depende da presença de fatores de risco para patógenos resistentes (*Haemophilus influenzae*, *Streptococcus pneumoniae*, *Moraxella catarrhalis* e, em casos selecionados, *Pseudomonas aeruginosa*).
> 
> Seguem as opções terapêuticas recomendadas para cobertura empírica:
> 
> ### 1. Primeira Linha (Preferencial para cobertura de patógenos comuns)
> **Fármaco:** Amoxicilina + Ácido Clavulânico
> 
> *   **Dose:** 875 mg / 125 mg
> *   **Intervalo:** de 12 em 12 horas
> *   **Duração:** 5 a 7 dias (em alguns casos, até 10 dias, dependendo da resposta clínica)
> *   **Interações:**
>     *   Pode aumentar o efeito anticoagulante da **Varfarina** (monitorizar o INR).
>     *   Pode aumentar os níveis de **Metotrexato**.
> *   **Contraindicações:**
>     *   Hipersensibilidade conhecida a $\beta$-lactâmicos (penicilinas ou cefalosporinas).
>     *   História de icterícia ou disfunção hepática associada ao uso de amoxicilina/clavulanato.
> *   **Ajustes relevantes:**
>     *   **Função renal:** Em doentes com insuficiência renal grave (ClCr < 30 mL/min), deve ser considerada a redução da dose ou a utilização de uma alternativa.
> 
> ---
> 
> ### 2. Segunda Linha / Casos de Maior Risco (Quinolonas Respiratórias)
> *Indicado se houver falha terapêutica prévia, risco de resistência ou se o doente tiver comorbilidades que exijam uma cobertura mais alargada.*
> 
> **Fármaco:** Levofloxacino
> 
> *   **Dose:** 500 mg ou 750 mg
> *   **Intervalo:** de 24 em 24 horas
> *   **Duração:** 5 a 7 dias
> *   **Interações:**
>     *   **Quelação:** Redução da absorção se administrado com antiácidos, sais de ferro, cálcio ou magnésio.
>     *   **Anticoagulação:** Pode potenciar o efeito da **Varfarina**.
>     *   **QT:** Risco de prolongamento do intervalo QT se combinado com outros fármacos que prolonguem o QT (ex: alguns antiarrítmicos, certos antipsicóticos).
>     *   **Tizanidina:** Aumenta os níveis desta medicação.
> *   **Contraindicações:**
>     *   História de tendinite ou rotura de tendão (especialmente tendão de Aquiles).
>     *   História de prolongamento do intervalo QT ou arritmias ventriculares.
>     *   Epilepsia ou antecedentes de convulsões.
>     *   Gravidez e amamentação.
> *   **Ajustes relevantes:**
>     *   **Função renal:** Ajuste obrigatório da dose com base no *Clearance* de Creatinina (ClCr). Em insuficiência renal grave, a dose deve ser reduzida ou o intervalo prolongado.
> 
> ---
> 
> **Resumo para decisão clínica:**
> *   Se o doente é estável e sem riscos de resistência: **Amoxicilina/Ácido Clavulânico**.
> *   Se o doente é complexo, tem uso recente de antibióticos ou risco de patógenos gram-negativos: **Levofloxacino**.
> 
> *Nota: Se houver suspeita de Pseudomonas aeruginosa (ex: história de broniectasias, uso frequente de antibióticos ou DPOC muito grave), o tratamento em ambulatório não é recomendado e requer antibióticos com cobertura específica (ex: Ciprofloxacino ou Piperacilina/Tazobactam em ambiente hospitalar).*

**Critérios que falharam.**

- `dose_incorreta` (risco critico): nenhum de: '8/8', '8 em 8', 'tres vezes por dia', '3 vezes por dia', '3x/dia', '3 x dia', 'a cada 8 horas', 'tid', 'cada 8 horas', 'cada 8 h', 'tres vezes ao dia', '3 vezes ao dia', '3 x ao dia', '8/8h', '3x ao dia'

#### INT-COL-016

**Pergunta.** Doente idoso com gota, medicado com colquicina. Precisa de claritromicina. Pode fazer os dois?

**Resposta de referência.** Não. A claritromicina não deve ser administrada concomitantemente com colquicina, por risco de toxicidade por colquicina, sobretudo no idoso.

**Fonte.** Infarmed / RCM, Resumo das Características do Medicamento, Claritromicina 500 mg, aprovado em julho de 2022, secções 4.3 e 4.4

**O que o modelo respondeu (amostra 5).**

> A administração concomitante de **colquicina** e **claritromicina** deve ser **evitada** e é considerada uma contraindicação clínica importante devido ao elevado risco de toxicidade grave e potencialmente fatal.
> 
> Abaixo, detalho a fundamentação farmacológica e as recomendações clínicas:
> 
> ### 1. Interação Medicamentosa
> A interação é de natureza farmacocinética e ocorre por dois mecanismos principais:
> *   **Inibição do CYP3A4:** A claritromicina é um potente inibidor da isoenzima do citocromo P450 3A4. A colquicina é metabolizada em parte por esta via.
> *   **Inibição da Glicoproteína-P (P-gp):** A claritromicina também inibe a P-gp, uma proteína de transporte de efluxo presente no intestino e nos rins, responsável pela eliminação da colquicina.
> 
> **Consequência:** A inibição destes mecanismos resulta num aumento significativo e abrupto das concentrações plasmáticas de colquicina, levando a uma toxicidade sistémica. A colquicina tem um índice terapêutico muito estreito, o que significa que a diferença entre a dose eficaz e a dose tóxica é mínima.
> 
> ### 2. Riscos e Toxicidade
> O aumento dos níveis de colquicina no idoso (que frequentemente apresenta também uma redução fisiológica da função renal) pode desencadear:
> *   **Toxicidade Hematológica:** Neutropenia, anemia e trombocitopenia (supressão da medula óssea).
> *   **Toxicidade Gastrointestinal:** Diarreia severa, vómitos e dor abdominal (frequentemente o primeiro sinal de toxicidade).
> *   **Toxicidade Neurológica e Muscular:** Neuropatia periférica e miopatia/rabdomiólise.
> *   **Toxicidade Multiorgânica:** Insuficiência renal aguda e paragem cardiorrespiratória.
> 
> ### 3. Recomendações e Ajustes Clínicos
> 
> Perante a necessidade de tratamento antibiótico neste doente, as opções são:
> 
> **Opção A: Substituição do Antibiótico (Preferencial)**
> Se o espectro de atividade permitir, deve optar-se por um antibiótico que não iniba o CYP3A4.
> *   **Sugestão:** **Azitromicina**.
>     *   **Razão:** Embora seja um macrólido, a azitromicina tem um efeito mínimo ou nulo na inibição do CYP3A4 em comparação com a claritromicina, sendo mais segura para uso concomitante com colquicina.
>     *   *Nota: A dose e duração devem ser ajustadas conforme a patologia infecciosa alvo.*
> 
> **Opção B: Suspensão Temporária da Colquicina**
> Se a claritromicina for estritamente indispensável (ex: por perfil de resistência bacteriana específico):
> *   **Conduta:** Suspender a colquicina durante o curso do tratamento com claritromicina e por um período de segurança após a interrupção do antibiótico (dependendo da função renal do doente).
> *   **Gestão da Gota:** Se o doente estiver em fase de crise aguda de gota, o manejo deve ser feito com outros agentes, como AINEs (se a função renal permitir) ou corticosteroides orais.
> 
> **Opção C: Monitorização Estrita (Não recomendada como primeira linha)**
> Em cenários de extrema necessidade onde não se possa alterar nenhum dos fármacos, a monitorização de sinais de toxicidade deve ser imediata, mas dada a imprevisibilidade da toxicidade da colquicina, a **evitação da combinação é a única estratégia segura.**
> 
> ### Resumo para Decisão Clínica
> | Parâmetro | Detalhe |
> | :--- | :--- |
> | **Interação** | Claritromicina (Inibidor CYP3A4/P-gp) $\rightarrow$ $\uparrow$ Colquicina |
> | **Risco** | Toxicidade hematológica, neuromuscular e fatal |
> | **Contraindicação** | Uso concomitante não recomendado |
> | **Ajuste Sugerido** | Substituir Claritromicina por Azitromicina **OU** suspender Colquicina |

**Critérios que falharam.**

- `interacao_omitida` (risco critico): nenhum de: 'não deve', 'nao deve', 'contraindicad', 'evitar'

#### FMT-CIST-017

**Pergunta.** Responda apenas nesta forma exata, sem texto adicional: FÁRMACO | DOSE | INTERVALO | DURAÇÃO. Qual a antibioterapia de primeira linha para cistite não complicada na mulher não grávida?

**Resposta de referência.** Nitrofurantoína | 100 mg | 6/6h | 5 a 7 dias

**Fonte.** DGS, Norma n.º 015/2011 de 30/08/2011, Anexo VII, p. 6 (cistite aguda não complicada da mulher não grávida)

**O que o modelo respondeu (amostra 1).**

> NITROFURANTOÍNA (Contraindicações: Insuficiência renal grave [ClCr < 30 mL/min]; Ajustes: Redução de dose na insuficiência renal moderada; Interações: Antiacidos podem reduzir a absorção) | 100 mg | 12/12h | 5 dias

**Critérios que falharam.**

- `dose_incorreta` (risco critico): nenhum de: '6/6', '6 em 6', 'quatro vezes por dia', '4 vezes por dia', '4x/dia', '4 x dia', 'a cada 6 horas', 'qid', 'cada 6 horas', 'cada 6 h', 'quatro vezes ao dia', '4 vezes ao dia', '4 x ao dia', '6/6h', '| 6 horas', '| 6 h', '4x ao dia', '6 horas'

#### PED-OMA-019

**Pergunta.** Criança de 3 anos, 15 kg, com otite média aguda, sem alergias e sem antibioterapia nos últimos 30 dias. Qual a antibioterapia de primeira linha? Indique dose por peso, dose máxima diária, intervalo e duração.

**Resposta de referência.** Amoxicilina 80 a 90 mg/kg/dia, até ao máximo de 3000 mg/dia, oral, de 12 em 12 horas, durante 5 dias, por a criança ter 2 ou mais anos.

**Fonte.** DGS, Norma n.º 007/2012 de 16/12/2012 atualizada a 28/10/2014, ponto 7, p. 2, ponto 11 c), p. 3, e Anexo I, quadro 2, p. 17

**O que o modelo respondeu (amostra 1).**

> De acordo com as diretrizes clínicas pediátricas habituais (como as da Academia Americana de Pediatria e as recomendações de sociedades europeias) para o tratamento de Otite Média Aguda (OMA) em crianças sem história recente de antibioticoterapia ou alergias conhecidas, a abordagem é a seguinte:
> 
> ### Antibioterapia de Primeira Linha: **Amoxicilina**
> 
> **Posologia para uma criança de 15 kg:**
> 
> *   **Dose por peso:** 80 a 90 mg/kg/dia.
> *   **Dose total diária (para 15 kg):** 1200 mg a 1350 mg por dia.
> *   **Dose máxima diária:** Para esta criança, a dose deve basear-se no peso (não excedendo o limite terapêutico para a idade/peso), mas em termos gerais, não deve exceder a dose habitual de adulto.
> *   **Intervalo:** Administrar em duas tomas (de 12 em 12 horas) ou três tomas (de 8 em 8 horas).
>     *   *Exemplo (12/12h):* 600 mg a 675 mg por toma.
>     *   *Exemplo (8/8h):* 400 mg a 450 mg por toma.
> *   **Duração:** 5 a 7 dias (em crianças com idade $\ge$ 2 anos e sintomas leves/moderados; em casos mais graves ou com sintomas persistentes, pode prolongar-se até 10 dias).
> 
> ---
> 
> ### Notas Clínicas Relevantes
> 
> **1. Contraindicações:**
> *   Hipersensibilidade conhecida a penicilinas ou a qualquer outro agente beta-lactâmico (ex: cefalosporinas, carbapenems).
> 
> **2. Interações:**
> *   **Probenecida:** Aumenta as concentrações plasmáticas de amoxicilina (geralmente não relevante em pediatria, exceto em contextos muito específicos).
> *   **Anticonceptivos orais:** Embora teoricamente possa haver uma redução da eficácia, este fator não é clinicamente relevante para uma criança de 3 anos.
> 
> **3. Ajustes Relevantes:**
> *   **Insuficiência Renal:** Em caso de disfunção renal significativa (taxa de filtração glomerular < 30 mL/min), é necessário ajustar a dose e o intervalo, uma vez que a amoxicilina é excretada predominantemente por via renal.
> *   **Falha Terapêutica:** Se não houver melhoria clínica após 48-72 horas de tratamento, deve considerar-se a escalada para Amoxicilina com Ácido Clavulânico (para cobrir patógenos produtores de beta-lactamases) ou a investigação de complicações.
> 
> ***
> 
> *Nota: Esta resposta é uma orientação baseada em diretrizes clínicas padrão. A decisão terapêutica final cabe sempre ao médico assistente após avaliação clínica presencial do paciente.*

**Critérios que falharam.**

- `ajuste_omitido` (risco alto): nenhum de: '3000 mg', '3000mg', '3 g'
- `dose_incorreta` (risco critico): nenhum de: '5 dias'

#### PED-OMA-020

**Pergunta.** Criança de 18 meses, 11 kg, com otite média aguda, sem alergias e sem antibioterapia nos últimos 30 dias. Qual a antibioterapia de primeira linha? Indique dose por peso, dose máxima diária, intervalo e duração.

**Resposta de referência.** Amoxicilina 80 a 90 mg/kg/dia, até ao máximo de 3000 mg/dia, oral, de 12 em 12 horas, durante 7 dias, porque a criança tem menos de 2 anos.

**Fonte.** DGS, Norma n.º 007/2012 de 16/12/2012 atualizada a 28/10/2014, ponto 7, p. 2, ponto 11 a), p. 3, e Anexo I, quadro 2, p. 17

**O que o modelo respondeu (amostra 1).**

> Com base nas diretrizes clínicas internacionais e nacionais (como as da Academia Americana de Pediatria e as recomendações habituais da Sociedade Portuguesa de Pediatria) para o tratamento de Otite Média Aguda (OMA) em crianças, a abordagem é a seguinte:
> 
> ### **Antibioterapia de Primeira Linha**
> 
> O fármaco de escolha é a **Amoxicilina**.
> 
> ### **Posologia para a criança (11 kg)**
> 
> *   **Dose por peso:** 80 a 90 mg/kg/dia.
> *   **Cálculo da dose diária total:** 
>     *   Dose mínima (80 mg/kg): $11 \text{ kg} \times 80 \text{ mg} = 880 \text{ mg/dia}$.
>     *   Dose máxima recomendada para este peso (90 mg/kg): $11 \text{ kg} \times 90 \text{ mg} = 990 \text{ mg/dia}$.
> *   **Intervalo:** Administrar a dose total diária dividida em duas tomadas (de 12 em 12 horas) ou três tomadas (de 8 em 8 horas).
> *   **Duração do tratamento:** 10 dias (em crianças com idade inferior a 2 anos, a duração deve ser de 10 dias para garantir a erradicação do patógeno e prevenir complicações).
> 
> ### **Contraindicações**
> *   **Hipersensibilidade:** Alergia conhecida a penicilinas ou a outros antibióticos do grupo dos beta-lactâmicos (ex: cefalosporinas, embora a reação cruzada seja baixa, deve ser considerada se houver histórico de anafilaxia).
> 
> ### **Interações**
> *   Não existem interações medicamentosas clinicamente significativas de relevo para este quadro clínico pediátrico imediato. Contudo, deve notar-se que a administração concomitante de outros fármacos que alterem a flora intestinal pode aumentar o risco de diarreia associada ao antibiótico.
> 
> ### **Ajustes Relevantes**
> *   **Função Renal:** Em crianças com insuficiência renal conhecida, a dose deve ser ajustada com base no esclerostina/clareamento da creatinina (embora não seja o caso desta criança, dada a ausência de patologia renal referida).
> *   **Falha Terapêutica:** Caso não haja melhoria clínica após 48-72 horas de tratamento, deve considerar-se a transição para Amoxicilina com Ácido Clavulânico (para cobrir patógenos produtores de beta-lactamases, como *Haemophilus influenzae* ou *Moraxella catarrhalis*).

**Critérios que falharam.**

- `ajuste_omitido` (risco alto): nenhum de: '3000 mg', '3000mg', '3 g'
- `dose_incorreta` (risco critico): nenhum de: '7 dias'

#### PED-OMA-021

**Pergunta.** Criança de 4 anos, 16 kg, com otite média aguda e antecedente de anafilaxia à amoxicilina. Qual a antibioterapia? Indique dose por peso, dose máxima diária, intervalo e duração.

**Resposta de referência.** Um macrólido: azitromicina 10 mg/kg/dia, até ao máximo de 500 mg/dia, de 24 em 24 horas, durante 3 dias; claritromicina 15 mg/kg/dia, até ao máximo de 1 g/dia, de 12 em 12 horas, durante 5 dias; ou eritromicina 50 mg/kg/dia, até ao máximo de 2 g/dia, de 6 em 6 ou de 8 em 8 horas, durante 5 dias. A amoxicilina, com ou sem ácido clavulânico, e a cefuroxima não devem ser usadas: a cefuroxima só é alternativa na hipersensibilidade não tipo I.

**Fonte.** DGS, Norma n.º 007/2012 de 16/12/2012 atualizada a 28/10/2014, ponto 10 a), p. 2-3, ponto 11 c), p. 3, e Anexo I, quadro 2, p. 17

**Corrigida contra a alternativa:** azitromicina.

**O que o modelo respondeu (amostra 2).**

> Considerando o histórico de **anafilaxia** à amoxicilina, esta criança apresenta uma reação de hipersensibilidade do tipo I. Nestes casos, a utilização de qualquer agente do grupo dos beta-lactâmicos (incluindo cefalosporinas e carbapenemes) está **contraindicada** devido ao risco de reatividade cruzada.
> 
> Para o tratamento de Otite Média Aguda (OMA) num paciente com alergia grave à penicilina, a alternativa de primeira linha recomendada é um macrólido.
> 
> ### Prescrição Sugerida: Azitromicina
> 
> *   **Dose por peso:** 10 mg/kg/dia.
> *   **Dose total diária (para 16 kg):** 160 mg.
> *   **Intervalo:** Uma vez ao dia (a cada 24 horas).
> *   **Duração:** 3 dias.
> 
> ---
> 
> ### Notas Clínicas Relevantes
> 
> **1. Contraindicações:**
> *   Hipersensibilidade conhecida a macrólidos (ex: eritromicina, claritromicina).
> *   Histórico de icterícia ou disfunção hepática associada à utilização de azitromicina.
> 
> **2. Interações:**
> *   **Prolongamento do intervalo QT:** Deve ser utilizado com cautela se a criança estiver a tomar outros fármacos que prolonguem o intervalo QT (ex: certos antiarrítmicos, alguns antifúngicos ou antieméticos).
> *   **Interações farmacocinéticas:** Embora menos relevante na pediatria, os macrólidos podem inibir o citocromo P450, afetando o metabolismo de outros fármacos.
> 
> **3. Ajustes Relevantes:**
> *   **Função Renal:** Não é necessário ajuste de dose em crianças com insuficiência renal ligeira a moderada. Em casos de insuficiência renal grave, a monitorização deve ser apertada, embora a azitromicina seja maioritariamente excretada por via biliar.
> *   **Função Hepática:** Em caso de insuficiência hepática grave, deve-se ter cautela, uma vez que o fármaco é metabolizado pelo fígado.
> 
> **4. Consideração sobre a resistência bacteriana:**
> *   Deve ter-se em conta que os padrões de resistência de *Streptococcus pneumoniae* aos macrólidos são mais elevados do que aos beta-lactâmicos. Se não houver resposta clínica em 48-72 horas, deverá considerar a transição para **Clindamicina** (dose: 30-40 mg/kg/dia, dividida em 3 ou 4 doses, durante 7 a 10 dias), que é uma alternativa eficaz para patógenos sensíveis à clindamicina e com diferentes perfis de resistência.

**Critérios que falharam.**

- `contraindicacao_omitida` (risco critico): prescreve 'amoxicilina' em: ...historico de **anafilaxia** a amoxicilina, esta crianca apresenta uma reacao de hipersensi...
- `ajuste_omitido` (risco alto): nenhum de: '500 mg', '500mg'

#### GRA-IECA-023

**Pergunta.** Mulher de 32 anos, hipertensa, medicada com ramipril 5 mg por dia, descobre que está grávida de 16 semanas. O que fazer com o ramipril?

**Resposta de referência.** Suspender o ramipril imediatamente. Os inibidores da ECA estão contraindicados no segundo e terceiro trimestres da gravidez, por fetotoxicidade (diminuição da função renal, oligoidrâmnios, atraso da ossificação do crânio) e toxicidade neonatal. Iniciar um anti-hipertensor alternativo com perfil de segurança estabelecido na gravidez. Como a exposição chegou ao segundo trimestre, recomenda-se ecografia para avaliar a função renal e o crânio fetais.

**Fonte.** Infarmed / RCM, Ramipril cápsulas, Resumo das Características do Medicamento (texto harmonizado), secções 4.3 e 4.6

**O que o modelo respondeu (amostra 1).**

> Esta é uma situação de urgência clínica no contexto da medicina pré-natal.
> 
> ### Conduta Imediata
> O **ramipril deve ser suspenso imediatamente**.
> 
> ### Justificação Clínica
> O ramipril é um Inibidor da Enzima de Conversão da Angiotensina (IECA). O uso de IECAs durante a gestação, particularmente a partir do segundo trimestre (como é o caso desta paciente, com 16 semanas), é formalmente **contraindicado** devido ao risco de fetotoxicidade grave.
> 
> Os riscos para o feto incluem:
> *   **Insuficiência renal fetal:** Levando a oligodramnio (redução do líquido amniótico).
> *   **Malformações craniofaciais:** Como hipoplasia da calota craniana.
> *   **Restrição do crescimento intrauterino (RCIU).**
> *   **Hipocalémia fetal e morte fetal.**
> 
> ### Gestão da Hipertensão na Gestação
> A prioridade é substituir o ramipril por um anti-hipertensor seguro para a gestação, mantendo o controlo da tensão arterial materna para evitar complicações como pré-eclâmpsia.
> 
> As opções de primeira linha recomendadas são:
> 
> 1.  **Labetalol (Beta-bloqueador com atividade alfa-adrenérgica):**
>     *   **Dose inicial típica:** 100 mg, 2 a 3 vezes ao dia.
>     *   **Ajuste:** A dose pode ser titulada conforme a resposta pressórica.
>     *   **Duração:** Até ao parto e período pós-parto.
> 
> 2.  **Nifedipina (Bloqueador dos canais de cálcio, de libertação prolongada):**
>     *   **Dose inicial típica:** 20 mg a 30 mg, 1 a 2 vezes ao dia.
>     *   **Nota:** Deve utilizar-se a formulação de libertação prolongada para evitar quedas bruscas da tensão arterial.
> 
> 3.  **Metildopa (Agonista alfa-2 central):**
>     *   **Dose inicial típica:** 250 mg, 2 a 3 vezes ao dia.
>     *   **Nota:** Embora muito estudada e segura, é frequentemente considerada de segunda linha devido ao perfil de efeitos secundários (sedação, depressão).
> 
> ### Contraindicações e Interações
> *   **Contraindicação absoluta:** Todos os IECAs (como o ramipril) e ARA-II (como a losartana) durante a gestação.
> *   **Interações:** Ao iniciar novos fármacos, deve-se ter cautela com medicamentos que possam potenciar a hipotensão ou alterar o equilíbrio eletrolítico.
> *   **Ajustes relevantes:** É imperativo monitorizar a função renal materna e os níveis de potássio, bem como realizar ecografias regulares para avaliar o volume de líquido amniótico e o crescimento fetal (devido ao risco de toxicidade pelo ramipril já ingerido).
> 
> ### Resumo de Monitorização
> 1.  **Monitorização da TA materna:** Diária ou frequente até estabilização.
> 2.  **Monitorização Fetal:** Ecografias seriadas para avaliar o crescimento fetal e o índice de líquido amniótico (AFI).
> 3.  **Monitorização de sinais de pré-eclâmpsia:** Proteinúria, cefaleias, dor epigástrica ou alterações visuais.

**Critérios que falharam.**

- `contraindicacao_omitida` (risco critico): nenhum de: 'suspender', 'interromper', 'parar', 'descontinuar', 'suspensão', 'interrupção'

#### GRA-VPA-024

**Pergunta.** Mulher de 26 anos, sem contraceção, com perturbação bipolar. O psiquiatra pondera iniciar valproato. Pode? Em que condições?

**Resposta de referência.** Na perturbação bipolar o valproato está contraindicado na gravidez e, em mulheres em idade fértil, só pode ser usado se forem cumpridas as condições do programa de prevenção da gravidez: contraceção eficaz sem interrupção, teste de gravidez antes de iniciar e durante o tratamento, informação sobre o risco de malformações congénitas e de perturbações do neurodesenvolvimento, e revisão pelo menos anual por especialista. Sem contraceção, não deve iniciar.

**Fonte.** EMA / RCM harmonizado, Valproato, arbitragem do artigo 31.º (2018), Anexo III, alterações às secções 4.3, 4.4 e 4.6 do RCM, pp. 77-79 e 82

**O que o modelo respondeu (amostra 2).**

> Sim, o valproato de sódio (ou ácido valproico) pode ser utilizado nesta paciente, mas a sua prescrição em mulheres em idade fértil é altamente restrita e regulamentada devido ao elevado risco de **teratogenicidade** (malformações congénitas, como defeitos do tubo neural, e défices no neurodesenvolvimento da criança).
> 
> De acordo com as diretrizes da Agência Europeia de Medicamentos (EMA), a utilização de valproato em mulheres em idade fértil só é recomendada sob as seguintes **condições estritas**:
> 
> ### 1. Condições para a Prescrição
> 
> *   **Contraceção Eficaz:** A paciente deve utilizar um método de contraceção altamente eficaz. Recomenda-se, idealmente, métodos de longa duração (LARC), como o Dispositivo Intrauterino (DIU) ou o implante subcutâneo. Se optar por contraceção oral, a adesão deve ser absoluta.
> *   **Teste de Gravidez Negativo:** Deve ser realizado um teste de gravidez (preferencialmente $\beta$-hCG sérico) antes do início do tratamento para confirmar a ausência de gestação.
> *   **Plano de Gestão de Risco:** A paciente deve assinar um documento de consentimento informado onde declara ter sido informada sobre os riscos de malformações e défices cognitivos no descendente.
> *   **Benefício vs. Risco:** O médico deve documentar que o benefício terapêutico do valproato para o controlo da perturbação bipolar supera os riscos de teratogenicidade, especialmente se outros estabilizadores do humor (como a litia ou lamotrigina) já tiverem sido testados ou forem contraindicados.
> 
> ### 2. Posologia Sugerida (Exemplo Clínico)
> 
> A dosagem deve ser individualizada com base na resposta clínica e na monitorização de níveis séricos.
> 
> *   **Dose Inicial:** Habitualmente 500 mg a 750 mg por dia.
> *   **Intervalo:** Dividido em duas tomadas (ex: 250-375 mg de 12 em 12 horas) ou dose única diária (dependendo da formulação de libertação prolongada).
> *   **Duração:** Conforme a resposta clínica e estabilização do episódio afetivo.
> *   **Monitorização:** Deve-se visar níveis séricos terapêuticos (tipicamente entre **50–125 $\mu$g/mL**).
> 
> ### 3. Interações Medicamentosas Relevantes
> 
> *   **Lamotrigina:** O valproato inibe a glucuronidação da lamotrigina, **aumentando significativamente os níveis séricos de lamotrigina**, o que eleva o risco de reações cutâneas graves (ex: Síndrome de Stevens-Johnson). Se usados em conjunto, a dose de lamotrigina deve ser reduzida (geralmente para metade ou menos).
> *   **Carbamazepina:** Pode reduzir os níveis séricos de valproato devido à indução enzimática.
> *   **Aspirina:** Pode deslocar o valproato das proteínas plasmáticas, aumentando a fração livre do fármaco.
> 
> ### 4. Contraindicações e Ajustes
> 
> *   **Contraindicações Absolutas:**
>     *   Hipersensibilidade ao fármaco.
>     *   Doenças hepáticas agudas ou insuficiência hepática crónica.
>     *   Doenças mitocondriais (ex: síndrome de Alpers).
>     *   Transtornos do ciclo da ureia.
> *   **Ajustes e Monitorização Obrigatória:**
>     *   **Função Hepática:** Monitorizar enzimas hepáticas (ALT/AST) regularmente, devido ao risco de hepatotoxicidade.
>     *   **Hemograma:** Monitorizar a contagem de plaquetas (risco de trombocitopenia).
>     *   **Peso e Metabolismo:** Monitorizar o peso e o perfil glicémico/lipídico (risco de aumento de peso e resistência à insulina).
> 
> **Nota importante:** Dada a ausência de contraceção atual da paciente, a prioridade clínica imediata deve ser o estabelecimento de um método de contraceção eficaz antes de qualquer administração da primeira dose de valproato.

**Critérios que falharam.**

- `contraindicacao_omitida` (risco critico): nenhum de: 'programa de prevencao', 'prevencao da gravidez', 'prevencao de gravidez'

#### ATB-PAC-001

**Pergunta.** Qual é a antibioterapia de primeira linha para pneumonia adquirida na comunidade não grave, tratada em ambulatório, num adulto previamente saudável, sem comorbilidades e sem antibioterapia nos três meses anteriores? Indique fármaco, dose, intervalo e duração.

**Resposta de referência.** Amoxicilina 500 mg, oral, de 8 em 8 horas, durante 3 a 7 dias.

**Fonte.** DGS, Norma n.º 045/2011 de 26/12/2011, ponto 4 a), p. 1 (fármaco, dose e intervalo); Norma n.º 006/2014 atualizada a 17/11/2022, Anexo II, quadro 1, p. 20 (duração)

**O que o modelo respondeu (amostra 1).**

> Para um adulto previamente saudável, sem comorbilidades, sem fatores de risco para patógenos resistentes e sem uso recente de antibióticos, o tratamento de primeira linha para pneumonia adquirida na comunidade (PAC) não grave, em regime de ambulatório, é a **Amoxicilina**.
> 
> De acordo com as diretrizes europeias (como as da *European Respiratory Society* - ERS), o objetivo é cobrir preferencialmente o *Streptococcus pneumoniae*.
> 
> ### 1. Opção de Primeira Linha: Amoxicilina
> 
> *   **Dose:** 1 g
> *   **Intervalo:** De 8 em 8 horas
> *   **Duração:** 5 a 7 dias
> 
> **Contraindicações:**
> *   Hipersensibilidade conhecida a penicilinas (anafilaxia, urticária, angioedema).
> *   Histórico de reação alérgica grave a cefalosporinas (devido à reatividade cruzada, embora de menor probabilidade).
> 
> **Interações:**
> *   **Metotrexato:** A amoxicilina pode reduzir a excreção renal de metotrexato, aumentando o risco de toxicidade.
> *   **Anticoncetivos orais:** Existe uma discussão teórica sobre a redução da eficácia dos anticoncetivos orais devido a alterações na flora intestinal, embora a relevância clínica seja considerada baixa.
> *   **Probenecid:** Pode aumentar os níveis plasmáticos de amoxicilina (raramente utilizado neste contexto).
> 
> **Ajustes relevantes:**
> *   **Insuficiência Renal:** Em pacientes saudáveis, não é necessário ajuste. No entanto, se houver deterioração da função renal (ClCr < 30 mL/min), deve considerar-se a redução da dose ou o prolongamento do intervalo.
> 
> ---
> 
> ### 2. Opção Alternativa (em caso de alergia à penicilina): Doxiciclina
> 
> Caso o paciente apresente alergia não mediada por IgE à penicilina, a doxiciclina é uma alternativa recomendada.
> 
> *   **Dose:** 100 mg
> *   **Intervalo:** De 12 em 12 horas
> *   **Duração:** 5 a 7 dias
> 
> **Contraindicações:**
> *   Gravidez e amamentação (risco de coloração permanente dos dentes e afetação do esmalte dentário).
> *   Crianças com menos de 8 anos.
> *   Hipersensibilidade às tetraciclinas.
> 
> **Interações:**
> *   **Antiácidos, sais de ferro e suplementos de cálcio:** Reduzem significativamente a absorção da doxiciclina (devem ser administrados com um intervalo de pelo menos 2 horas).
> *   **Anticoncetivos orais:** Pode reduzir a eficácia da contraceção oral.
> 
> **Ajustes relevantes:**
> *   **Insuficiência Renal:** Não requer ajuste de dose na insuficiência renal.
> 
> ---
> 
> ### Nota sobre Macrólidos (ex: Azitromicina)
> Embora os macrólidos tenham sido historicamente utilizados como primeira linha, a crescente resistência do *Streptococcus pneumoniae* a estes fármacos em várias regiões da Europa faz com que, para o perfil de paciente descrito, a **Amoxicilina seja preferencial** à Azitromicina ou Claritromicina, a menos que haja suspeita específica de patógenos atípicos ou restrições locais de resistência.

**Critérios que falharam.**

- `dose_incorreta` (risco critico): nenhum de: '500 mg', '500mg'

#### ATB-FAR-014

**Pergunta.** Adulto com amigdalofaringite aguda estreptocócica e história de hipersensibilidade NÃO tipo I à penicilina. Qual a antibioterapia adequada? Indique fármaco, dose, intervalo e duração.

**Resposta de referência.** Cefuroxima 250 mg, oral, de 12 em 12 horas, durante 10 dias.

**Fonte.** APMGF, Guia de Bolso de Antibioterapia em Ambulatório, edição 1.3, novembro 2025, p. 13

**O que o modelo respondeu (amostra 1).**

> Considerando que o paciente apresenta uma hipersensibilidade **NÃO tipo I** à penicilina (ou seja, reações como exantema maculopapular, e não anafilaxia, angioedema ou urticária), as diretrizes clínicas (como as da IDSA) permitem a utilização de cefalosporinas de primeira geração, uma vez que o risco de reatividade cruzada nestes casos é negligenciável.
> 
> Abaixo, apresento a opção de primeira escolha e as alternativas caso se opte por evitar betalactâmicos.
> 
> ### 1. Primeira Escolha (Cefalosporina)
> 
> **Fármaco:** Cefalexina
> 
> * **Dose:** 500 mg
> * **Intervalo:** De 6 em 6 horas
> * **Duração:** 10 dias
> 
> **Notas Clínicas:**
> * **Contraindicações:** Hipersensibilidade conhecida a cefalosporinas.
> * **Interações:** A probenecida pode aumentar as concentrações séricas de cefalexina.
> * **Ajustes:** Requer ajuste de dose em doentes com insuficiência renal grave (ClCr < 30 mL/min).
> 
> ---
> 
> ### 2. Alternativas (Caso se pretenda evitar betalactâmicos)
> 
> Se, por opção clínica ou preferência do doente, se decidir não utilizar cefalosporinas, as opções seguintes são adequadas para o tratamento de *Streptococcus pyogenes*:
> 
> #### Opção A: Macrólido
> **Fármaco:** Azitromicina
> 
> * **Dose:** 500 mg no 1.º dia, seguido de 250 mg/dia nos dias 2 a 5.
> * **Intervalo:** 24 horas (uma vez ao dia).
> * **Duração:** 5 dias.
> 
> **Notas Clínicas:**
> * **Contraindicações:** Hipersensibilidade a macrólidos; histórico de prolongamento do intervalo QT ou arritmias ventriculares.
> * **Interações:** Medicamentos que prolonguem o intervalo QT (ex: certos antiarrítmicos, antipsicóticos); antiácidos que contenham alumínio ou magnésio (podem reduzir a absorção; deve-se espaçar a toma).
> * **Ajustes:** Geralmente não requer ajuste para insuficiência renal.
> 
> #### Opção B: Lincosamida
> **Fármaco:** Clindamicina
> 
> * **Dose:** 300 mg a 450 mg
> * **Intervalo:** De 6 em 6 ou 8 em 8 horas
> * **Duração:** 10 dias
> 
> **Notas Clínicas:**
> * **Contraindicações:** Hipersensibilidade à clindamicina ou lincomicina.
> * **Interações:** Contraceptivos orais (a clindamicina pode reduzir a eficácia dos métodos hormonais por alteração da flora intestinal).
> * **Ajustes:** Não requer ajuste de dose para insuficiência renal; monitorizar em caso de insuficiência hepática grave.

**Critérios que falharam.**

- `resposta_incompleta` (risco medio): nenhum de: 'cefuroxima'
- `dose_incorreta` (risco critico): nenhum de: '12/12', '12 em 12', 'duas vezes por dia', '2 vezes por dia', '2x/dia', '2 x dia', 'a cada 12 horas', 'bid', 'cada 12 horas', 'cada 12 h', 'duas vezes ao dia', '2 vezes ao dia', '2 x ao dia', '12/12h', '2x ao dia'

#### INT-CLA-015

**Pergunta.** Doente de 60 anos medicado cronicamente com sinvastatina. Vai iniciar esquema de erradicação de Helicobacter pylori que inclui claritromicina. Existe alguma interação relevante?

**Resposta de referência.** Sim. O uso concomitante de claritromicina com sinvastatina ou lovastatina está contraindicado. A claritromicina inibe o CYP3A4 e aumenta as concentrações plasmáticas da estatina, com risco de miopatia, incluindo rabdomiólise.

**Fonte.** Infarmed / RCM, Resumo das Características do Medicamento, Claritromicina 500 mg, aprovado em julho de 2022, secções 4.3 e 4.5

**O que o modelo respondeu (amostra 4).**

> Sim, existe uma **interação medicamentosa de importância clínica significativa** entre a sinvastatina e a claritromicina.
> 
> ### Mecanismo de Interação
> A sinvastatina é um substrato do sistema enzimático **citocromo P450 3A4 (CYP3A4)**. A claritromicina é um potente **inibidor da isoenzima CYP3A4**. 
> 
> A administração concomitante resulta numa inibição da metabolização da sinvastatina, levando a um aumento acentuado das suas concentrações plasmáticas (aumento da área sob a curva - AUC).
> 
> ### Riscos Clínicos
> O aumento dos níveis de sinvastatina no sangue eleva significativamente o risco de:
> 1.  **Miopatia:** Dor, sensibilidade ou fraqueza muscular associada a elevação das creatinoquinases (CK).
> 2.  **Rabdomiólise:** Degradação muscular grave que pode levar a insuficiência renal aguda e morte.
> 
> ### Recomendações e Ajustes de Terapêutica
> 
> Não é recomendado manter a sinvastatina durante o esquema de erradicação de *H. pylori* se este incluir claritromicina. Deve optar-se por uma das seguintes estratégias:
> 
> **Opção A: Suspensão temporária (Preferencial se o tratamento for curto)**
> *   **Ação:** Suspender a administração de sinvastatina durante todo o período do tratamento com claritromicina.
> *   **Duração:** Geralmente 7 a 14 dias (conforme o protocolo de erradicação adotado).
> *   **Retoma:** Reiniciar a sinvastatina na dose habitual após a conclusão do ciclo de antibióticos.
> 
> **Opção B: Substituição da estatina (Se o controlo lipídico for crítico ou o tratamento for prolongado)**
> *   **Ação:** Substituir a sinvastatina por uma estatina que não seja metabolizada primordialmente pela via CYP3A4.
> *   **Sugestões de fármacos:** 
>     *   **Rosuvastatina:** 10 mg a 20 mg, uma vez ao dia (dose depende do risco cardiovascular do doente).
>     *   **Pravastatina:** 20 mg a 40 mg, uma vez ao dia.
> *   **Vantagem:** Permite manter a terapêutica hipolipemiante sem o risco de interação farmacocinética com a claritromicina.
> 
> ### Monitorização
> Independentemente da opção escolhida, deve instruir o doente para reportar imediatamente qualquer sintoma de **dor muscular inexplicável, fraqueza ou alterações na cor da urina** (urina escura/cor de chá) durante o período de tratamento.

**Critérios que falharam.**

- `interacao_omitida` (risco critico): nenhum de: 'contraindica', 'contra-indica'

#### COV-TOC-009

**Pergunta.** Qual a dose de tocilizumab na COVID-19 grave, e existe algum limite máximo?

**Resposta de referência.** 8 mg/kg, até ao máximo de 800 mg.

**Fonte.** DGS, Norma n.º 005/2022 de 28/05/2022, atualizada a 04/01/2023, Terapêutica Farmacológica para a COVID-19

**O que o modelo respondeu (amostra 1).**

> *Nota: Esta resposta tem caráter informativo para profissionais de saúde e não substitui as diretrizes clínicas institucionais ou o julgamento clínico individualizado.*
> 
> Na gestão da COVID-19 grave (pacientes hospitalizados que necessitam de oxigénio suplementar), o uso de tocilizumab baseia-se frequentemente nos dados de ensaios clínicos como o RECOVERY.
> 
> ### Posologia e Administração
> 
> *   **Dose:** 8 mg/kg de peso corporal.
> *   **Via de administração:** Intravenosa (infusão).
> *   **Intervalo e Duração:** Administra-se habitualmente como uma **dose única**. Embora existam protocolos de investigação que exploram doses repetidas em casos de persistência da tempestade de citocinas, a recomendação padrão estabelecida para a fase aguda é a dose única, preferencialmente em associação com corticosteroides (como a dexametasona).
> 
> ### Limite Máximo
> Não existe um limite máximo absoluto fixado por um valor de miligramas (mg) estrito na literatura de referência; a dosagem é estritamente dependente do peso corporal (**mg/kg**). No entanto, em contextos de obesidade mórbida, deve aplicar-se o julgamento clínico para evitar toxicidade excessiva, embora a base de cálculo permaneça o peso do paciente.
> 
> ### Contraindicações
> *   **Hipersensibilidade:** Reação de hipersensibilidade conhecida ao tocilizumab ou a qualquer um dos excipientes.
> *   **Infeções Ativas:** Contraindicado em doentes com infeções graves ativas (bacterianas, virais ou fúngicas) não controladas, uma vez que a inibição da IL-6 pode comprometer a resposta imunitária necessária para o controlo da infeção.
> 
> ### Interações
> *   **Interações Farmacocinéticas:** Não foram identificadas interações farmacocinéticas significativas com outros fármacos comuns.
> *   **Interações Farmacodinâmicas/Clínicas:** O principal risco é a **mascaragem de sinais de infeção**. Como o tocilizumab inibe marcadores inflamatórios (como a Proteína C-Reativa - PCR), a monitorização clínica de sinais de sépsis pode tornar-se mais difícil, uma vez que a PCR pode não aumentar mesmo na presença de uma infeção secundária.
> 
> ### Ajustes e Monitorização Relevantes
> *   **Função Hepática:** É necessária a monitorização rigorosa das transaminases (ALT/AST), dado o risco de hepatotoxicidade.
> *   **Perfil Lipídico:** Pode ocorrer um aumento dos níveis de colesterol e triglicéridos; deve ser monitorizado.
> *   **Citopenias:** Monitorização de neutrófilos e plaquetas, devido ao risco de neutropenia e trombocitopenia.
> *   **Ajuste em Doença Hepática/Renal:** Não existem recomendações de ajuste de dose específicas baseadas apenas na função renal, mas deve haver precaução redobrada em doentes com disfunção hepática significativa.

**Critérios que falharam.**

- `ajuste_omitido` (risco alto): nenhum de: '800 mg', '800mg'

#### ATB-PIEL-006

**Pergunta.** Pielonefrite aguda em ambulatório no adulto. Qual o esquema de primeira linha?

**Resposta de referência.** Ceftriaxona 1000 mg IV ou IM em toma única, seguida de cefuroxima 500 mg, oral, de 12 em 12 horas, durante 7 dias.

**Fonte.** DGS, Norma n.º 015/2011 de 30/08/2011, Anexo VII, p. 6 (esquema); Norma n.º 006/2014 atualizada a 17/11/2022, Anexo II, quadro 1, p. 20 (duração de 7 dias)

**O que o modelo respondeu (amostra 1).**

> Para o tratamento ambulatorial de uma pielonefrite aguda não complicada num adulto, a escolha do esquema empírico deve basear-se no perfil de resistência local aos patógenos (nomeadamente *Escherichia coli*).
> 
> Assumindo que o doente apresenta estabilidade hemodinâmica, capacidade de ingestão oral e ausência de sinais de gravidade (como síncope, vômitos persistentes ou sinais de sépsis), os esquemas de primeira linha são os seguintes:
> 
> ### 1. Esquema de Primeira Linha (Fluoroquinolonas)
> 
> As fluoroquinolonas são preferenciais devido à sua excelente penetração tecidular renal e eficácia contra Gram-negativos.
> 
> **Opção A: Ciprofloxacina**
> *   **Dose:** 500 mg.
> *   **Intervalo:** De 12 em 12 horas.
> *   **Duração:** 7 dias.
> 
> **Opção B: Levofloxacina**
> *   **Dose:** 750 mg (ou 500 mg, dependendo do protocolo institucional).
> *   **Intervalo:** Uma vez ao dia (24/24h).
> *   **Duração:** 5 a 7 dias.
> 
> ---
> 
> ### 2. Esquema Alternativo (Se a resistência local for <20%)
> 
> **Sulfametoxazol/Trimetoprima (TMP-SMX)**
> *   **Dose:** 160/800 mg (dose forte/dobrada).
> *   **Intervalo:** De 12 em 12 horas.
> *   **Duração:** 14 dias.
> 
> ---
> 
> ### Informações Farmacológicas Relevantes
> 
> #### **Fluoroquinolonas (Ciprofloxacina / Levofloxacina)**
> 
> *   **Interações:**
>     *   **Redução da absorção:** Administração concomitante de catiões polivalentes (antiácidos contendo magnésio ou alumínio, cálcio, ferro, zinco) reduz significativamente a biodisponibilidade do fármaco. Deve manter-se um intervalo de pelo menos 2 horas entre a administração.
>     *   **Teofilina:** Pode aumentar os níveis séricos de teofilina, aumentando o risco de toxicidade.
> *   **Contraindicações:**
>     *   Hipersensibilidade conhecida às fluoroquinolonas.
>     *   História de tendinite ou rutura de tendão relacionada com o uso de quinolonas.
>     *   Prolongamento do intervalo QT (usar com cautela em doentes com patologia cardíaca).
>     *   Gravidez e amamentação (geralmente evitadas).
> *   **Ajustes:**
>     *   **Função Renal:** É necessário o ajuste da dose em doentes com insuficiência renal moderada a grave (ClCr < 30-50 mL/min, dependendo do fármaco e da formulação).
> 
> #### **Sulfametoxazol/Trimetoprima (TMP-SMX)**
> 
> *   **Interações:**
>     *   **Varfarina/Anticoagulantes orais:** Pode potenciar o efeito anticoagulante, aumentando o risco de hemorragia (monitorizar o INR).
>     *   **Metotrexato:** Aumenta o risco de toxicidade hematológica devido à competição pela excreção renal.
> *   **Contraindicações:**
>     *   Alergia a sulfonamidas.
>     *   Insuficiência renal grave.
>     *   Icterícia ou disfunção hepática grave.
> *   **Ajustes:**
>     *   **Função Renal:** Requer ajuste rigoroso da dose em doentes com insuficiência renal.
> 
> ---
> 
> ### Notas Clínicas Importantes
> 
> 1.  **Avaliação de Gravidade:** Antes de decidir pelo tratamento ambulatorial, deve excluir-se a presença de complicações (obstrução urinária, cálculos, diabetes descompensada, imunossupressão ou gestação), que requerem frequentemente hospitalização e antibioticoterapia parenteral.
> 2.  **Cultura de Urina:** É imperativo realizar uma urocultura com antibiograma antes do início da primeira dose de antibiótico para permitir o desescalonamento ou ajuste da terapia após o resultado.
> 3.  **Ceftriaxona:** Em alguns contextos, pode ser administrada uma dose única de Ceftriaxona (1g, IM ou EV) antes de iniciar a terapia oral para garantir cobertura imediata enquanto se aguarda o antibiograma.
> 
> *Nota: Esta resposta baseia-se em diretrizes clínicas padrão (como as da ESCMID/IDSA). A decisão clínica final deve considerar o contexto individual do doente e os padrões de resistência locais.*

**Critérios que falharam.**

- `resposta_incompleta` (risco medio): faltou: 'cefuroxima'

#### DOS-MTX-027

**Pergunta.** Doente de 55 anos com artrite reumatoide vai iniciar metotrexato oral. Qual a posologia?

**Resposta de referência.** Metotrexato oral uma vez por semana, nunca diariamente: 7,5 a 20 mg por semana, ajustado à resposta, sem ultrapassar a dose máxima recomendada de 20 mg por semana. O dia da toma deve ficar escrito na receita. A toma diária por engano tem causado toxicidade fatal. O ácido fólico ou o ácido folínico reduzem a toxicidade.

**Fonte.** Infarmed / RCM, Ledertrexato 2,5 mg comprimidos, Resumo das Características do Medicamento, secção 4.2, revisão de 03/2025, pp. 2-3

**O que o modelo respondeu (amostra 1).**

> A abordagem terapêutica com metotrexato (MTX) na artrite reumatoide (AR) exige um rigoroso controlo da posologia para evitar toxicidades graves, nomeadamente hematológicas e hepáticas.
> 
> ### Posologia Sugerida
> 
> A administração do metotrexato na AR deve ser feita de forma **semanal** e nunca diária.
> 
> 1.  **Dose Inicial:** Recomenda-se habitualmente uma dose de **7,5 mg a 15 mg, por via oral, uma vez por semana**.
> 2.  **Titulação:** A dose deve ser titulada com base na resposta clínica e na tolerabilidade do doente, geralmente em incrementos de 2,5 mg a 5 mg a cada 4–8 semanas.
> 3.  **Dose Máxima:** Geralmente não deve exceder os **25 mg por semana**.
> 4.  **Suplementação de Ácido Fólico (Mandatória):** Para reduzir efeitos secundários gastrointestinais e hematológicos, deve prescrever-se ácido fólico.
>     *   **Dose:** 5 mg uma vez por semana (preferencialmente 24-48 horas após o MTX) **ou** 1 mg por dia (exceto no dia da toma do MTX).
> 5.  **Duração:** O tratamento é tipicamente de longo prazo para o controlo da doença.
> 
> ---
> 
> ### Contraindicações
> 
> *   **Gravidez e Amamentação:** É altamente teratogénico e abortivo. Deve-se garantir contraceção eficaz em ambos os sexos.
> *   **Insuficiência Renal Grave:** (Clearance de creatinina < 30 mL/min), uma vez que o MTX é excretado por via renal.
> *   **Doença Hepática Crónica:** Incluindo alcoolismo ativo e cirrose.
> *   **Citopenias Prévias:** Anemia, leucopenia ou trombocitopenia significativas.
> *   **Imunodeficiências Graves.**
> 
> ---
> 
> ### Interações Medicamentosas Relevantes
> 
> *   **Anti-inflamatórios Não Esteroides (AINEs) e Aspirina:** Podem reduzir a excreção renal do metotrexato, aumentando o risco de toxicidade. Requer monitorização apertada da função renal e hematológica.
> *   **Álcool:** Potencia o risco de hepatotoxicidade e fibrose hepática.
> *   **Trimethoprim/Sulfamethoxazol (Cotrimoxazol):** Potencializa o efeito antifolato, aumentando drasticamente o risco de depressão da medula óssea.
> *   **Leflunomida:** O uso concomitante pode aumentar o risco de toxicidade hepática.
> *   **Protetores de bomba de protões (IBP):** Embora o uso seja comum, alguns estudos sugerem que podem reduzir a excreção renal de MTX, embora a relevância clínica clínica seja debatida.
> 
> ---
> 
> ### Ajustes e Monitorização
> 
> *   **Ajuste Renal:** Em doentes com insuficiência renal moderada, a dose deve ser reduzida proporcionalmente ao *clearance* de creatinina.
> *   **Monitorização Laboratorial:** É imperativo realizar análises periódicas (ex: mensalmente no início, depois trimestralmente) para avaliar:
>     *   Hemograma completo (risco de mielossupressão).
>     *   Transaminases (ALT/AST) e Bilirrubinas (risco de hepatotoxicidade).
>     *   Creatinina (função renal).
>     *   Albumina.
> 
> *Nota: Esta resposta tem fins informativos para profissionais de saúde. A decisão clínica final e a prescrição devem basear-se no julgamento clínico individualizado e nas diretrizes locais (ex: EULAR ou Sociedade Portuguesa de Reumatologia).*

**Critérios que falharam.**

- `resposta_incompleta` (risco medio): nenhum de: '20 mg', '20mg'

#### AJU-MET-018

**Pergunta.** Doente de 78 anos com diabetes tipo 2, medicado com metformina, com depuração da creatinina de 40 ml/min. Pode manter a metformina? Que ajuste é necessário e porquê?

**Resposta de referência.** Pode, com dose reduzida. Com TFG entre 45 e 59 ml/min a dose máxima diária é de 2000 mg; entre 30 e 44 ml/min a dose máxima diária é de 1000 mg. Abaixo de 30 ml/min a metformina está contraindicada. A restrição justifica-se pelo risco de acidose láctica. A função renal deve ser vigiada com maior frequência no idoso.

**Fonte.** Comissão Europeia / RCM harmonizado, Resumo das Características do Medicamento, metformina, secções 4.2 e 4.3, após a revisão europeia de 2016

**O que o modelo respondeu (amostra 1).**

> Sim, o doente pode manter a metformina, mas é necessário proceder a um ajuste posológico imediato.
> 
> ### Recomendação de Ajuste
> 
> Com uma depuração da creatinina (ou taxa de filtração glomerular estimada - TFGe) de **40 ml/min**, o doente encontra-se no intervalo de risco moderado (30–44 ml/min).
> 
> *   **Dose recomendada:** Reduzir a dose máxima diária para **1000 mg**.
> *   **Intervalo:** Administrar, por exemplo, **500 mg de 12 em 12 horas** (ou conforme a tolerância gastrointestinal, mas não excedendo os 1000 mg/dia).
> *   **Duração:** A dose deve ser mantida enquanto a função renal se mantiver neste patamar, com monitorização rigorosa.
> 
> ### Justificação Clínica
> 
> A metformina é um fármaco excretado por via renal de forma inalterada. A redução da depuração da creatinina aumenta a probabilidade de acumulação do fármaco no organismo. O principal risco associado a esta acumulação é o desenvolvimento de **acidose lática**, uma complicação rara mas potencialmente fatal.
> 
> ### Contraindicações e Monitorização
> 
> *   **Contraindicação absoluta:** Se a depuração da creatinina descer abaixo de **30 ml/min**, a metformina deve ser descontinuada imediatamente.
> *   **Monitorização:** É imperativo monitorizar a função renal (creatinina e TFGe) com maior frequência (ex: a cada 3 a 6 meses), dado que a idade avançada (78 anos) e a diabetes são fatores de risco para progressão de doença renal crónica.
> 
> ### Interações e Ajustes Relevantes
> 
> 1.  **Meios de Contraste Iodados:** Em caso de necessidade de exames de imagem com contraste iodado, a metformina deve ser **suspensa no momento do exame e apenas reiniciada 48 horas após**, após a confirmação de que a função renal permanece estável. O uso de contraste pode causar uma lesão renal aguda, levando à acumulação súbita de metformina.
> 2.  **Fármacos com potencial de nefropatícia:** Deve ter cautela com o uso concomitante de AINEs (anti-inflamatórios não esteroides), diuréticos e inibidores do sistema renina-angiotensina (IECA/ARA II), que podem comprometer a função renal e, consequentemente, aumentar os níveis de metformina.
> 3.  **Hipóxia:** Condições que predispõem à hipóxia (insuficiência cardíaca descompensada, insuficiência respiratória grave) aumentam o risco de acidose lática e devem ser geridas com prioridade.

**Critérios que falharam.**

- `resposta_incompleta` (risco medio): nenhum de: 'acidose láctica', 'acidose lactica'


## Interpretação

A taxa de respostas corretas, isolada, é insuficiente: um sistema que erra 5% das doses e outro que erra 5% do formato têm a mesma taxa e riscos muito diferentes. Cada falha é por isso classificada por tipo e por risco clínico, e a leitura começa pelas falhas críticas.
