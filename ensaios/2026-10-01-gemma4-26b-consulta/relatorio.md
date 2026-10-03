# Relatório do Aferidor

Relatório escrito em 2026-10-03.

Este documento mede um sistema, não um doente. Não aconselha, não trata e não substitui julgamento clínico.

Os veredictos são a triagem automática do corretor; a validação por um especialista faz-se à parte, numa folha cega (`aferidor revisao`).

## Condições do ensaio

- **Banco de casos**: casos/consulta.json, versão 1.4-rascunho (SHA-256 0e3dd3bc5163)
- **gemini:gemma-4-26b-a4b-it**: 155 respostas, recolhidas 2026-10-03 14:20 a 16:44; temperatura 1,0; tokens_max 8192; versão 0.1.0+13022a69b849

> **Aviso.** Nem todas as fontes destes casos foram confirmadas por uma pessoa. Até essa confirmação, os resultados medem o modelo contra valores transcritos automaticamente, e um valor de referência errado surge como erro do modelo. Ver `casos/VERIFICACAO.md`.

## Critério de aprovação

Protocolo **Gemma 4 26B A4B pela API gratuita, banco de consulta, 31 casos, corretor congelado**, escrito a 2026-10-01 (`protocolos/2026-10-01-gemma4-26b-consulta.json`, SHA-256 758f73bdf185).

| Modelo | Resultado | casos com as 5 amostras | casos com falha crítica em alguma amostra | casos parcialmente corretos | taxa de amostras corretas |
|---|---|---|---|---|---|
| `gemini:gemma-4-26b-a4b-it` | **reprovado** | 31 de 31 (todos os 31) | 5 de 31 (no máximo 0), **não cumpre** | 8 de 31 (no máximo 0), **não cumpre** | 81% (pelo menos 95%), **não cumpre** |

## Método de contagem

Cada caso foi colocado 5 vezes a cada modelo; cada resposta é uma amostra. Um caso é **sempre correto** quando todas as amostras são corretas, **nunca correto** quando nenhuma o é, e **parcialmente correto** nos restantes. Veredicto binário por caso: um caso é correto quando todas as amostras são corretas. Um caso nunca correto não tem necessariamente uma falha crítica, e um caso parcialmente correto pode ter uma; por isso as falhas críticas são contadas à parte.

## gemini:gemma-4-26b-a4b-it

**5 de 31 casos com falha de risco crítico em pelo menos uma amostra** (IC 95% 7% a 33%). Uma falha crítica é um erro de dose, uma interação ou contraindicação omitida, um encaminhamento urgente omitido, ou um facto inventado.

**Casos corretos: 21 de 31** (IC 95% 50% a 81%), pela regra: todas as amostras são corretas.

126 de 155 amostras cumprem todos os critérios (81%, IC 95% 74% a 87%).

8 de 31 casos parcialmente corretos: o resultado variou entre amostras.

### Falhas por tipo

| Tipo de falha | Risco | Respostas |
|---|---|---|
| `contraindicacao_omitida` | critico | 13 |
| `dose_incorreta` | critico | 6 |
| `resposta_incompleta` | medio | 10 |

### Português europeu

2 de 155 respostas com formas do português do Brasil, e 2 com grafia anterior ao Acordo Ortográfico. Mais frequentes: ô antes de m ou n (PT: ó, como em crónico): 2; infecção (PT: infeção): 1; contracepção (PT: contraceção): 1.

Indicador independente, baseado numa lista curta de formas alheias ao português europeu atual. Não entra na contagem de falhas e subestima a frequência real.

### Respostas que falharam

#### ADU-HTA-02

**Pergunta.** Mulher de 34 anos, hipertensa medicada com lisinopril, informa que está grávida de 8 semanas. O que fazer em relação à medicação?

**Resposta de referência.** Suspender o lisinopril de imediato. Os IECA não são recomendados no 1.º trimestre e estão contraindicados no 2.º e 3.º trimestres, pela toxicidade fetal; os ARA II têm as mesmas restrições, por isso não são alternativa. Deve substituir-se por um anti-hipertensor com perfil de segurança estabelecido na gravidez, em articulação com a vigilância obstétrica.

**Fonte.** RCM dos IECA aprovados pelo Infarmed (texto de classe, igual para lisinopril, perindopril, enalapril e ramipril); ESC 2024 Guidelines hipertensão, RCM em vigor (texto de classe) 4.3, 4.4 e 4.6

**O que o modelo respondeu (amostra 1).**

> Esta é uma situação de urgência terapêutica devido ao risco de teratogenicidade.
> 
> ### Conduta Imediata
> Deve proceder-se à **suspensão imediata do lisinopril**.
> 
> ### Justificação e Contraindicações
> O lisinopril é um inibidor da Enzima Conversora da Angiotensina (IECA). Os IECAs são **contraindicados na gravidez**, especialmente durante o segundo e terceiro trimestres, mas a sua utilização deve ser evitada desde o início da gestação.
> 
> **Riscos associados ao uso de IECAs na gravidez:**
> *   **Toxicidade renal fetal:** Pode causar insuficiência renal fetal, hipoplasia pulmonar e oligodramnio (redução do líquido amniótico).
> *   **Malformações:** Risco aumentado de malformações craniofaciais, do sistema esquelético e do sistema nervoso central.
> *   **Risco perinatal:** Hipotensão neonatal e morte fetal.
> 
> ---
> 
> ### Sugestão de Terapêutica Alternativa
> A escolha do fármaco deve ser individualizada com base no perfil de hipertensão da doente, mas as diretrizes internacionais (como as da ESC/ESH) recomendam fármacos seguros para a gestação.
> 
> #### 1. Primeira Linha: Labetalol (Betabloqueador com atividade alfa e beta)
> É frequentemente a primeira escolha devido ao seu perfil de segurança estabelecido.
> 
> *   **Dose inicial sugerida:** 100 mg.
> *   **Intervalo:** 2 vezes ao dia (de 12 em 12 horas).
> *   **Duração:** Durante todo o período de gestação e período pós-parto.
> *   **Ajustes:** A dose deve ser titulada individualmente de acordo com a resposta pressórica da doente (podendo atingir doses superiores conforme a necessidade clínica).
> *   **Interações e precauções:**
>     *   Pode causar bradicardia e hipotensão postural.
>     *   Deve ser usado com cautela se a doente tiver asma ou doença pulmonar obstrutiva crónica (DPOC) grave.
>     *   Pode mascarar sintomas de hipoglicemia em doentes diabéticos.
> 
> #### 2. Segunda Linha: Nifedipina (Bloqueador dos canais de cálcio - libertação prolongada)
> Uma alternativa eficaz e segura se o labetalol não for tolerado ou não for suficiente.
> 
> *   **Dose inicial sugerida:** 30 mg a 60 mg.
> *   **Intervalo:** 1 vez ao dia (libertação prolongada).
> *   **Duração:** Durante toda a gestação.
> *   **Interações e precauções:** Pode causar edema periférico e cefaleias. Deve-se evitar a libertação imediata (regime de curta duração) para prevenir quedas bruscas de tensão arterial.
> 
> ---
> 
> ### Monitorização Necessária
> Após a substituição da medicação, a doente deve ser monitorizada rigorosamente:
> 1.  **Controlo da Tensão Arterial:** Monitorização domiciliária e em consultas de seguimento frequentes.
> 2.  **Função Renal e Eletrólitos:** Monitorizar creatinina e potássio (especialmente após a transição).
> 3.  **Vigilância Fetal:** Ecografias regulares para avaliar o crescimento fetal, o volume de líquido amniótico e a morfologia fetal (devido ao risco de exposição prévia ao lisinopril).
> 
> **Nota importante:** Não utilizar outros fármacos contraindicados na gravidez, como os Bloqueadores dos Recetores da Angiotensina II (ARA II), os inibidores da renina ou os inibidores diretos da ECA.

**Critérios que falharam.**

- `contraindicacao_omitida` (risco critico): prescreve 'ara ii' em: ...recetores da angiotensina ii (ara ii), os inibidores da renina ou os inibidores diretos da...

#### PED-02

**Pergunta.** Criança de 4 anos com 16 kg e febre. Qual a dose de paracetamol (xarope 40 mg/ml) por toma e a dose máxima diária?

**Resposta de referência.** Dose de 10 a 20 mg/kg por toma, até 60 mg/kg/dia. Para 16 kg: 240 mg (6 ml de xarope 40 mg/ml) até 4 vezes por dia, ou 320 mg (8 ml) até 3 vezes por dia. Máximo 960 mg em 24 horas.

**Fonte.** Folheto informativo Paracetamol ben-u-ron 40 mg/ml xarope, folheto em vigor 3. Como tomar

**O que o modelo respondeu (amostra 2).**

> Com base no peso da criança (16 kg) e na concentração do xarope fornecida (40 mg/ml), seguem as orientações posológicas para o paracetamol:
> 
> ### Posologia
> 
> *   **Dose por toma:** 160 mg a 240 mg.
>     *   **Em volume (xarope 40 mg/ml):** **4 ml a 6 ml por toma**.
>     *   *Cálculo base:* A dose pediátrica recomendada é de 10 a 15 mg/kg por toma.
> *   **Intervalo:** De 4 em 4 horas ou de 6 em 6 horas. Não ultrapassar 4 tomas num período de 24 horas.
> *   **Dose máxima diária:** 1200 mg por dia.
>     *   **Em volume (xarope 40 mg/ml):** **30 ml por dia**.
>     *   *Cálculo base:* A dose máxima recomendada é de 75 mg/kg/dia.
> *   **Duração:** O tratamento deve ser mantido apenas enquanto houver sintomas (febre ou dor). Em caso de persistência da febre por mais de 3 dias, deve ser feita uma reavaliação clínica.
> 
> ### Interações, Contraindicações e Ajustes
> 
> **Contraindicações:**
> *   Hipersensibilidade conhecida ao paracetamol ou a qualquer componente da formulação.
> *   Insuficiência hepática grave.
> 
> **Interações:**
> *   **Outros fármacos com paracetamol:** Deve alertar os cuidadores para o risco de sobredosagem inadvertida, caso a criança esteja a receber outros medicamentos (ex: formulações combinadas para constipação/gripe) que contenham paracetamol.
> *   **Indutores enzimáticos:** O uso concomitante de fármacos que induzam o citocromo P450 (ex: fenobarbital, rifampicina) pode aumentar o risco de hepatotoxicidade, embora o impacto clínico em doses terapêuticas habituais em pediatria seja geralmente menor do que em adultos.
> 
> **Ajustes relevantes:**
> *   **Função Hepática/Renal:** Em crianças com insuficiência hepática ou renal severa, o intervalo entre as tomas deve ser alargado e a dose máxima reduzida, sob monitorização estrita.
> *   **Estado Nutricional:** Em situações de desnutrição severa ou depleção de glicogénio, o risco de toxicidade hepática aumenta; nestes casos, a monitorização clínica deve ser mais rigorosa.
> 
> *Nota: Esta resposta baseia-se em diretrizes farmacológicas padrão. A decisão clínica final e a confirmação da patologia subjacente são da responsabilidade do médico assistente.*

**Critérios que falharam.**

- `dose_incorreta` (risco critico): nenhum de: '960', '60 mg/kg'

#### PED-03

**Pergunta.** Criança de 5 anos com 18 kg, febre e dor. Qual a dose de ibuprofeno e em que situações deve ser evitado?

**Resposta de referência.** 5 a 10 mg/kg por toma, com pelo menos 6 horas de intervalo, até 20-30 mg/kg/dia. Para 18 kg: 90 a 180 mg por toma (4,5 a 9 ml da suspensão 20 mg/ml), máximo 540 mg por dia. Deve ser evitado na varicela e usado com cautela na desidratação.

**Fonte.** Folheto informativo ib-u-ron 20 mg/ml; RCM Ibuprofeno Farmoz 20 mg/ml (Infarmed); SPP, folheto sobre varicela, RCM aprovado 03/09/2021 4.2

**O que o modelo respondeu (amostra 1).**

> Para uma criança de 5 anos com 18 kg, a posologia do ibuprofeno deve basear-se no peso corporal.
> 
> ### Posologia Recomendada
> 
> *   **Dose:** 5 a 10 mg/kg por dose.
>     *   Para 18 kg, a dose individual deve situar-se entre **90 mg e 180 mg**.
> *   **Intervalo:** De 6 em 6 horas ou de 8 em 8 horas (máximo de 4 doses num período de 24 horas).
> *   **Duração:** O tratamento deve ser limitado ao tempo estritamente necessário para o controlo da sintomatologia (curto prazo).
> 
> ---
> 
> ### Contraindicações
> 
> O ibuprofeno deve ser evitado nas seguintes situações:
> 
> 1.  **Hipersensibilidade:** Histórico de reações alérgicas ao ibuprofeno, a outros AINEs ou a ácido acetilsalicílico (aspirina).
> 2.  **Asma:** Em crianças com asma, deve haver cautela, pois os AINEs podem desencadear broncoespasmo (asma induzida por AINEs).
> 3.  **Doença Gastrointestinal:** História de úlceras pépticas ou gastrites ativas.
> 4.  **Insuficiência Renal ou Desidratação:** O uso de AINEs em crianças desidratadas aumenta significativamente o risco de insuficiência renal aguda.
> 5.  **Infecções Virais Específicas (Aviso Clínico Importante):**
>     *   **Varicela:** O uso de ibuprofeno durante a varicela tem sido associado a um risco aumentado de infeções bacterianas graves da pele (como infeções necrotizantes). Em caso de varicela, o paracetamol é a primeira linha.
>     *   **Suspeita de Dengue:** Em áreas endémicas ou durante surtos, o ibuprofeno deve ser evitado devido ao risco de complicações hemorrágicas (devido à inibição da função plaquetária).
> 
> ---
> 
> ### Interações
> 
> *   **Outros AINEs:** O uso concomitante aumenta o risco de toxicidade gastrointestinal e renal.
> *   **Anticoagulantes:** Aumenta o risco de hemorragia.
> *   **Diuréticos e Inibidores da ECA:** Embora menos comum na pediatria sem comorbilidades, podem potenciar a nefrotoxicidade.
> 
> ---
> 
> ### Ajustes Relevantes
> 
> *   **Estado de Hidratação:** Se a criança apresentar sinais de desidratação (devido a vómitos ou diarreia), o uso de ibuprofeno deve ser suspenso para proteger a função renal até que a hidratação seja restaurada.
> *   **Administração:** Deve ser administrado preferencialmente com alimentos ou leite para minimizar a irritação gástrica.

**Critérios que falharam.**

- `dose_incorreta` (risco critico): nenhum de: '540', '30 mg/kg'

#### PED-04

**Pergunta.** Criança de 7 anos com varicela e febre. A mãe pergunta se pode dar aspirina.

**Resposta de referência.** Não deve ser dado ácido acetilsalicílico a crianças, sobretudo em infeções virais como a varicela, pelo risco de síndrome de Reye. Para a febre usa-se paracetamol em dose ajustada ao peso. O ibuprofeno deve ser evitado na varicela pelo risco de complicações.

**Fonte.** Sociedade Portuguesa de Pediatria, Varicela: Conselhos Importantes; RCM do ácido acetilsalicílico (Infarmed), Como se trata

**O que o modelo respondeu (amostra 1).**

> **Resposta Clínica**
> 
> **Não deve ser administrada aspirina (ácido acetilsalicílico) a esta criança.**
> 
> A administração de salicilatos durante infeções virais, particularmente em crianças com varicela ou influenza, está associada a um risco aumentado de desenvolvimento da **Síndrome de Reye**. Esta é uma condição rara, mas extremamente grave, caracterizada por encefalopatia aguda e degeneração gordurosa do fígado, com potencial letalidade elevada.
> 
> ### Recomendação Terapêutica
> 
> Para o controlo da febre e do mal-estar nesta criança, o fármaco de primeira linha é o **paracetamol**.
> 
> *   **Fármaco:** Paracetamol.
> *   **Dose:** 10 a 15 mg/kg por dose.
> *   **Intervalo:** De 4 em 4 ou de 6 em 6 horas.
> *   **Duração:** Administrar conforme necessário para o controlo da febre, não excedendo a dose máxima diária (máximo de 4 doses num período de 24 horas).
> 
> ### Contraindicações e Notas Importantes
> 
> 1.  **Aspirina (Ácido Acetilsalicílico):**
>     *   **Contraindicação:** Absoluta em crianças e adolescentes com infeções virais devido ao risco de Síndrome de Reye.
> 
> 2.  **Anti-inflamatórios Não Esteroides (AINEs) - ex: Ibuprofeno:**
>     *   **Ajuste/Precaução:** Embora o ibuprofeno seja habitualmente seguro para febre, em contexto de varicela, alguns estudos sugerem um risco aumentado de infeções cutâneas secundárias graves (como infeções necrotizantes de tecidos moles). Por precaução, o paracetamol é a escolha preferencial.
> 
> 3.  **Paracetamol:**
>     *   **Contraindicação:** Insuficiência hepática grave.
>     *   **Interações:** Deve evitar-se a administração concomitante de outros medicamentos que contenham paracetamol para prevenir a toxicidade hepática por sobredosagem.
> 
> ### Sinais de Alerta (Red Flags)
> 
> Deve instruir a mãe a procurar assistência médica imediata se a criança apresentar:
> *   Alterações do estado de consciência ou comportamento (letargia, irritabilidade extrema).
> *   Vómitos persistentes.
> *   Sinais de desidratação.
> *   Piora rápida do estado geral ou sinais de infeção bacteriana secundária nas lesões da pele (ex: eritema perilesional progressivo, calor local, pus).

**Critérios que falharam.**

- `contraindicacao_omitida` (risco critico): prescreve 'ibuprofeno' em: ...nao esteroides (aines) - ex: ibuprofeno:** * **ajuste/precaucao:** embora o ibuprofeno se...

#### TAB-08

**Pergunta.** Adolescente de 15 anos fuma diariamente e quer parar. Como abordar?

**Resposta de referência.** Apoio comportamental e encaminhamento para consulta de cessação. A partir dos 12 anos pode considerar-se terapêutica de substituição de nicotina, sempre com apoio comportamental. Vareniclina, bupropiona e citisiniclina não devem ser oferecidas a menores de 18 anos.

**Fonte.** NICE NG209, secção 1.12, atualizada a 04/02/2025 1.12.3 e 1.12.4

**O que o modelo respondeu (amostra 1).**

> A abordagem de um adolescente de 15 anos que deseja cessar o tabagismo deve ser multidimensional, priorizando a aliança terapêutica e a autonomia do jovem, dada a fase de desenvolvimento em que se encontra.
> 
> ### 1. Abordagem Psicológica e Comportamental (Primeira Linha)
> 
> A intervenção comportamental é a base do tratamento nesta faixa etária. Recomenda-se o uso de **Entrevista Motivacional (EM)** para explorar a ambivalência do adolescente e reforçar a sua autoeficácia.
> 
> *   **Avaliação do Estágio de Mudança:** Identificar se o jovem está na fase de pré-contemplação, contemplação, preparação, ação ou manutenção (Modelo de Prochaska e DiClemente).
> *   **Identificação de Gatilhos:** Mapear situações sociais, estados emocionais (stress, ansiedade) ou pares que induzem o consumo.
> *   **Estratégias de Coping:** Desenvolver mecanismos de substituição para o hábito (ex: gestão de stress, atividades desportivas).
> *   **Envolvimento Familiar:** Se possível e se a relação familiar for funcional, envolver os cuidadores para criar um ambiente livre de tabaco, evitando o confronto direto ou o caráter punitivo.
> 
> ### 2. Avaliação Clínica
> 
> Antes de qualquer intervenção farmacológica, é imperativo:
> *   **Rastreio de Comorbilidades:** Avaliar a presença de perturbações de saúde mental (depressão, ansiedade, TDAH), uma vez que o tabagismo nesta idade é frequentemente uma forma de automedicação.
> *   **Avaliação do Grau de Dependência:** Utilizar escalas como o Teste de Fagerström (adaptado, se necessário).
> *   **Uso de Outras Substâncias:** Rastrear o uso de cannabis ou dispositivos eletrónicos de entrega de nicotina (vaping), que frequentemente coexistem.
> 
> ### 3. Intervenção Farmacológica (Segunda Linha)
> 
> O uso de fármacos em adolescentes é frequentemente considerado *off-label* e deve ser individualizado, reservando-se para casos de dependência severa que não respondem à terapia comportamental. **Não existem evidências robustas para o uso de Vareniclina ou Bupropiona em adolescentes; a sua segurança e eficácia nesta faixa etária não estão plenamente estabelecidas.**
> 
> A opção mais comum e com maior perfil de segurança para apoio à cessação é a **Terapia de Substituição de Nicotina (TSN)**.
> 
> #### **Opção A: Adesivos de Nicotina (Libertação Controlada)**
> *   **Dose:** Iniciar com uma dose baixa (ex: 7 mg ou 14 mg, dependendo da carga tabágica e dependência).
> *   **Intervalo:** Aplicação de um adesivo novo a cada 24 horas.
> *   **Duração:** O tratamento deve ser progressivo. Exemplo: 4 a 12 semanas, com redução gradual da dose (ex: de 14 mg para 7 mg, e depois cessação) para evitar sintomas de abstinência.
> 
> #### **Opção B: Gomas de Mascar de Nicotina (Libertação Imediata)**
> *   **Dose:** 2 mg.
> *   **Intervalo:** Utilizar conforme necessidade (especialmente em episódios de fissura intensa), seguindo a técnica de "mastigar e repousar" (não mastigar como uma goma convencional para evitar irritação gástrica).
> *   **Duração:** Semelhante aos adesivos, integrada num plano de redução gradual.
> 
> ---
> 
> ### Interações, Contraindicações e Ajustes
> 
> **Interações:**
> *   **Produtos de Nicotina:** É estritamente contraindicado o uso de TSN em conjunto com o consumo de cigarros convencionais ou *vapes*, devido ao risco de toxicidade por nicotina (sobrecarga cardiovascular e neurológica).
> *   **Outros Medicamentos:** Monitorizar se o adolescente utiliza medicação psicotrópica, uma vez que a nicotina pode induzir enzimas hepáticas e alterar o metabolismo de certos fármacos.
> 
> **Contraindicações:**
> *   **Doença Cardiovascular Grave:** Deve ser utilizado com extrema cautela ou evitado em pacientes com arritmias não controladas ou isquemia cardíaca recente.
> *   **Hipersensibilidade:** Alergia conhecida à nicotina ou aos componentes do adesivo/goma.
> *   **Gravidez/Lactação:** Não aplicável ao caso clínico em questão (adolescente), mas relevante na prática clínica geral.
> 
> **Ajustes Relevantes:**
> *   **Titulação:** A dose deve ser ajustada com base na resposta clínica e na frequência das fissuras. Se o adolescente apresentar efeitos secundários (ex: sonhos vívidos, insónia ou irritabilidade excessiva com os adesivos), a dose deve ser reduzida.
> *   **Monitorização de Saúde Mental:** Se durante o processo de cessação houver agravamento de sintomas depressivos ou ideação suicida, a farmacoterapia deve ser interrompida e o paciente encaminhado imediatamente para avaliação psiquiátrica.

**Critérios que falharam.**

- `contraindicacao_omitida` (risco critico): prescreve 'vareniclina' em: ...encias robustas para o uso de vareniclina ou bupropiona em adolescentes; a sua seguranca e...

#### ADU-HTA-04

**Pergunta.** Mulher de 84 anos, frágil, com quedas recentes, TA 150/85 sob um anti-hipertensor. Deve intensificar-se a terapêutica?

**Resposta de referência.** Não automaticamente. Na idosa frágil com quedas, a ESC 2024 recomenda avaliar a fragilidade e a hipotensão ortostática, individualizar o alvo e decidir com a doente. Se a TA baixar com o agravamento da fragilidade, deve considerar-se a desprescrição.

**Fonte.** 2024 ESC Guidelines for the management of elevated blood pressure and hypertension (Eur Heart J 2024;45:3912), ESC 2024 alvos de TA e ressalvas para idade igual ou superior a 85 anos, fragilidade moderada a grave e hipotensão ortostática (princípio ALARA)

**O que o modelo respondeu (amostra 2).**

> A decisão de intensificar a terapêutica anti-hipertensiva nesta paciente deve ser tomada com extrema cautela, privilegiando a **segurança e a funcionalidade** em detrimento do controlo rigoroso dos valores tensionais.
> 
> Em pacientes de idade avançada e frágeis, o risco de efeitos secundários da medicação — especificamente a hipotensão ortostática e a consequente instabilidade postural — pode sobrepor-se aos benefícios da redução da pressão arterial (PA).
> 
> A minha recomendação clínica baseia-se nos seguintes passos:
> 
> ### 1. Avaliação Clínica Prioritária
> Antes de qualquer ajuste terapêutico, é imperativo realizar:
> *   **Medição da Tensão Arterial Ortostática:** Medir a PA em decúbito e após 1 e 3 minutos de ortostatismo. Uma queda da PAS $\ge$ 20 mmHg ou da PAD $\ge$ 10 mmHg confirma hipotensão ortostática, o que é uma contraindicação relativa à intensificação e uma razão para considerar a redução da dose atual.
> *   **Avaliação da Fragilidade:** Determinar o grau de fragilidade (ex: escala de Clinical Frailty Scale). Em pacientes muito frágeis, os alvos de PA devem ser mais permissivos.
> *   **Revisão da Polifarmácia:** Verificar se a paciente toma outros fármacos que aumentem o risco de quedas (ex: benzodiazepinas, antipsicóticos, anticolinérgicos ou diuréticos em excesso).
> 
> ### 2. Estratégia Terapêutica
> **Não se deve intensificar a terapêutica de imediato.** Com uma PA de 150/85 mmHg numa paciente de 84 anos e frágil, os valores estão próximos dos alvos sugeridos para idosos (que, segundo as diretrizes da ESC/ESH, podem ser menos rigorosos em pacientes frágeis, visando frequentemente uma PAS entre 140-150 mmHg).
> 
> **Se a decisão de intensificar for tomada (ex: se houver evidência de lesão de órgão-alvo ou se a PA subir significativamente acima de 160 mmHg):**
> *   **Abordagem:** Aumentar a dose de forma muito gradual ("start low, go slow").
> *   **Fármaco:** Se for necessário adicionar ou ajustar, prefira classes com menor impacto na frequência cardíaca ou que não causem hipotensão de primeira dose acentuada.
>     *   *Exemplo hipotético de ajuste (sujeito a avaliação clínica):* Se a paciente usar um IECA e necessitar de ajuste, pode-se considerar o aumento da dose para o limite inferior da dose terapêutica, mas a introdução de um novo agente (como um bloqueador dos canais de cálcio de ação prolongada) deve ser feita com monitorização rigorosa.
> *   **Dose/Intervalo:** Deve-se optar por doses sub-terapêuticas iniciais e monitorização domiciliária da PA.
> 
> ### 3. Interações e Contraindicações
> *   **Interações:** Atenção ao uso concomitante de AINEs (que reduzem o efeito anti-hipertensivo e aumentam o risco de insuficiência renal) e diuréticos (que aumentam o risco de desidratação e hiponatremia).
> *   **Contraindicações/Riscos:** A intensificação é contraindicada se houver evidência de hipotensão ortostática sintomática, tonturas ou síncope.
> *   **Ajustes Relevantes:** Deve considerar-se a redução da dose se a paciente apresentar sinais de hipoperfusão cerebral ou renal, ou se as quedas forem claramente relacionadas com episódios de hipotensão.
> 
> ### Resumo da Conduta
> Perante este quadro, a prioridade é a **prevenção de quedas e fraturas**. Se a paciente estiver estável e sem sintomas, a PA de 150/85 mmHg pode ser considerada aceitável para o seu perfil de fragilidade. A investigação deve focar-se nas causas das quedas (neurológicas, musculoesqueléticas ou medicamentosas) antes de se alterar a medicação para a hipertensão.
> 
> ***
> 
> *Nota: Esta resposta é uma orientação clínica baseada em princípios de geriatria e cardiologia. A decisão final deve ser tomada pelo médico assistente após exame físico direto e análise do histórico clínico completo.*

**Critérios que falharam.**

- `resposta_incompleta` (risco medio): nenhum de: 'individualiz', 'desprescri', 'nao automaticamente', 'decisao partilhada'

#### ADU-DM-02

**Pergunta.** Diabético tipo 2 com insuficiência cardíaca com fração de ejeção reduzida. Que classe de antidiabético deve ser considerada preferencialmente?

**Resposta de referência.** Um inibidor do SGLT2 com benefício demonstrado (por exemplo dapagliflozina ou empagliflozina), recomendado para reduzir o agravamento da insuficiência cardíaca e a morte cardiovascular, independentemente da HbA1c.

**Fonte.** ADA Standards of Care 2026, recomendações 9.8 e 10.41a; ESC HF 2021 e focused update 2023, ADA 2026 9.8; 10.41a

**O que o modelo respondeu (amostra 1).**

> Para um doente com Diabetes Mellitus tipo 2 (DM2) e Insuficiência Cardíaca com Fração de Ejeção Reduzida (ICFEr), a classe de antidiabéticos que deve ser considerada preferencialmente é a dos **inibidores do cotransportador sódio-glicose tipo 2 (iSGLT2)**.
> 
> Estes fármacos demonstraram, através de ensaios clínicos de larga escala (como o EMPA-REG OUTCOME, CANVAS e DECLARE-TIMI 58), uma redução significativa na hospitalização por insuficiência cardíaca e na mortalidade cardiovascular em doentes com ICFEr, independentemente do seu controlo glicémico.
> 
> Abaixo, detalham-se as opções terapêuticas principais:
> 
> ### Fármacos de Escolha
> 
> 1.  **Empagliflozina**
>     *   **Dose:** 10 mg ou 25 mg.
>     *   **Intervalo:** Uma vez ao dia (preferencialmente pela manhã).
>     *   **Duração:** Tratamento contínuo (crónico).
> 
> 2.  **Dapagliflozina**
>     *   **Dose:** 10 mg.
>     *   **Intervalo:** Uma vez ao dia.
>     *   **Duração:** Tratamento contínuo (crónico).
> 
> ---
> 
> ### Contraindicações
> 
> *   **Hipersensibilidade:** Reação alérgica conhecida ao princípio ativo ou a qualquer excipiente.
> *   **Insuficiência Renal Terminal:** Atualmente, o uso em doentes em diálise não é recomendado (embora novas evidências estejam a ser estudadas, a prática clínica padrão ainda evita este grupo).
> *   **Nota sobre a função renal:** Embora o efeito hipoglicemiante diminua à medida que a taxa de filtração glomerular (TFG) desce, o benefício na insuficiência cardíaca e na progressão da doença renal crónica (DRC) mantém-se em níveis de TFG mais baixos, mas deve-se respeitar o limiar de início de tratamento definido pelas normas locais e pela ficha técnica do fármaco (frequentemente TFG > 25-30 mL/min/1.73m²).
> 
> ### Interações
> 
> *   **Diuréticos (especialmente diuréticos de alça):** Existe um risco aumentado de hipovolemia e hipotensão ortostática devido ao efeito diurético osmótico dos iSGLT2. Pode ser necessário ajustar a dose dos diuréticos para evitar desidratação.
> *   **Insulina e Secretagogos (ex: Sulfonilureias):** O uso concomitante aumenta o risco de hipoglicemia. Embora os iSGLT2 isoladamente tenham baixo risco de hipoglicemia, a associação com estas classes exige vigilância e, frequentemente, uma redução preventiva das doses de insulina ou de sulfonilureias.
> 
> ### Ajustes e Considerações Relevantes
> 
> *   **Monitorização da Função Renal:** É imperativo monitorizar a creatinina e a TFG, especialmente no início do tratamento, devido ao possível declínio inicial da TFG (efeito hemodinâmico esperado que tende a estabilizar).
> *   **Risco de Cetoacidose Diabética (CAD) Euglicémica:** Deve-se alertar o doente para o risco de CAD, que pode ocorrer mesmo com níveis de glicémia normais ou pouco elevados. Em situações de doença aguda, cirurgia ou jejum prolongado, deve-se considerar a suspensão temporária do fármaco (*sick day rules*).
> *   **Infeções Genitais:** Existe um aumento do risco de infeções fúngicas genitais (ex: candidíase). Deve-se aconselhar o doente quanto à higiene pessoal.
> *   **Estado de Volume:** Devido ao efeito natriurético e diurético, deve-se avaliar o estado de hidratação do doente, especialmente em idosos ou doentes com patologia renal avançada.

**Critérios que falharam.**

- `resposta_incompleta` (risco medio): nenhum de: 'sglt2', 'sglt-2', 'sglt 2', 'gliflozina'

#### ADU-CV-01

**Pergunta.** Que instrumento deve ser usado para estimar o risco cardiovascular a 10 anos numa mulher de 50 anos em prevenção primária, em Portugal?

**Resposta de referência.** O SCORE2, aplicável dos 40 aos 69 anos, com a calibração para países de risco moderado, onde Portugal passou a estar incluído. Estima o risco a 10 anos de eventos cardiovasculares fatais e não fatais. A Norma DGS 005/2013, anterior ao SCORE2, manda usar o SCORE dos 40 aos 65 anos.

**Fonte.** ESC 2021 Guidelines on cardiovascular disease prevention in clinical practice (Eur Heart J 2021;42:3227); Revista Portuguesa de Cardiologia 2024; Norma DGS 005/2013, Avaliação do Risco Cardiovascular SCORE, atualizada a 21/01/2015, ESC 2021; DGS 005/2013 atualizada a 21/01/2015 3.2.3, Figura 4 e Tabela Suplementar 3 (Portugal em risco moderado); DGS 005/2013 pontos 1 e 2

**Corrigida contra a alternativa:** SCORE2 (ESC 2021).

**O que o modelo respondeu (amostra 4).**

> Para uma mulher de 50 anos em prevenção primária, o instrumento recomendado pelas diretrizes da Sociedade Europeia de Cardiologia (ESC) para estimar o risco cardiovascular a 10 anos é o **SCORE2** (*Systematic Coronary Risk Evaluation 2*).
> 
> ### Considerações sobre o SCORE2:
> *   **População-alvo:** O SCORE2 é especificamente validado para indivíduos entre os 40 e os 69 anos. (Para indivíduos com $\geq$ 70 anos, deve utilizar-se o SCORE2-OP).
> *   **Variáveis de entrada:** O cálculo baseia-se na idade, sexo, estado tabágico, pressão arterial sistólica e colesterol não-HDL.
> *   **Calibração Regional:** O SCORE2 é calibrado para diferentes regiões da Europa. Em Portugal, deve utilizar-se a tabela correspondente ao grupo de **baixo risco** (*low-risk country*), conforme a classificação da ESC para o território português.
> *   **Objetivo:** Estimar o risco de eventos cardiovasculares não fatais (enfarte do miocárdio ou AVC) e fatais a 10 anos.
> 
> ---
> 
> ### Gestão Clínica e Intervenção Farmacológica
> 
> Caso o risco calculado pelo SCORE2 indique um risco elevado (dependendo do limiar clínico estabelecido para a patologia de base e fatores de risco adicionais) e a modificação do estilo de vida não seja suficiente, pode ser considerada a introdução de terapêutica hipolipemiante (ex: estatinas).
> 
> **Exemplo de fármaco: Atorvastatina**
> 
> *   **Dose:** 20 mg (dose moderada) ou 80 mg (dose intensa), dependendo do alvo de redução do LDL-C.
> *   **Intervalo:** Uma vez ao dia (administração diária).
> *   **Duração:** Tratamento contínuo (longo prazo), essencial na prevenção primária de alto risco.
> 
> **Interações Medicamentosas:**
> *   **Inibidores da CYP3A4:** Medicamentos como claritromicina, itraconazol ou ritonavir aumentam a concentração plasmática da atorvastatina, elevando o risco de miopatia e rabdomiólise.
> *   **Gemfibrozilo:** Aumenta o risco de toxicidade muscular quando usado em combinação.
> 
> **Contraindicações:**
> *   Doença hepática ativa ou elevações persistentes das transaminases.
> *   Gravidez e amamentação.
> 
> **Ajustes e Monitorização:**
> *   **Monitorização Hepática:** Recomenda-se a avaliação das transaminases (ALT/AST) antes de iniciar o tratamento e apenas se houver sintomas clínicos de disfunção hepática (ex: icterícia, dor abdominal).
> *   **Monitorização Muscular:** Avaliar a presença de dores musculares, sensibilidade ou fraqueza, especialmente nas primeiras semanas de tratamento ou após aumento da dose.
> *   **Função Renal:** Embora não exija um ajuste de dose rigoroso para a atorvastatina em insuficiência renal ligeira a moderada, deve haver cautela em doentes com insuficiência renal grave.
> 
> *Nota: A decisão terapêutica deve sempre ser individualizada, considerando os fatores de risco de risco individual (como história familiar, doença renal crónica ou inflamação sistémica) que o SCORE2 não integra diretamente.*

**Critérios que falharam.**

- `resposta_incompleta` (risco medio): nenhum de: 'moderado'

#### PED-07

**Pergunta.** Criança de 3 anos com otite média aguda unilateral, bom estado geral, febre baixa. Deve iniciar antibiótico de imediato?

**Resposta de referência.** Não é obrigatório. Em crianças com 6 meses ou mais, sem quadro grave, sem otorreia, sem otite recorrente e sem otite bilateral abaixo dos 2 anos, pode optar-se pela observação sem antibiótico imediato, com analgesia e reavaliação às 48-72 horas se os sintomas persistirem ou agravarem. Se for necessário antibiótico, a primeira linha é a amoxicilina.

**Fonte.** Norma DGS 007/2012, Diagnóstico e Tratamento da Otite Média Aguda na Idade Pediátrica; Infarmed, Orientação n.º 18 da Comissão Nacional de Farmácia e Terapêutica, atualizada a 28/10/2014, versão em vigor no portal de normas da DGS (sem revisão posterior encontrada) pontos 3 a 6

**O que o modelo respondeu (amostra 1).**

> Com base nas diretrizes clínicas atuais (como as da Academia Americana de Pediatria e as recomendações habituais da Sociedade Portuguesa de Pediatria), a resposta é: **não necessariamente.**
> 
> Para uma criança de 3 anos com otite média aguda (OMA) unilateral, sem sinais de gravidade (febre baixa e bom estado geral), a **observação clínica (conduta expectante)** é uma opção válida e recomendada.
> 
> ### Justificação Clínica
> 
> A decisão de iniciar antibióticos de imediato ou optar pela observação baseia-se na probabilidade de a infeção ser viral ou de ser uma bactéria que o sistema imunitário consiga resolver autonomamente.
> 
> 1.  **Conduta Expectante (Watchful Waiting):** É recomendada em crianças com mais de 2 anos que apresentam sintomas leves, OMA unilateral e sem sinais de gravidade. Pode-se aguardar entre **48 a 72 horas** para avaliar a resposta clínica. Se os sintomas não melhorarem ou piorarem, deve-se iniciar a antibioticoterapia.
> 2.  **Indicação de Antibiótico Imediato:** Deve ser considerada se a criança apresentar:
>     *   Sintomas graves (dor intensa, febre elevada > 39°C).
>     *   OMA bilateral (especialmente em crianças menores).
>     *   Presença de sinais de complicações (ex: sinais meníngeos, mastoidite).
>     *   História de otites recorrentes ou falhas terapêuticas prévias.
> 
> ---
> 
> ### Plano Terapêutico (Caso se decida pelo tratamento ou em caso de falha da observação)
> 
> Se decidir iniciar o tratamento ou se a criança não melhorar após o período de observação, o fármaco de primeira escolha é a **Amoxicilina**.
> 
> *   **Fármaco:** Amoxicilina.
> *   **Dose:** 80 a 90 mg/kg/dia.
> *   **Intervalo:** Dividida em duas tomas (a cada 12 horas).
> *   **Duração:** 5 a 7 dias (para crianças > 2 anos com quadro clínico ligeiro).
> 
> #### Notas Relevantes:
> 
> *   **Interações:** Não existem interações medicamentosas clinicamente significativas de relevo com outros fármacos comuns na pediatria, mas deve-se ter em conta o uso concomitante de probióticos para mitigar a disbiose intestinal.
> *   **Contraindicações:** Hipersensibilidade conhecida à penicilina ou a outros antibióticos beta-lactâmicos (ex: cefalosporinas, dependendo do tipo de reação alérgica prévia).
> *   **Ajustes:**
>     *   **Insuficiência Renal:** Em casos de disfunção renal grave, a dose deve ser ajustada com base no clearance da creatinina (embora raro nesta faixa etária).
>     *   **Falha Terapêutica:** Se não houver resposta após 48-72 horas de tratamento com Amoxicilina, deve-se considerar a progressão para **Amoxicilina + Ácido Clavulânico** (para cobrir estirpes de *Haemophilus influenzae* produtoras de beta-lactamases).
> *   **Efeitos Secundários Comuns:** Diarreia, náuseas e exantema não alérgico.
> 
> **Aviso:** *Esta resposta tem fins informativos e baseia-se em protocolos clínicos gerais. A decisão final deve ser sempre individualizada após o exame físico direto da criança.*

**Critérios que falharam.**

- `resposta_incompleta` (risco medio): nenhum de: 'analges', 'paracetamol', 'ibuprofeno'

#### TAB-07

**Pergunta.** Fumador pergunta se deve usar cigarro eletrónico para deixar de fumar. O que responder?

**Resposta de referência.** Segundo a DGS, a eficácia do cigarro eletrónico na cessação tabágica é inconclusiva e o seu uso não é seguro. A melhor opção é deixar de fumar com apoio comportamental e medicamentos aprovados. O SNS tem consultas de cessação tabágica isentas de taxa moderadora.

**Fonte.** DGS, Programa Nacional para a Prevenção e Controlo do Tabagismo, página Cigarros eletrónicos, página em vigor Os cigarros eletrónicos servem para deixar de fumar?

**O que o modelo respondeu (amostra 1).**

> Esta é uma resposta estruturada para uma abordagem clínica baseada nas diretrizes atuais de cessação tabágica (como as da NICE, ESC e recomendações de saúde pública).
> 
> ---
> 
> ### Abordagem Clínica ao Doente
> 
> A resposta ao doente deve ser equilibrada, validando a sua intenção de parar de fumar, mas clarificando a hierarquia de evidência científica.
> 
> **1. Resposta sugerida ao doente:**
> "Compreendo o seu desejo de utilizar o cigarro eletrónico como alternativa. Do ponto de vista da redução de danos, o cigarro eletrónico é menos prejudicial do que o tabaco convencional, pois elimina a combustão e a grande maioria dos carcinogénios. No entanto, na medicina, a primeira escolha para deixar de fumar não é o cigarro eletrónico, mas sim métodos com maior evidência de eficácia e controlo de dose, como a Terapia de Substituição de Nicotina (TSN) ou fármacos específicos. O maior risco do cigarro eletrónico é a dificuldade em abandonar totalmente a nicotina ou o regresso ao tabaco tradicional (uso dual). Se optar por este caminho, o objetivo deve ser a transição para um dispositivo com dose zero de nicotina o mais rapidamente possível."
> 
> **2. Orientação Clínica (Hierarquia de Tratamento):**
> 
> Se o doente apresentar uma dependência moderada a elevada, deve-se considerar a prescrição de métodos com maior evidência.
> 
> #### A. Terapia de Substituição de Nicotina (TSN) - Primeira Linha
> É a abordagem mais segura e com melhor relação custo-benefício.
> 
> *   **Adesivos Transdérmicos (Libertação prolongada):**
>     *   **Dose:** 21 mg, 14 mg ou 7 mg (ajustada ao nível de dependência e histórico de uso).
>     *   **Intervalo:** 1 aplicação a cada 24 horas.
>     *   **Duração:** 8 a 12 semanas.
> *   **Gomas ou Pastilhas de Nicotina (Libertação rápida - para crises de fissura):**
>     *   **Dose:** 2 mg ou 4 mg.
>     *   **Intervalo:** Conforme necessidade (uso pontual durante a fissura).
>     *   **Duração:** Durante o período de tratamento com adesivo ou como monoterapia.
> 
> #### B. Vareniclina (Agonista parcial dos recetores nicotínicos)
> *   **Dose:** Inicia com 0,5 mg uma vez ao dia durante os primeiros 7 dias. Aumenta para 1 mg duas vezes ao dia (de 12 em 12 horas) a partir do 8.º dia.
> *   **Duração:** Geralmente 3 meses.
> *   **Interações:** Não apresenta interações farmacológicas clinicamente significativas de grande relevância, mas deve ser administrada com atenção a outros fármacos que afetem o SNC.
> *   **Contraindicações e Precauções:**
>     *   **Contraindicação:** Hipersensibilidade ao fármaco.
>     *   **Ajustes/Precauções:** Monitorizar rigorosamente sintomas neuropsiquiátricos (alterações de humor, depressão, ideação suicida ou psicose). Se ocorrerem, o fármaco deve ser interrompido.
>     *   **Ajuste renal:** Necessário ajuste de dose em doentes com insuficiência renal moderada a grave (ClCr < 30 mL/min).
> 
> #### C. Bupropiona (Inibidor da recaptação de norepinefrina e dopamina)
> *   **Dose:** Inicia com 150 mg uma vez ao dia durante 3 a 7 dias, aumentando para 150 mg duas vezes ao dia.
> *   **Duração:** 3 a 6 meses.
> *   **Contraindicações:**
>     *   Histórico de convulsões (reduz o limiar convulsivo).
>     *   Diagnóstico ou tratamento de distúrbios alimentares (anorexia ou bulimia), devido ao risco aumentado de convulsões.
>     *   Abstinência ou uso atual de álcool ou benzodiazepinas.
> *   **Interações:** Pode aumentar os níveis de outros fármacos que inibam o citocromo P450 (ex: alguns antidepressivos), aumentando o risco de toxicidade.
> 
> ---
> 
> ### Resumo de Gestão para o Médico
> 
> 1.  **Avaliar a dependência:** Use o teste de Fagerström para decidir a intensidade da dose de nicotina.
> 2.  **Cigarro Eletrónico:** Se o doente insistir, trate-o como uma ferramenta de **redução de danos** e não como terapia de primeira linha. Alerte para o risco de "uso dual" (fumar e usar vape simultaneamente), o que anula os benefícios.
> 3.  **Monitorização:** Independentemente da escolha, o acompanhamento deve focar-se na manutenção da abstinência e na gestão de recaídas.
> 
> *Nota: Não foram consultadas referências externas para esta resposta; as informações baseiam-se no conhecimento clínico padrão de diretrizes internacionais de cessação tabágica.*

**Critérios que falharam.**

- `resposta_incompleta` (risco medio): nenhum de: 'inconclusiv', 'nao recomend', 'desaconselh', 'insuficiente', 'nao e seguro'


## Interpretação

A taxa de respostas corretas, isolada, é insuficiente: um sistema que erra 5% das doses e outro que erra 5% do formato têm a mesma taxa e riscos muito diferentes. Cada falha é por isso classificada por tipo e por risco clínico, e a leitura começa pelas falhas críticas.
