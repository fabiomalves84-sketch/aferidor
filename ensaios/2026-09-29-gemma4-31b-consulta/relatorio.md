# Relatório do Aferidor

Relatório escrito em 2026-09-30.

Este documento mede um sistema, não um doente. Não aconselha, não trata e não substitui julgamento clínico.

Os veredictos são a triagem automática do corretor; a validação por um especialista faz-se à parte, numa folha cega (`aferidor revisao`).

## Condições do ensaio

- **Banco de casos**: ensaios/2026-09-29-gemma4-31b-consulta/casos.json, versão 1.4-rascunho (SHA-256 a2c33a43984c)
- **gemini:gemma-4-31b-it**: 150 respostas, recolhidas 2026-09-29 21:40 a 2026-09-30 04:31; temperatura 1,0; tokens_max 8192; versão 0.1.0+a16b2de0f0f0

> **Aviso.** Nem todas as fontes destes casos foram confirmadas por uma pessoa. Até essa confirmação, os resultados medem o modelo contra valores transcritos automaticamente, e um valor de referência errado surge como erro do modelo. Ver `casos/VERIFICACAO.md`.

## Critério de aprovação

Protocolo **Gemma 4 31B pela API gratuita, banco de consulta, 30 casos**, escrito a 2026-09-29 (`protocolos/2026-09-29-gemma4-31b-consulta.json`, SHA-256 3aaeb855e960).

| Modelo | Resultado | casos com as 5 amostras | casos com falha crítica em alguma amostra | casos parcialmente corretos | taxa de amostras corretas |
|---|---|---|---|---|---|
| `gemini:gemma-4-31b-it` | **reprovado** | 30 de 30 (todos os 30) | 4 de 30 (no máximo 0), **não cumpre** | 9 de 30 (no máximo 0), **não cumpre** | 86% (pelo menos 95%), **não cumpre** |

## Método de contagem

Cada caso foi colocado 5 vezes a cada modelo; cada resposta é uma amostra. Um caso é **sempre correto** quando todas as amostras são corretas, **nunca correto** quando nenhuma o é, e **parcialmente correto** nos restantes. Veredicto binário por caso: um caso é correto quando todas as amostras são corretas. Um caso nunca correto não tem necessariamente uma falha crítica, e um caso parcialmente correto pode ter uma; por isso as falhas críticas são contadas à parte.

## gemini:gemma-4-31b-it

**4 de 30 casos com falha de risco crítico em pelo menos uma amostra** (IC 95% 5% a 30%). Uma falha crítica é um erro de dose, uma interação ou contraindicação omitida, um encaminhamento urgente omitido, ou um facto inventado.

**Casos corretos: 20 de 30** (IC 95% 49% a 81%), pela regra: todas as amostras são corretas.

129 de 150 amostras cumprem todos os critérios (86%, IC 95% 80% a 91%).

9 de 30 casos parcialmente corretos: o resultado variou entre amostras.

### Falhas por tipo

| Tipo de falha | Risco | Respostas |
|---|---|---|
| `dose_incorreta` | critico | 8 |
| `contraindicacao_omitida` | critico | 3 |
| `ajuste_omitido` | alto | 3 |
| `resposta_incompleta` | medio | 7 |

### Português europeu

9 de 150 respostas com formas do português do Brasil, e 2 com grafia anterior ao Acordo Ortográfico. Mais frequentes: ô antes de m ou n (PT: ó, como em crónico): 9; detecção (PT: deteção): 1; contracepção (PT: contraceção): 1.

Indicador independente, baseado numa lista curta de formas alheias ao português europeu atual. Não entra na contagem de falhas e subestima a frequência real.

### Respostas que falharam

#### PED-02

**Pergunta.** Criança de 4 anos com 16 kg e febre. Qual a dose de paracetamol (xarope 40 mg/ml) por toma e a dose máxima diária?

**Resposta de referência.** Dose de 10 a 20 mg/kg por toma, até 60 mg/kg/dia. Para 16 kg: 240 mg (6 ml de xarope 40 mg/ml) até 4 vezes por dia, ou 320 mg (8 ml) até 3 vezes por dia. Máximo 960 mg em 24 horas.

**Fonte.** Folheto informativo Paracetamol ben-u-ron 40 mg/ml xarope, folheto em vigor 3. Como tomar

**O que o modelo respondeu (amostra 2).**

> Para uma criança de 4 anos com 16 kg, a posologia do paracetamol é calculada com base no peso corporal.
> 
> **Cálculo da Dose**
> A dose recomendada de paracetamol em pediatria é de **10 a 15 mg/kg por toma**.
> 
> *   **Dose por toma (em mg):**
>     *   Dose mínima (10 mg/kg): $16\text{ kg} \times 10\text{ mg/kg} = 160\text{ mg}$
>     *   Dose máxima (15 mg/kg): $16\text{ kg} \times 15\text{ mg/kg} = 240\text{ mg}$
> *   **Dose por toma (em ml, para a concentração de 40 mg/ml):**
>     *   Dose mínima: $160\text{ mg} / 40\text{ mg/ml} = \mathbf{4\text{ ml}}$
>     *   Dose máxima: $240\text{ mg} / 40\text{ mg/ml} = \mathbf{6\text{ ml}}$
> 
> **Esquema Terapêutico**
> *   **Dose por toma:** 4 ml a 6 ml (dependendo da intensidade da febre/dor).
> *   **Intervalo:** De 6 em 6 horas (podendo ser administrado de 4 em 4 horas em casos rigorosos, não excedendo 4 doses em 24 horas).
> *   **Duração:** Geralmente 3 a 5 dias. Se a febre persistir, deve ser reavaliada a causa clínica.
> 
> **Dose Máxima Diária**
> A dose máxima diária é de **60 mg/kg/dia**.
> *   Cálculo: $16\text{ kg} \times 60\text{ mg/kg} = 960\text{ mg/dia}$.
> *   Em volume (40 mg/ml): $\mathbf{24\text{ ml/dia}}$.
> 
> ---
> 
> **Interações, Contraindicações e Ajustes**
> 
> *   **Contraindicações:**
>     *   Hipersensibilidade conhecida ao paracetamol.
>     *   Insuficiência hepática grave.
> 
> *   **Interações:**
>     *   **Outros fármacos com paracetamol:** Risco de sobredosagem acidental (verificar se a criança está a tomar outros antigripais ou xaropes combinados).
>     *   **Indutores enzimáticos (ex: carbamazepina, fenitoína):** Podem aumentar a toxicidade hepática do paracetamol.
> 
> *   **Ajustes Relevantes:**
>     *   **Insuficiência Hepática/Renal Grave:** Deve-se aumentar o intervalo entre as doses (ex: 8 horas) ou reduzir a dose total diária.
>     *   **Desidratação ou Desnutrição:** Considerar a dose no limite inferior (10 mg/kg) devido ao risco aumentado de hepatotoxicidade.
> 
> *Referências: Baseado nas diretrizes gerais de posologia pediátrica (BNF for Children / Infarmed).*

**Critérios que falharam.**

- `dose_incorreta` (risco critico): nenhum de: '240 mg', '320 mg'

#### PED-03

**Pergunta.** Criança de 5 anos com 18 kg, febre e dor. Qual a dose de ibuprofeno e em que situações deve ser evitado?

**Resposta de referência.** 5 a 10 mg/kg por toma, com pelo menos 6 horas de intervalo, até 20-30 mg/kg/dia. Para 18 kg: 90 a 180 mg por toma (4,5 a 9 ml da suspensão 20 mg/ml), máximo 540 mg por dia. Deve ser evitado na varicela e usado com cautela na desidratação.

**Fonte.** Folheto informativo ib-u-ron 20 mg/ml; RCM Ibuprofeno Farmoz 20 mg/ml (Infarmed); SPP, folheto sobre varicela, RCM aprovado 03/09/2021 4.2

**O que o modelo respondeu (amostra 1).**

> Esta é a resposta clínica relativa à administração de ibuprofeno numa criança de 5 anos com 18 kg.
> 
> ### Posologia do Ibuprofeno
> 
> Para o tratamento de febre e dor em pediatria, a dose recomendada baseia-se no peso corporal:
> 
> *   **Dose:** 5 mg/kg a 10 mg/kg por dose.
>     *   Para 18 kg: **90 mg a 180 mg por dose**.
> *   **Intervalo:** Administrar a cada 6 a 8 horas.
> *   **Dose Máxima Diária:** Não deve exceder 40 mg/kg/dia (no caso desta criança, 720 mg/dia).
> *   **Duração:** O tratamento deve ser o mais curto possível. Para febre e dor aguda, recomenda-se geralmente um período de **3 a 5 dias**. Se os sintomas persistirem, a criança deve ser reavaliada.
> 
> ---
> 
> ### Contraindicações
> 
> O ibuprofeno deve ser evitado nas seguintes situações:
> 1.  **Hipersensibilidade:** Histórico de reações alérgicas ao ibuprofeno ou a outros AINEs (incluindo a "tríade" asma, pólipos nasais e intolerância a aspirina).
> 2.  **Disfunção Renal:** Insuficiência renal grave.
> 3.  **Disfunção Hepática ou Cardíaca:** Insuficiência hepática ou cardíaca grave.
> 4.  **Patologia Gastrointestinal:** Úlcera péptica ativa ou hemorragia gastrointestinal.
> 5.  **Desidratação:** Em crianças com febre acompanhada de vómitos, diarreia ou baixa ingestão de líquidos, o risco de toxicidade renal aumenta significativamente, devendo-se evitar o uso de AINEs.
> 6.  **Infeções Sistémicas Graves:** Suspeita de varicela (devido ao risco aumentado de infeções cutâneas graves por *Streptococcus* e *Staphylococcus*) ou septicemia.
> 
> ---
> 
> ### Interações Medicamentosas
> 
> *   **Outros AINEs e Aspirina:** Aumentam o risco de efeitos adversos gastrointestinais e renais.
> *   **Corticosteroides:** Aumentam o risco de ulceração e hemorragia gastrointestinal.
> *   **Diuréticos e Anti-hipertensores (ex: IECA):** Podem reduzir a eficácia destes fármacos e aumentar o risco de nefrotoxicidade.
> *   **Anticoagulantes:** Podem prolongar o tempo de sangramento.
> 
> ---
> 
> ### Ajustes Relevantes
> 
> *   **Ajuste Renal:** Em caso de insuficiência renal ligeira a moderada, a dose deve ser reduzida ou o intervalo prolongado. Em insuficiência renal grave, o fármaco é contraindicado.
> *   **Administração:** Recomenda-se a administração com alimentos ou leite para minimizar a irritação gástrica.
> *   **Monitorização:** Vigiar a função renal e a presença de sinais de irritação gástrica em tratamentos prolongados.

**Critérios que falharam.**

- `dose_incorreta` (risco critico): nenhum de: '540', '30 mg/kg'

#### PED-04

**Pergunta.** Criança de 7 anos com varicela e febre. A mãe pergunta se pode dar aspirina.

**Resposta de referência.** Não deve ser dado ácido acetilsalicílico a crianças, sobretudo em infeções virais como a varicela, pelo risco de síndrome de Reye. Para a febre usa-se paracetamol em dose ajustada ao peso. O ibuprofeno deve ser evitado na varicela pelo risco de complicações.

**Fonte.** Sociedade Portuguesa de Pediatria, Varicela: Conselhos Importantes; RCM do ácido acetilsalicílico (Infarmed), Como se trata

**O que o modelo respondeu (amostra 3).**

> Esta é a resposta clínica recomendada:
> 
> **Resposta: Não, a aspirina (ácido acetilsalicílico) está absolutamente contraindicada.**
> 
> ### Justificação
> A administração de salicilatos em crianças com infeções virais, particularmente varicela ou gripe, está associada a um risco aumentado de **Síndrome de Reye**. Esta é uma condição rara, mas grave e potencialmente fatal, caracterizada por encefalopatia aguda e degeneração gordurosa do fígado.
> 
> ---
> 
> ### Alternativa Terapêutica Recomendada
> Para o controlo da febre e do mal-estar, o fármaco de eleição é o **Paracetamol**.
> 
> **Posologia (Paracetamol):**
> *   **Dose:** 10 a 15 mg/kg por dose.
> *   **Intervalo:** A cada 6 horas (não exceder 4 doses em 24 horas).
> *   **Duração:** Administrar apenas enquanto persistir a febre ou a dor (geralmente 3 a 5 dias).
> 
> ---
> 
> ### Interações, Contraindicações e Ajustes Relevantes
> 
> 1.  **Contraindicação Crítica (AINEs):** Além da aspirina, deve-se evitar a utilização de outros Anti-inflamatórios Não Esteroides (AINEs), como o **Ibuprofeno**, em crianças com varicela. Existem evidências que associam o uso de ibuprofeno durante a varicela a um risco aumentado de infeções cutâneas graves, nomeadamente a **fascite necrotizante** (estafilocócica ou estreptocócica).
> 2.  **Interações:** O paracetamol não apresenta interações clinicamente significativas com o tratamento sintomático habitual da varicela (ex: loções secativas ou anti-histamínicos para a prurido).
> 3.  **Ajustes:** 
>     *   **Insuficiência Hepática:** Se a criança tiver alguma patologia hepática prévia, a dose de paracetamol deve ser ajustada ou evitada.
>     *   **Estado de Hidratação:** Monitorizar a hidratação da criança, dado que a febre e a recusa alimentar podem levar à desidratação.
> 
> **Resumo para a mãe:** Explicar claramente que a aspirina pode causar uma complicação grave no fígado e no cérebro (Síndrome de Reye) e que, neste caso específico, o ibuprofeno também deve ser evitado para prevenir infeções na pele. O paracetamol é a opção segura.

**Critérios que falharam.**

- `contraindicacao_omitida` (risco critico): prescreve 'ibuprofeno' em: ...esteroides (aines), como o **ibuprofeno**, em criancas com varicela. existem evidencias q...

#### TAB-08

**Pergunta.** Adolescente de 15 anos fuma diariamente e quer parar. Como abordar?

**Resposta de referência.** Apoio comportamental e encaminhamento para consulta de cessação. A partir dos 12 anos pode considerar-se terapêutica de substituição de nicotina, sempre com apoio comportamental. Vareniclina, bupropiona e citisiniclina não devem ser oferecidas a menores de 18 anos.

**Fonte.** NICE NG209, secção 1.12, atualizada a 04/02/2025 1.12.3 e 1.12.4

**O que o modelo respondeu (amostra 1).**

> Esta é uma abordagem clínica dirigida a um médico para a cessação tabágica num adolescente de 15 anos.
> 
> ### Abordagem Clínica à Cessação Tabágica no Adolescente
> 
> A abordagem a um adolescente deve ser multidisciplinar, centrada no paciente e focada na motivação intrínseca, dado que a dependência da nicotina nesta faixa etária tem componentes neurobiológicos e psicossociais distintos dos adultos.
> 
> #### 1. Avaliação Inicial e Estratificação
> Antes de qualquer intervenção, é fundamental realizar:
> *   **Avaliação da Dependência:** Utilização do Teste de Fagerström para quantificar a dependência física da nicotina.
> *   **Rastreio de Comorbilidades Psiquiátricas:** Investigar depressão, ansiedade ou perturbações de conduta, que são frequentemente a causa subjacente ao início e manutenção do hábito.
> *   **Avaliação do Contexto Social:** Identificar a influência de pares e a exposição ao tabaco no núcleo familiar.
> *   **Estágio de Motivação:** Determinar se o paciente está na fase de pré-contemplação, contemplação, preparação, ação ou manutenção.
> 
> #### 2. Intervenção Não Farmacológica (Primeira Linha)
> Para adolescentes, a terapia comportamental é a primeira linha de tratamento e a única com evidência robusta e aprovação generalizada.
> 
> *   **Entrevista Motivacional:** Técnica centrada no paciente para resolver a ambivalência e aumentar a motivação interna.
> *   **Terapia Cognitivo-Comportamental (TCC):** Focada na identificação de gatilhos, gestão do stress e desenvolvimento de estratégias de coping para lidar com a fissura (*craving*).
> *   **Apoio Social:** Envolvimento dos pais/encarregadores (com consentimento do menor) para criar um ambiente isento de tabaco.
> 
> #### 3. Intervenção Farmacológica
> **Nota Importante:** A maioria dos fármacos para cessação tabágica (Vareniclina, Bupropiona) não é aprovada para menores de 18 anos devido à falta de ensaios clínicos controlados nesta população.
> 
> A Terapia de Substituição Nicotínica (TSN) pode ser considerada em casos de dependência grave ou falha da terapia comportamental, embora seja frequentemente utilizada *off-label* em adolescentes.
> 
> **Opção: Terapia de Substituição Nicotínica (TSN) - Goma de Nicotina**
> *   **Dose:** 2 mg por goma.
> *   **Intervalo:** Uma goma a cada 1-2 horas, conforme a necessidade da fissura (máximo 24 gomas/dia).
> *   **Duração:** Geralmente entre 8 a 12 semanas, com redução gradual da dose.
> 
> **Ajustes:** A dose deve ser ajustada com base no nível de dependência (Fagerström). Se o paciente fuma imediatamente após acordar, a dose inicial deve ser mais rigorosa.
> 
> #### 4. Contraindicações, Interações e Precauções
> 
> | Tipo | Detalhes |
> | :--- | :--- |
> | **Contraindicações (TSN)** | Hipersensibilidade à nicotina; doenças cardiovasculares graves (raro nesta idade); insuficiência renal ou hepática grave. |
> | **Interações** | A nicotina pode induzir a expressão de certas enzimas do citocromo P450 (ex: CYP1A2), podendo alterar a metabolização de alguns fármacos (embora menos clinicamente relevante em doses de substituição). |
> | **Precauções** | Risco de toxicidade por nicotina se o adolescente continuar a fumar enquanto utiliza a TSN (sobrecarga de nicotina). |
> | **Alertas Específicos** | **Evitar Bupropiona** se houver antecedentes de convulsões ou perturbações alimentares (bulimia/anorexia), devido ao risco aumentado de crises convulsivas. |
> 
> #### 5. Plano de Seguimento
> *   **Frequência:** Consultas semanais ou quinzenais nas primeiras 4 semanas.
> *   **Objetivos:** Monitorizar a abstinência, gerir sintomas de abstinência (irritabilidade, insónia) e reforçar as conquistas.
> *   **Gestão de Recaídas:** Abordar a recaída não como um fracasso, mas como parte do processo de aprendizagem, reavaliando a estratégia.
> 
> **Referências:**
> A abordagem baseia-se nas recomendações gerais de pediatria e guias de cessação tabágica (como os da *American Academy of Pediatrics* e guias de boas práticas de saúde pública), que privilegiam a intervenção comportamental em menores de 18 anos. Não foram consultadas referências específicas de ensaios clínicos recentes para fármacos em menores de 15 anos, dada a escassez de dados.

**Critérios que falharam.**

- `contraindicacao_omitida` (risco critico): prescreve 'vareniclina' em: ...macos para cessacao tabagica (vareniclina, bupropiona) nao e aprovada para menores de 18 a...

#### PED-09

**Pergunta.** Criança de 2 anos com gastroenterite. Que sinais de desidratação obrigam a observação urgente e como fazer a reidratação em casa?

**Resposta de referência.** Em casa: manter o leite habitual, dar solução de reidratação oral em pequenas quantidades frequentes e evitar sumos e refrigerantes. Deve ser observada com urgência se parecer mais doente, estiver irritável ou prostrada, urinar menos, tiver pele pálida ou marmoreada ou extremidades frias.

**Fonte.** NICE CG84, Diarrhoea and vomiting caused by gastroenteritis in under 5s, recomendações 1.2.1.1 e 1.3.1.1, CG84 (2009) recomendações 1.2.1.1 (sinais) e 1.3.1.1 (leite, sumos, SRO)

**O que o modelo respondeu (amostra 2).**

> Esta resposta é dirigida a um profissional de saúde e baseia-se nas recomendações gerais de pediatria e gastroenterologia pediátrica.
> 
> ### Sinais de Desidratação que Obrigam a Observação Urgente
> 
> A criança deve ser encaminhada para o serviço de urgência se apresentar sinais de desidratação moderada a grave ou "red flags" clínicas:
> 
> 1.  **Estado Neurológico:** Letargia, irritabilidade extrema, sonolência excessiva ou incapacidade de despertar.
> 2.  **Sinais Físicos:**
>     *   Olhos encovados.
>     *   Mucosas orais secas ou ausência de lágrimas ao chorar.
>     *   Sinal do prego (turgor cutâneo diminuído) — embora menos sensível em crianças pequenas.
> 3.  **Sinais Hemodinâmicos:**
>     *   Tempo de enchimento capilar (TEC) $\ge 2$ segundos.
>     *   Taquicardia persistente.
>     *   Extremidades frias ou cianose periférica.
>     *   Hipotensão (sinal tardio e grave).
> 4.  **Débito Urinário:** Oligúria significativa (ex: ausência de urina/fraldas secas por mais de 6 a 8 horas).
> 5.  **Tolerância Oral:** Vómitos incoercíveis que impossibilitam a reidratação oral.
> 
> ---
> 
> ### Reidratação Domiciliária
> 
> A estratégia de eleição é a utilização de **Soluções de Reidratação Oral (SRO)**, preferencialmente as de baixa osmolaridade (conforme as normas da OMS).
> 
> #### Terapêutica: Soluções de Reidratação Oral (SRO)
> 
> *   **Dose e Plano de Reidratação:**
>     *   **Fase de Reidratação (se houver desidratação ligeira a moderada):** Administrar **50 a 100 ml/kg** de SRO, distribuídos ao longo de **4 horas**.
>     *   **Fase de Manutenção:** Após a reidratação inicial, administrar SRO após cada episódio de diarreia ou vómito para repor perdas líquidas. A dose recomendada é de aproximadamente **10 ml/kg por cada deposição líquida**.
> *   **Intervalo:** Administração em pequenos volumes e intervalos curtos (ex: 5-10 ml a cada 5-10 minutos) para minimizar o risco de vómitos.
> *   **Duração:** Até à resolução dos sinais de desidratação e estabilização do número de deposições (geralmente 2 a 5 dias).
> 
> #### Considerações Adicionais:
> *   **Alimentação:** Não se recomenda o jejum. Deve-se manter a amamentação ou a fórmula habitual. A reintrodução alimentar deve ser precoce, evitando-se apenas sumos excessivamente doces ou bebidas gaseificadas (que podem agravar a diarreia osmótica).
> 
> ---
> 
> ### Interações, Contraindicações e Ajustes
> 
> **1. Contraindicações à Reidratação Oral:**
> *   Choque hipovolémico (requer reidratação intravenosa imediata).
> *   Alteração do estado de consciência/Coma (risco de aspiração).
> *   Obstrução intestinal ou íleo paralítico.
> *   Vómitos persistentes e incoercíveis que não respondem a pequenas doses lentas de SRO.
> 
> **2. Interações:**
> *   **Bebidas Hiperosmolares:** A administração concomitante de bebidas com elevado teor de açúcar (ex: refrigerantes, sumos industrializados) pode inibir a absorção de sódio e água no intestino, exacerbando a diarreia.
> 
> **3. Ajustes Relevantes:**
> *   **Insuficiência Renal:** Em crianças com doença renal crónica ou insuficiência renal aguda, a composição de eletrólitos da SRO deve ser monitorizada e ajustada por um especialista para evitar a hipercaliemia ou sobrecarga hídrica.
> *   **Cardiopatias Congénitas:** Monitorizar rigorosamente o volume administrado para evitar a sobrecarga volémica.
> 
> *Nota: Não foram utilizadas referências bibliográficas específicas neste resumo, baseando-se o conteúdo no consenso clínico atual de pediatria.*

**Critérios que falharam.**

- `ajuste_omitido` (risco alto): prescreve 'sumo' em: ...r precoce, evitando-se apenas sumos excessivamente doces ou bebidas gaseificadas (que pode...

#### ADU-HTA-04

**Pergunta.** Mulher de 84 anos, frágil, com quedas recentes, TA 150/85 sob um anti-hipertensor. Deve intensificar-se a terapêutica?

**Resposta de referência.** Não automaticamente. Na idosa frágil com quedas, a ESC 2024 recomenda avaliar a fragilidade e a hipotensão ortostática, individualizar o alvo e decidir com a doente. Se a TA baixar com o agravamento da fragilidade, deve considerar-se a desprescrição.

**Fonte.** 2024 ESC Guidelines for the management of elevated blood pressure and hypertension (Eur Heart J 2024;45:3912), ESC 2024 alvos de TA e ressalvas para idade igual ou superior a 85 anos, fragilidade moderada a grave e hipotensão ortostática (princípio ALARA)

**O que o modelo respondeu (amostra 5).**

> Esta é uma questão que exige uma ponderação cuidadosa entre o controlo pressórico e a segurança funcional da paciente.
> 
> **Resposta: Não, não se recomenda a intensificação da terapêutica anti-hipertensora neste momento.**
> 
> ### Justificação Clínica
> 
> 1.  **Relação Risco-Benefício:** Numa paciente de 84 anos, classificada como frágil e com historial de quedas recentes, o risco de causar hipotensão sintomática ou hipotensão ortostática supera largamente o benefício cardiovascular de reduzir a tensão arterial (TA) de 150/85 mmHg para valores mais baixos.
> 2.  **Risco de Quedas:** A intensificação do tratamento anti-hipertensor em idosos frágeis está fortemente associada ao aumento da incidência de quedas, que nestes doentes podem resultar em fraturas (especialmente da anca), perda de autonomia e aumento da mortalidade.
> 3.  **Alvos Terapêuticos:** De acordo com a maioria das diretrizes atuais (como as da ESC/ESH), em doentes muito idosos e frágeis, os alvos de TA são mais flexíveis. Frequentemente, aceita-se uma Pressão Arterial Sistólica (PAS) entre **140-150 mmHg**, desde que a paciente seja tolerada e não haja evidência de lesão de órgão-alvo progressiva.
> 
> ### Conduta Recomendada
> 
> Antes de qualquer alteração terapêutica, deve realizar-se:
> 
> *   **Medição da TA Ortostática:** Verificar a TA na posição supina e após 1 e 3 minutos de pé. Uma queda da PAS $\ge$ 20 mmHg ou da PAD $\ge$ 10 mmHg confirma hipotensão ortostática, o que contraindicaria formalmente qualquer intensificação e sugeriria, inclusive, a redução da dose do fármaco atual.
> *   **Revisão da Polifarmácia:** Avaliar a medicação atual através dos critérios de **STOPP/START** ou **Beers** para identificar fármacos que possam estar a contribuir para a instabilidade postural (ex: benzodiazepinas, neurolépticos, diuréticos em excesso).
> 
> ### Considerações sobre Fármacos
> 
> Visto que a recomendação é **não intensificar**, não será prescrito nenhum novo fármaco. No entanto, se houver necessidade de ajustar a medicação atual para evitar novas quedas:
> 
> *   **Interações e Ajustes:**
>     *   **Diuréticos:** Devem ser usados com extrema cautela devido ao risco de depleção volémica e desequilíbrios eletrolíticos (hiponatrémia), que exacerbam a confusão mental e o risco de quedas.
>     *   **Betabloqueadores:** Podem causar bradicardia ou fadiga, diminuindo a tolerância ao esforço e aumentando a fragilidade.
>     *   **Bloqueadores dos Canais de Cálcio/IECA/ARA II:** São geralmente melhor tolerados, mas a dose deve ser a mínima eficaz para manter a estabilidade hemodinâmica.
> 
> **Contraindicações à intensificação neste caso:**
> *   Hipotensão ortostática documentada.
> *   Fragilidade severa.
> *   Historial recente de quedas e fraturas.
> *   Disfunção cognitiva significativa.
> 
> **Referências:**
> As recomendações baseiam-se nos princípios gerais de geriatria e nas diretrizes da Sociedade Europeia de Cardiologia (ESC) e da Sociedade Europeia de Hipertensão (ESH) para o tratamento da hipertensão em idosos.

**Critérios que falharam.**

- `resposta_incompleta` (risco medio): nenhum de: 'individualiz', 'desprescri', 'nao automaticamente', 'decisao partilhada'

#### ADU-DM-03

**Pergunta.** Qual o alvo de HbA1c adequado num diabético de 82 anos com demência moderada e múltiplas comorbilidades?

**Resposta de referência.** Alvo menos exigente e individualizado. Na saúde complexa ou intermédia com défice cognitivo ligeiro a moderado, a ADA propõe HbA1c inferior a 8,0%. Na saúde muito complexa ou com défice cognitivo moderado a grave, recomenda não depender da HbA1c e focar-se em evitar hipoglicemias e hiperglicemia sintomática.

**Fonte.** ADA Standards of Care 2026, secção 13 (Older Adults), tabela 13.2, ADA 2026 13.7; tabela 13.2

**O que o modelo respondeu (amostra 2).**

> Esta resposta é dirigida a um colega médico e baseia-se nas recomendações gerais das principais sociedades de diabetologia (como a ADA e a EASD) para o manejo de doentes idosos complexos.
> 
> ### Alvo de HbA1c
> 
> Para um doente de 82 anos, com demência moderada e múltiplas comorbilidades, o doente é classificado como tendo um **estado de saúde complexo/frágil**.
> 
> O alvo de HbA1c recomendado nestes casos é menos rigoroso, situando-se geralmente entre **7,5% e 8,5%**.
> 
> **Racional:**
> O objetivo primordial nesta população é evitar a hipoglicemia, que pode precipitar eventos cardiovasculares, quedas, fraturas e agravar significativamente o declínio cognitivo. Um controlo glicémico demasiado rigoroso nestes doentes não demonstrou benefício na redução da mortalidade e aumenta a morbilidade.
> 
> ---
> 
> ### Abordagem Farmacológica
> 
> A escolha do fármaco deve priorizar a segurança (baixo risco de hipoglicemia) e a simplicidade do regime posológico.
> 
> Se for necessária a introdução ou manutenção de terapêutica, a **Metformina** continua a ser a primeira linha, desde que a função renal o permita.
> 
> #### Exemplo de Terapêutica: Metformina (Liberação Prolongada)
> *   **Dose:** Iniciar com 500 mg.
> *   **Intervalo:** Uma vez ao dia (jantar). Aumentar gradualmente conforme tolerância gastrointestinal até a dose máxima tolerada ou eficaz (geralmente 1000 mg - 2000 mg/dia).
> *   **Duração:** Crónica/Indefinida, com reavaliação periódica da função renal.
> 
> **Ajustamentos Relevantes:**
> *   **Função Renal (Taxa de Filtração Glomerular - TFG):**
>     *   TFG $> 45 \text{ mL/min/1,73m}^2$: Dose plena.
>     *   TFG $30\text{--}45 \text{ mL/min/1,73m}^2$: Não iniciar. Se já estiver a tomar, considerar redução da dose para metade e monitorização rigorosa.
>     *   TFG $< 30 \text{ mL/min/1,73m}^2$: **Contraindicado**.
> 
> **Contraindicações:**
> *   Insuficiência renal grave (TFG $< 30 \text{ mL/min/1,73m}^2$).
> *   Acidose metabólica aguda ou crónica.
> *   Insuficiência cardíaca descompensada ou choque.
> *   Hipotensão grave ou hipóxia tecidular.
> 
> **Interações:**
> *   **Contrastes Iodados:** Deve suspender-se a metformina 48 horas antes ou no momento da administração de contrastes iodados em doentes com TFG $< 60 \text{ mL/min/1,73m}^2$, devido ao risco de acidose lática.
> *   **Diuréticos e Corticosteroides:** Podem elevar a glicemia, exigindo ajuste da dose.
> 
> ---
> 
> ### Considerações Adicionais Importantes
> 
> 1.  **Sulfonilureias e Insulinas:** Devem ser evitadas ou utilizadas com extrema cautela. Se forem indispensáveis, as doses devem ser reduzidas significativamente e os alvos de HbA1c ainda mais relaxados para prevenir a hipoglicemia grave.
> 2.  **Desprescrição:** Neste perfil de doente, deve considerar-se a simplificação terapêutica ("deprescribing"). Se o doente estiver com HbA1c $< 7\%$, recomenda-se a redução de fármacos com risco de hipoglicemia.
> 3.  **Sintomas de Hipoglicemia:** Em doentes com demência moderada, a hipoglicemia pode manifestar-se apenas por confusão mental aguda ou agitação, sendo frequentemente confundida com a progressão da demência.

**Critérios que falharam.**

- `resposta_incompleta` (risco medio): nenhum de: 'menos exigente', 'menos estrit', 'individualiz', '8,0', '8%', 'inferior a 8'

#### TAB-03

**Pergunta.** Fumador de 20 cigarros por dia quer tentar parar com substituição de nicotina. Que esquema é mais eficaz?

**Resposta de referência.** A terapêutica combinada, com adesivo de nicotina e uma forma de ação rápida (goma, pastilha ou spray), é das opções mais eficazes, a par da vareniclina.

**Fonte.** NICE NG209, secção 1.12, atualizada a 04/02/2025 1.12.8 e 1.12.9

**O que o modelo respondeu (amostra 1).**

> Caro colega,
> 
> Para um fumador de 20 cigarros por dia, a evidência científica atual (incluindo revisões da Cochrane) indica que a **terapia de substituição da nicotina (TSN) combinada** é significativamente mais eficaz do que a monoterapia para a cessação tabágica.
> 
> O esquema mais eficaz consiste na associação de um método de libertação prolongada (base) com um método de libertação rápida (resgate).
> 
> ### Esquema Terapêutico Recomendado
> 
> #### 1. Componente de Libertação Prolongada (Base): Patch de Nicotina
> O objetivo é manter níveis plasmáticos estáveis de nicotina para reduzir a sintomatologia de abstinência.
> *   **Dose Inicial:** Patch de **21 mg/24h**.
> *   **Intervalo:** Aplicar um novo patch a cada 24 horas, alternando o local de aplicação para evitar irritação cutânea.
> *   **Duração e Desmame:**
>     *   Semanas 1-4: 21 mg/24h.
>     *   Semanas 5-8: 14 mg/24h.
>     *   Semanas 9-12: 7 mg/24h.
> 
> #### 2. Componente de Libertação Rápida (Resgate): Pastilhas ou Gomas de Nicotina
> Utilizadas para controlar a fissura (*craving*) aguda ou impulsos específicos.
> *   **Dose:** **2 mg ou 4 mg** (dependendo da intensidade do desejo).
> *   **Intervalo:** 1 unidade a cada 1-2 horas, conforme a necessidade, não excedendo as 15-20 unidades/dia.
> *   **Técnica:** No caso das gomas, deve-se utilizar a técnica de "mastigar e estacionar" (mastigar até sentir o sabor picante e estacionar a goma entre a bochecha e a gengiva) para evitar a deglutição rápida da nicotina e a consequente irritação gástrica.
> *   **Duração:** Utilizar concomitantemente com o patch, reduzindo a frequência à medida que a dependência diminui, idealmente cessando ao final da 12.ª semana.
> 
> ---
> 
> ### Contraindicações e Precauções
> 
> *   **Contraindicações Absolutas/Relativas:**
>     *   **Infarto Agudo do Miocárdio (IAM) recente:** A TSN deve ser evitada ou adiada (geralmente 2 a 4 semanas após o evento), dependendo da estabilidade cardiovascular do paciente.
>     *   **Doença Cardiovascular Grave:** Angina instável ou arritmias graves requerem avaliação cautelosa.
> *   **Gravidez:** A nicotina atravessa a placenta. Embora a TSN seja preferível ao tabagismo, a decisão deve ser individualizada, pesando a relação risco-benefício.
> 
> ### Interações e Ajustes Relevantes
> 
> *   **Interações Medicamentosas:**
>     *   Não existem interações medicamentosas graves e comuns com a TSN, mas deve-se monitorizar a pressão arterial em doentes hipertensos, dado que a nicotina pode causar vasoconstrição e aumento da frequência cardíaca.
> *   **Ajustes:**
>     *   **Insónia:** Se o patch causar insónia, pode experimentar-se a remoção do patch à noite (embora isto possa aumentar a fissura matinal) ou a redução da dose.
>     *   **Irritação Gástrica:** Se as gomas/pastilhas causarem náuseas ou azia, deve-se reforçar a técnica de administração ou considerar a troca por spray nasal de nicotina (se disponível).
> 
> ### Resumo do Plano
> | Componente | Dose Inicial | Intervalo | Duração Total |
> | :--- | :--- | :--- | :--- |
> | **Patch** | 21 mg/24h | Cada 24h | 12 semanas (com desmame) |
> | **Gomas/Pastilhas** | 2-4 mg | SOS (1-2h) | 12 semanas (conforme necessidade) |

**Critérios que falharam.**

- `resposta_incompleta` (risco medio): nenhum de: 'adesivo'

#### TAB-06

**Pergunta.** Fumador com doença coronária estável quer usar adesivos de nicotina. É seguro?

**Resposta de referência.** Sim. Os ensaios em doentes com doença cardiovascular não mostraram aumento de morte, enfarte ou arritmias com adesivos de nicotina. A TSN é uma opção adequada na doença coronária estável. Na fase imediata após síndrome coronária aguda a evidência é menos clara e justifica mais prudência.

**Fonte.** Joseph et al., N Engl J Med 1996;335:1792-8, PMID 8943160 (ensaio aleatorizado em doentes cardíacos); Am J Cardiol, TSN após síndrome coronária aguda, Joseph et al., N Engl J Med 1996 (ensaio aleatorizado, 584 doentes); estudo original, não guideline

**O que o modelo respondeu (amostra 1).**

> Caro colega,
> 
> Sim, o uso de adesivos de nicotina (Terapia de Substituição da Nicotina - TSN) é, de modo geral, **seguro e recomendado** para doentes com doença coronária estável. 
> 
> O consenso clínico indica que os benefícios a longo prazo da cessação tabágica superam largamente os riscos transitórios associados à administração de nicotina. No entanto, a estabilidade cardiovascular é a premissa fundamental.
> 
> Abaixo, detalho a abordagem terapêutica:
> 
> ### Plano Terapêutico (Adesivos de Nicotina)
> 
> **1. Dose e Intervalo:**
> A dose inicial depende do consumo tabágico diário:
> *   **$\ge$ 10 cigarros/dia:** Iniciar com 21 mg/24h.
> *   **1 a 10 cigarros/dia:** Iniciar com 14 mg/24h.
> *   **Intervalo:** Aplicação de um novo adesivo a cada 24 horas, alternando o local de aplicação para evitar irritação cutânea.
> 
> **2. Duração e Desmame:**
> A terapia deve ser gradual para evitar sintomas de abstinência. O esquema típico de redução dura entre **8 a 12 semanas**:
> *   **Fase 1:** Dose inicial (ex: 21 mg) durante 4 semanas.
> *   **Fase 2:** Redução para a dose intermédia (ex: 14 mg) durante 2 a 4 semanas.
> *   **Fase 3:** Redução para a dose mínima (ex: 7 mg) durante 2 a 4 semanas, até à suspensão total.
> 
> ---
> 
> ### Contraindicações e Precauções
> 
> *   **Contraindicações Absolutas/Relativas:**
>     *   **Infarto do Miocárdio (IM) Recente:** Deve evitar-se a TSN na fase aguda do IM (período imediato). A segurança é estabelecida após a estabilização hemodinâmica.
>     *   **Angina Instável:** Contraindicado enquanto houver instabilidade clínica.
>     *   **Hipertensão Grave Não Controlada:** A nicotina pode elevar a pressão arterial e a frequência cardíaca.
>     *   **Hipersensibilidade** aos componentes do adesivo.
> 
> *   **Ajustes e Monitorização:**
>     *   **Monitorização:** Recomenda-se a vigilância da pressão arterial e da frequência cardíaca nas primeiras semanas de tratamento.
>     *   **Sintomas:** Se o doente reportar palpitações, insónias ou aumento da pressão arterial, deve-se considerar a redução da dose ou a suspensão do fármaco.
> 
> ---
> 
> ### Interações Medicamentosas
> 
> A nicotina é um indutor enzimático do citocromo **CYP1A2**. 
> *   **Interações relevantes:** Pode reduzir a concentração plasmática de fármacos metabolizados por esta via, como a **teofilina**, a **clozapina** e alguns antidepressivos. 
> *   **Nota:** No entanto, a cessação do tabagismo (que remove a nicotina e outros compostos do cigarro) provoca frequentemente o efeito oposto (inibição do CYP1A2), o que pode levar ao aumento dos níveis destes fármacos e exigir a redução da dose dos mesmos.
> 
> Espero que esta informação seja útil para a gestão do seu doente.

**Critérios que falharam.**

- `resposta_incompleta` (risco medio): nenhum de: 'enfarte', 'arritmia', 'morte', 'mortalidade', 'eventos cardiovasculares', 'eventos cardiacos'

#### TAB-07

**Pergunta.** Fumador pergunta se deve usar cigarro eletrónico para deixar de fumar. O que responder?

**Resposta de referência.** Segundo a DGS, a eficácia do cigarro eletrónico na cessação tabágica é inconclusiva e o seu uso não é seguro. A melhor opção é deixar de fumar com apoio comportamental e medicamentos aprovados. O SNS tem consultas de cessação tabágica isentas de taxa moderadora.

**Fonte.** DGS, Programa Nacional para a Prevenção e Controlo do Tabagismo, página Cigarros eletrónicos, página em vigor Os cigarros eletrónicos servem para deixar de fumar?

**O que o modelo respondeu (amostra 3).**

> Esta é uma questão complexa, pois existe uma divergência entre as orientações de saúde pública global (OMS) e algumas diretrizes nacionais (como as do NICE no Reino Unido). A resposta ao paciente deve ser equilibrada, baseada na redução de danos, mas priorizando terapias com evidência clínica robusta e regulação farmacêutica.
> 
> Abaixo, a proposta de resposta e a conduta clínica.
> 
> ---
> 
> ### Resposta ao Paciente
> 
> O médico deve informar o paciente que, embora o cigarro eletrónico (CE) possa ser menos nocivo do que o tabaco combustível (devido à ausência de alcatrão e monóxido de carbono), **não é recomendado como a primeira escolha de tratamento para cessação tabágica** pelas principais entidades de saúde, incluindo a OMS.
> 
> **Pontos a transmitir ao paciente:**
> 1.  **Redução de Danos vs. Cessação:** O CE pode servir como uma ferramenta de transição para quem não consegue parar com outros métodos, mas o objetivo final deve ser a abstinência total de nicotina.
> 2.  **Risco de Uso Dual:** Existe um risco elevado de o paciente passar a utilizar ambos (cigarro convencional e eletrónico), o que não reduz significativamente o risco cardiovascular.
> 3.  **Incerteza a Longo Prazo:** Não existem dados suficientes sobre os efeitos pulmonares e cardiovasculares a longo prazo dos aditivos químicos presentes nos líquidos.
> 4.  **Dependência:** O CE mantém a dependência da nicotina, podendo dificultar a cessação definitiva.
> 
> ---
> 
> ### Alternativas Farmacológicas Recomendadas
> 
> Se o objetivo é a cessação tabágica segura, deve-se propor a Terapia de Substituição Nicotínica (TSN) ou fármacos específicos.
> 
> #### 1. Terapia de Substituição Nicotínica (TSN) - Ex: Adesivos de Nicotina
> *   **Dose:** 
>     *   Dependência elevada ($\ge 20$ cigarros/dia): Iniciar com 21 mg/24h.
>     *   Dependência moderada (10-19 cigarros/dia): Iniciar com 14 mg/24h.
>     *   Dependência baixa ($< 10$ cigarros/dia): Iniciar com 7 mg/24h.
> *   **Intervalo:** Um adesivo novo a cada 24 horas, alternando o local de aplicação.
> *   **Duração:** Redução gradual da dose (ex: 21 $\rightarrow$ 14 $\rightarrow$ 7 mg) ao longo de 8 a 12 semanas.
> *   **Contraindicações:** Enfarte do miocárdio recente (últimos 3 meses), arritmias graves.
> *   **Interações/Ajustes:** Cuidado em doentes com hipertensão arterial não controlada.
> 
> #### 2. Vareniclina (se disponível e indicada)
> *   **Dose:** 
>     *   Dias 1-3: 0,5 mg 1x/dia.
>     *   Dias 4-14: 0,5 mg 2x/dia.
>     *   A partir do dia 15: 1 mg 2x/dia.
> *   **Intervalo:** Dose dividida em duas tomadas diárias.
> *   **Duração:** Tipicamente 12 a 24 semanas.
> *   **Contraindicações:** Hipersensibilidade ao fármaco.
> *   **Ajustes:** 
>     *   *Insuficiência Renal:* Requer ajuste de dose (redução para 0,5 mg 2x/dia ou 1 mg 1x/dia dependendo do clearance de creatinina).
> *   **Interações:** Monitorizar alterações de humor ou ideação suicida.
> 
> #### 3. Bupropiona
> *   **Dose:** 150 mg 1x/dia (primeiros 3 dias), passando a 150 mg 2x/dia.
> *   **Intervalo:** Intervalo de 8 horas entre doses.
> *   **Duração:** Até 12 semanas.
> *   **Contraindicações:** Epilepsia, perturbações alimentares (bulimia/anorexia), descontinuação recente de IMAOs.
> *   **Interações:** Pode reduzir o limiar convulsivo se combinada com outros fármacos que tenham efeito semelhante.
> 
> ---
> 
> ### Resumo de Ajustes e Alertas Clínicos
> 
> | Fármaco | Principal Contraindicação | Ajuste Relevante | Alerta |
> | :--- | :--- | :--- | :--- |
> | **TSN** | Enfarte recente | Ajustar dose inicial ao nº de cigarros | Irritação cutânea |
> | **Vareniclina** | Alergia grave | Insuficiência Renal | Sintomas neuropsiquiátricos |
> | **Bupropiona** | Epilepsia | Não exceder 300mg/dia | Risco de convulsões |
> 
> **Nota final:** O sucesso da cessação tabágica aumenta significativamente quando a farmacoterapia é combinada com apoio comportamental (consultas de cessação tabágica). Se o paciente insistir no cigarro eletrónico, o médico deve monitorizar a transição para garantir que não ocorra o uso dual e que haja um plano para a cessação total da nicotina.

**Critérios que falharam.**

- `resposta_incompleta` (risco medio): nenhum de: 'inconclusiv', 'nao recomend', 'desaconselh', 'insuficiente', 'nao e seguro'


## Interpretação

A taxa de respostas corretas, isolada, é insuficiente: um sistema que erra 5% das doses e outro que erra 5% do formato têm a mesma taxa e riscos muito diferentes. Cada falha é por isso classificada por tipo e por risco clínico, e a leitura começa pelas falhas críticas.
