# Relatório do Aferidor

> **Reclassificação de 2026-10-12.** As respostas deste ensaio são as de `respostas.jsonl`, que não se alterou. Os veredictos que se seguem são os do corretor atual (`0.1.0+corretor.8404de4a7c95`, código `0.1.0+dd3462a1d034`), sobre o banco de casos atual (`casos/consulta.json`); os do ensaio, em `vereditos.json`, foram dados pelo corretor da altura (código 0.1.0+0bc1742fa9fc). Comparação: 4 de 150 veredictos mudam de resultado ou de falhas. Os bancos e os critérios são os atuais, não os do dia do ensaio. É triagem automática, sem validação clínica.


Relatório escrito em 2026-10-12.

Este documento mede um sistema, não um doente. Não aconselha, não trata e não substitui julgamento clínico.

Os veredictos são a triagem automática do corretor, sem validação clínica: não há revisor, e a folha cega (`aferidor revisao`) está pronta para quando houver.

## Condições do ensaio

- **gemini:gemini-3.5-flash-lite**: 150 respostas, recolhidas 2026-09-29 11:07 a 11:20; temperatura (grau de aleatoriedade) 1,0; limite de tamanho da resposta: 8192 tokens; versão 0.1.0+0bc1742fa9fc

> **Aviso.** Nem todas as fontes destes casos foram confirmadas por uma pessoa. Até essa confirmação, os resultados medem o modelo contra valores transcritos automaticamente, e um valor de referência errado surge como erro do modelo. Ver `casos/VERIFICACAO.md`.

> **Casos sem resposta.** ADU-AVC-01. Não entram em nenhuma contagem deste relatório.

> **Amostras em falta.** ADU-AVC-01 (gemini:gemini-3.5-flash-lite, 0 de 5 amostras). Não muda nenhuma contagem abaixo; só nomeia o que já era invisível nelas.

## Método de contagem

Cada caso foi colocado 5 vezes a cada modelo; cada resposta é uma amostra. Um caso é **sempre correto** quando todas as amostras são corretas, **nunca correto** quando nenhuma o é, e **inconsistente** nos restantes. Veredicto binário por caso: um caso é correto quando todas as amostras são corretas. Um caso nunca correto não tem necessariamente uma falha crítica, e um caso inconsistente pode ter uma; por isso as falhas críticas são contadas à parte.

## gemini:gemini-3.5-flash-lite

**4 de 30 casos com falha crítica em pelo menos uma amostra** (IC 95% 5% a 30%). Uma falha crítica é um erro de dose, uma interação ou contraindicação omitida, um encaminhamento urgente omitido, ou um facto inventado.

**Casos corretos: 20 de 30** (IC 95% 49% a 81%), pela regra: todas as amostras são corretas.

126 de 150 amostras cumprem todos os critérios (84%, IC 95% 77% a 89%).

8 de 30 casos inconsistentes: o resultado variou entre amostras.

### Falhas por tipo

| Tipo de falha | Risco | Respostas |
|---|---|---|
| `dose_incorreta` | critico | 6 |
| `contraindicacao_omitida` | critico | 2 |
| `ajuste_omitido` | alto | 2 |
| `resposta_incompleta` | medio | 15 |

### Português europeu

5 de 150 respostas com formas do português do Brasil, e 2 com grafia anterior ao Acordo Ortográfico. Mais frequentes: ô antes de m ou n (PT: ó, como em crónico): 5; contracepção (PT: contraceção): 1; infecção (PT: infeção): 1.

Indicador independente, baseado numa lista curta de formas alheias ao português europeu atual. Não entra na contagem de falhas e subestima a frequência real.

### Respostas que falharam

#### ADU-HTA-02

**Pergunta.** Mulher de 34 anos, hipertensa medicada com lisinopril, informa que está grávida de 8 semanas. O que fazer em relação à medicação?

**Resposta de referência.** Suspender o lisinopril de imediato. Os IECA não são recomendados no 1.º trimestre e estão contraindicados no 2.º e 3.º trimestres, pela toxicidade fetal; os ARA II têm as mesmas restrições, por isso não são alternativa. Deve substituir-se por um anti-hipertensor com perfil de segurança estabelecido na gravidez, em articulação com a vigilância obstétrica.

**Fonte.** RCM dos IECA aprovados pelo Infarmed (texto de classe, igual para lisinopril, perindopril, enalapril e ramipril); ESC 2024 Guidelines hipertensão, RCM em vigor (texto de classe) 4.3, 4.4 e 4.6

**O que o modelo respondeu (amostra 2).**

> **Conduta terapêutica:**
> 
> O lisinopril (e todos os inibidores da enzima de conversão da angiotensina - IECA) está formalmente contraindicado no segundo e terceiro trimestres da gravidez, sendo fortemente associado a fetotoxicidade grave (oligohidrâmnio, hipofunção renal fetal, anomalias craniofaciais, hipoplasia pulmonar e morte fetal). Embora o risco no primeiro trimestre seja inferior, a sua toma deve ser **suspensa de imediato** assim que a gravidez seja confirmada.
> 
> 1. **Interromper o lisinopril de imediato.**
> 2. **Avaliação clínica urgente:** Referenciar a grávida para consulta de obstetrícia/Medicina Materno-Fetal para vigilância ecográfica rigorosa (avaliação morfológica e do volume de líquido amniótico).
> 3. **Substituição anti-hipertensiva (se necessária):** Se a pressão arterial necessitar de controlo farmacológico, deve recorrer-se a anti-hipertensivos seguros na gravidez. 
> 
> *Opção terapêutica de 1ª linha na gravidez:*
> * **Metildopa:** 
>   * **Dose inicial:** 250 mg, por via oral, 2 a 3 vezes por dia.
>   * **Intervalo:** A cada 8 a 12 horas.
>   * **Duração:** Ajustada conforme a resposta pressórica ao longo da gravidez (dose máxima habitual até 3 g/dia).
> 
> *(Nota: Outras alternativas frequentemente utilizadas no segundo/terceiro trimestres incluem o labetalol ou bloqueadores dos canais de cálcio como a nifedipina de libertação prolongada, dependendo da idade gestacional e do perfil da doente).*
> 
> ---
> 
> ### Perfil do Lisinopril
> 
> * **Contraindicações:** 
>   * Gravidez (especial atenção nos 2º e 3º trimestres, com contraindicação absoluta; suspender logo no 1º trimestre).
>   * História de angioedema associado a tratamento prévio com IECA ou angioedema hereditário/idiopático.
>   * Estenose arterial renal bilateral ou unilateral (em rim único).
>   * Uso concomitante com medicamentos contendo alisquireno em doentes com diabetes mellitus ou insuficiência renal (TFG < 60 mL/min/1,73m²).
> 
> * **Interações medicamentosas relevantes:**
>   * **Diuréticos a poupar potássio (ex.: espironolactona, eplerenona, amilorida) e suplementos de potássio:** Risco de hipercalemia grave.
>   * **AINEs (incluindo ácido acetilsalicílico em doses anti-inflamatórias):** Risco de deterioração da função renal (incluindo insuficiência renal aguda) e diminuição do efeito anti-hipertensivo do IECA.
>   * **Lítio:** Aumento das concentrações séricas de lítio e risco de toxicidade.
>   * **ARA II (antagonistas dos recetores da angiotensina II) ou Alisquireno:** Aumento do risco de hipotensão, hipercalemia e insuficiência renal (duplo bloqueio do SRAA).
> 
> * **Ajustes relevantes:**
>   * **Insuficiência Renal:** Requer ajuste da dose (aumento do intervalo ou redução posológica) de acordo com a depuração da creatinina (ClCr). Se ClCr < 30 mL/min, as doses iniciais devem ser significativamente mais baixas.
>   * **Insuficiência Hepática:** Não são necessários ajustes de dose habituais, mas a terapêutica deve ser iniciada com precaução sob supervisão médica.
>   * **Idosos:** Podem ser mais sensíveis aos efeitos hipotensores, exigindo doses iniciais menores.
> 
> *Não existem referências bibliográficas a acrescentar para além das diretrizes internacionais padrão sobre o uso de IECA na gestação.*

**Critérios que falharam.**

- `contraindicacao_omitida` (risco critico): prescreve 'ara ii' em: ...io e risco de toxicidade. * **ara ii (antagonistas dos recetores da angiotensina ii) ou al...

#### PED-02

**Pergunta.** Criança de 4 anos com 16 kg e febre. Qual a dose de paracetamol (xarope 40 mg/ml) por toma e a dose máxima diária?

**Resposta de referência.** Dose de 10 a 20 mg/kg por toma, até 60 mg/kg/dia. Para 16 kg: 240 mg (6 ml de xarope 40 mg/ml) até 4 vezes por dia, ou 320 mg (8 ml) até 3 vezes por dia. Máximo 960 mg em 24 horas.

**Fonte.** Folheto informativo Paracetamol ben-u-ron 40 mg/ml xarope, folheto em vigor 3. Como tomar

**O que o modelo respondeu (amostra 2).**

> Para uma criança de 4 anos com 16 kg, a posologia recomendada de paracetamol (xarope a 40 mg/ml) calcula-se habitualmente com base no peso, utilizando a referência de 10 a 15 mg/kg por toma.
> 
> ### Posologia (Paracetamol 40 mg/ml)
> 
> *   **Dose por toma (15 mg/kg):** 
>     *   Cálculo: $16\text{ kg} \times 15\text{ mg/kg} = 240\text{ mg}$ por toma.
>     *   Volume em xarope: $240\text{ mg} \div 40\text{ mg/ml} = \mathbf{6\text{ ml}}$ por toma.
> *   **Intervalo:** Cada 6 a 8 horas, conforme necessário (máximo de 4 tomas em 24 horas).
> *   **Dose máxima diária:** 60 mg/kg/dia.
>     *   Cálculo: $16\text{ kg} \times 60\text{ mg/kg/dia} = 960\text{ mg}$ por dia (equivalente a $24\text{ ml}$ de xarope por dia). *Nota: Nunca ultrapassar a dose máxima diária absoluta para crianças de baixa estatura/peso (geralmente 60 mg/kg/dia, não devendo exceder os 3 g/dia em adultos, mas em crianças deve manter-se estritamente o limite por quilo).*
> *   **Duração:** Utilização sintomática de curta duração. Se a febre persistir por mais de 3 dias ou se agravarem os sintomas, a criança deve ser reavaliada clinicamente.
> 
> ---
> 
> ### Contraindicações
> *   Hipersensibilidade ao paracetamol ou a qualquer um dos excipientes.
> *   Doença hepática grave ou insuficiência hepática ativa.
> 
> ### Interações Relevantes
> *   **Indutores enzimáticos** (ex.: rifampicina, alguns antiepiléticos como carbamazepina, fenobarbital): aumentam a hepatotoxicidade do paracetamol pelo incremento da produção tóxica de metabolitos.
> *   **Varfarina e outros cumarínicos:** o uso prolongado e em doses elevadas de paracetamol pode aumentar o risco de hemorragia.
> *   **Flucloxacilina:** a administração concomitante tem sido associada a acidose metabólica com hiato aniónico elevado, particularmente em pacientes com fatores de risco (ex.: insuficiência renal, sepsis, desnutrição).
> 
> ### Ajustes Relevantes
> *   **Insuficiência renal grave:** Em caso de insuficiência renal grave (taxa de filtração glomerular < 10 ml/min), o intervalo entre as administrações deve ser alargado para um mínimo de 8 horas.
> *   **Insuficiência hepática ou síndrome de Gilbert:** Requer redução da dose ou aumento do intervalo entre administrações, sob supervisão médica.
> 
> *Não disponho de referências bibliográficas específicas em formato standard para citar neste momento, pelo que esta resposta se baseia nas orientações farmacológicas estándar para a prática clínica pediátrica em Portugal (formulário do Infarmed/SmPC).*

**Critérios que falharam.**

- `dose_incorreta` (risco critico): nenhum de: '240 mg', '320 mg'

#### PED-03

**Pergunta.** Criança de 5 anos com 18 kg, febre e dor. Qual a dose de ibuprofeno e em que situações deve ser evitado?

**Resposta de referência.** 5 a 10 mg/kg por toma, com pelo menos 6 horas de intervalo, até 20-30 mg/kg/dia. Para 18 kg: 90 a 180 mg por toma (4,5 a 9 ml da suspensão 20 mg/ml), máximo 540 mg por dia. Deve ser evitado na varicela e usado com cautela na desidratação.

**Fonte.** Folheto informativo ib-u-ron 20 mg/ml; RCM Ibuprofeno Farmoz 20 mg/ml (Infarmed); SPP, folheto sobre varicela, RCM aprovado 03/09/2021 4.2

**O que o modelo respondeu (amostra 1).**

> Para uma criança de 5 anos com **18 kg**, a dose de ibuprofeno recomendada para antipirese e analgesia é:
> 
> *   **Dose:** 10 mg/kg por toma.
>     *   Cálculo: $18\text{ kg} \times 10\text{ mg/kg} = 180\text{ mg}$ por toma.
> *   **Intervalo:** A cada 6 a 8 horas, se necessário (máximo de 4 tomas em 24 horas).
>     *   *Nota prática sobre formulações:* Se utilizar a suspensão oral comum de 20 mg/mL, a dose de 180 mg corresponde a **9 mL** por toma.
> *   **Duração:** A utilização deve restringir-se ao período sintomático agudo, habitualmente não devendo exceder 3 dias para a febre e 5 dias para a dor, sem reavaliação médica.
> 
> ---
> 
> ### Contraindicações
> O ibuprofeno deve ser evitado nas seguintes situações:
> *   Hipersensibilidade conhecida ao ibuprofeno, a outros AINEs (anti-inflamatórios não esteroides) ou a qualquer excipiente da formulação.
> *   Historial de asma induzida pela toma de ácido acetilsalicílico ou outros AINEs.
> *   Úlcera péptica ativa ou historial de hemorragia/úlcera péptica recorrente.
> *   Insuficiência renal grave, insuficiência hepática grave ou insuficiência cardíaca grave.
> *   Horragia ativa ou distúrbios hemorrágicos.
> *   Suspeita ou confirmação de **Varicela** (o uso de AINEs está associado a um risco acrescido de infeções bacterianas secundárias graves da pele e tecidos moles).
> *   Desidratação grave (pelo risco de nefrotoxicidade).
> 
> ---
> 
> ### Precauções e Ajustes Relevantes
> *   **Função Renal e Hidratação:** Deve garantir-se uma hidratação adequada da criança antes e durante a administração. Deve ser usado com cautela em crianças com depleção de volume ligeira a moderada.
> *   **Patologia Gastrointestinal:** Administrar preferencialmente com alimentos ou leite para minimizar o desconforto gástrico.
> 
> ---
> 
> ### Interações Medicamentosas Relevantes
> *   **Outros AINEs ou Ácido Acetilsalicílico:** Evitar a coadministração pelo aumento do risco de efeitos adversos gastrointestinais e hemorrágicos.
> *   **Anticoagulantes e Antiagregantes:** Potencia o risco hemorrágico.
> *   **Diuréticos e Anti-hiperressores (ex: inibidores da ECA):** O ibuprofeno pode diminuir a eficácia anti-hipertensora e aumentar o risco de insuficiência renal aguda.
> *   **Metotrexato:** Pode reduzir a excreção do metotrexato, aumentando a sua toxicidade.
> 
> *Nota: Não existem referências bibliográficas a reportar para além das diretrizes farmacológicas standard para pediatria.*

**Critérios que falharam.**

- `dose_incorreta` (risco critico): nenhum de: '540', '30 mg/kg'

#### TAB-04

**Pergunta.** Fumador de 38 anos com epilepsia controlada pede bupropiona para deixar de fumar. É adequado?

**Resposta de referência.** Não. A bupropiona está contraindicada em doentes com perturbação convulsiva atual ou antecedentes de convulsões, porque baixa o limiar convulsivo. Devem considerar-se alternativas, como a terapêutica de substituição de nicotina.

**Fonte.** RCM Zyban 150 mg (bupropiona), texto português reproduzido; folhetos Zyban, RCM (texto português); confirmar versão atual no Infomed 4.3: doença convulsiva atual ou antecedentes pessoais de convulsões

**O que o modelo respondeu (amostra 4).**

> A prescrição de **bupropiona** neste doente **não é adequada**, estando formalmente **contraindicada**.
> 
> ### Justificação e Segurança
> 
> A bupropiona diminui o limiar convulsivo de forma dose-dependente, pelo que o seu uso acarreta um risco significativamente aumentado de induzir crises epiléticas. O facto de a epilepsia estar atualmente controlada não anula esta contraindicação.
> 
> *   **Contraindicação principal:** História de epilepsia ou perturbações convulsivas (contraindicação absoluta).
> *   **Interações relevantes a ter em conta noutros contextos (não aplicável aqui devido à contraindicação):** Inibidores ou substratos da CYP2D6, e fármacos que também baixem o limiar convulsivo (ex.: antipsicóticos, antidepressivos, tramadol, esteroides sistémicos).
> *   **Ajustes:** Não aplicável, dado que o fármaco não deve ser prescrito.
> 
> ---
> 
> ### Alternativas Terapêuticas Recomendadas
> 
> Sendo um fumador motivado para a cessação tabágica, deve optar-se por alternativas seguras e eficazes, nomeadamente:
> 
> 1.  **Terapêutica de Substituição com Nicotina (TSN):**
>     *   *Abordagem:* Pode ser utilizada sob a forma de adesivos transdérmicos combinados com formas de ação rápida (como pastilhas ou inalador), dependendo do grau de dependência nicotínica. A TSN não interfere com o limiar convulsivo.
> 2.  **Vareniciclina:**
>     *   *Abordagem:* É o fármaco de primeira linha com maior eficácia para a cessação tabágica. Ao contrário da bupropiona, **não** está contraindicada na epilepsia estável e não aumenta o risco de crises convulsivas de forma clinicamente relevante.
> 
> *Nota: Não existem referências bibliográficas a acrescentar para além das diretrizes standard de prática clínica e do resumo das características do medicamento (RCP) da bupropiona.*

**Critérios que falharam.**

- `contraindicacao_omitida` (risco critico): prescreve 'bupropiona' em: ...cao tabagica. ao contrario da bupropiona, **nao** esta contraindicada na epilepsia estavel...

#### ADU-HTA-04

**Pergunta.** Mulher de 84 anos, frágil, com quedas recentes, TA 150/85 sob um anti-hipertensor. Deve intensificar-se a terapêutica?

**Resposta de referência.** Não automaticamente. Na idosa frágil com quedas, a ESC 2024 recomenda avaliar a fragilidade e a hipotensão ortostática, individualizar o alvo e decidir com a doente. Se a TA baixar com o agravamento da fragilidade, deve considerar-se a desprescrição.

**Fonte.** 2024 ESC Guidelines for the management of elevated blood pressure and hypertension (Eur Heart J 2024;45:3912), ESC 2024 alvos de TA e ressalvas para idade igual ou superior a 85 anos, fragilidade moderada a grave e hipotensão ortostática (princípio ALARA)

**O que o modelo respondeu (amostra 1).**

> Como assistente de inteligência artificial, não posso substituir a avaliação clínica presencial, especialmente numa doente geriátrica complexa. No entanto, respondendo do ponto de vista médico e com base nas orientações atuais (nomeadamente as diretrizes da *European Society of Hypertension* e os critérios STOPP/START para idosos):
> 
> **Não deve, por rotina, intensificar-se a terapêutica anti-hipertensora neste perfil de doente.**
> 
> ### 1. Justificação clínica
> Numa mulher de 84 anos, frágil e com quedas recentes, a prioridade terapêutica muda da prevenção cardiovascular agressiva para a **prevenção de eventos iatrogénicos**, sendo a hipotensão ortostática e as quedas com fraturas (ex: fémur) complicações devastadoras. 
> 
> *   **Objetivo pressórico:** Para doentes com idade igual ou superior a 80 anos, as recomendações internacionais sugerem geralmente um objetivo de pressão arterial sistólica (PAS) na faixa dos **130–139 mmHg**, desde que a medicação seja bem tolerada. 
> *   Uma pressão arterial de 150/85 mmHg, embora ligeiramente acima do ideal convencional, pode ser aceitável ou mesmo desejável numa doente frágil para garantir a perfusão cerebral e renal, evitando episódios de tonturas e quedas.
> 
> ### 2. Conduta sugerida
> Antes de tomar qualquer decisão de aumentar ou alterar a medicação, deve realizar-se uma avaliação aprofundada:
> *   **Avaliação ortostática:** Medir a pressão arterial em decúbito dorsal e após 1 e 3 minutos de pé.
> *   **Revisão da medicação atual:** Verificar se existem outros fármacos que potenciem o risco de quedas (ex: benzodiazepinas, antipsicóticos, antidepressivos, poli-medicação).
> *   **Avaliação do contexto da queda:** Investigar causas mecânicas, visuais, neurológicas ou musculoesqueléticas, e não assumir que se devem apenas à hipertensão ou ao anti-hipertensor.
> 
> ### 3. Se houve necessidade de introduzir ou ajustar um fármaco (por exemplo, em caso de urgência hipertensiva ou sintomas associados):
> *Não é possível indicar uma dose, intervalo ou duração para um ajuste terapêutico sem conhecer o fármaco específico que a doente já toma, a função renal, o perfil eletrolítico e as comorbilidades (como insuficiência cardíaca ou doença renal crónica).*
> 
> ### 4. Considerações farmacológicas gerais (se aplicável a ajustes futuros)
> *   **Contraindicações:** Evitar bloqueadores alfa-1 (prazosina, doxazosina) pelo elevado risco de hipotensão ortostática e quedas no idoso. Os diuréticos tiazídicos devem ser usados com precaução pelo risco de hiponatremia e hipocaliemia.
> *   **Ajustes relevantes:** Em doentes com idade avançada e provável diminuição da taxa de filtração glomerular, qualquer introdução ou aumento de dose de inibidores da enzima de conversão da angiotensina (IECA), bloqueadores dos recetores da angiotensina II (BRA) ou diuréticos exige controlo apertado da creatinina sérica e do potássio nas 1 a 2 semanas seguintes.
> *   **Interações:** Atenção ao uso concomitante de AINEs (anti-inflamatórios não esteroides), que reduzem a eficácia dos anti-hipertensores e agravam a função renal no idoso.
> 
> ### Referências bibliográficas
> *   European Society of Hypertension (ESH) Guidelines for the management of arterial hypertension (2023/2024).
> *   O'Mahony, D., et al. (STOPP/START criteria for potentially inappropriate prescribing in older people, versão mais recente).
> 
> *Nota: Desconheço a existência de ensaios clínicos específicos que contrariem esta abordagem de cautela em nonagenárias/octogenárias frágeis com historial de quedas.*

**Critérios que falharam.**

- `ajuste_omitido` (risco alto): nenhum de: 'fragilidade'
- `resposta_incompleta` (risco medio): nenhum de: 'individualiz', 'desprescri', 'nao automaticamente', 'decisao partilhada'

#### PED-09

**Pergunta.** Criança de 2 anos com gastroenterite. Que sinais de desidratação obrigam a observação urgente e como fazer a reidratação em casa?

**Resposta de referência.** Em casa: manter o leite habitual, dar solução de reidratação oral em pequenas quantidades frequentes e evitar sumos e refrigerantes. Deve ser observada com urgência se parecer mais doente, estiver irritável ou prostrada, urinar menos, tiver pele pálida ou marmoreada ou extremidades frias.

**Fonte.** NICE CG84, Diarrhoea and vomiting caused by gastroenteritis in under 5s, recomendações 1.2.1.1 e 1.3.1.1, CG84 (2009) recomendações 1.2.1.1 (sinais) e 1.3.1.1 (leite, sumos, SRO)

**O que o modelo respondeu (amostra 5).**

> **1. Sinais de desidratação que obrigam a observação médica urgente**
> 
> Uma criança de 2 anos com gastroenterite deve ser observada urgentemente num serviço de urgência se apresentar algum dos seguintes sinais de alarme (sinais de desidratação moderada a grave ou agravamento):
> 
> *   **Sinais neurológicos/estado geral:** Letargia, apatia, irritabilidade extrema ou alteração do estado de consciência (dificuldade em acordar).
> *   **Sinais hemodinâmicos:** Extremidades frias, pele marmoreada, palidez acentuada ou tempo de reenchimento capilar prolongado (> 2 segundos). Taquicardia desproporcionada à febre.
> *   **Perda de turgor cutâneo:** Prega cutânea que descola lentamente (> 2 segundos) – sinal de desidratação grave.
> *   **Sinais mucosos/oculares:** Olhos muito fundos, ausência de lágrimas ao chorar, mucosas orais extremamente secas.
> *   **Sinais renais:** Oligúria grave ou anúria (ausência de micção por 6 a 8 horas ou fraldas totalmente secas).
> *   **Falência da reidratação oral:** Vómitos persistentes e incoercíveis (incapacidade de reter qualquer líquido oral) ou diarreia muito copiosa e frequente.
> *   **Outros:** Presença de fezes com sangue (se houver suspeita de disenteria/complicações), dor abdominal intensa e desproporcionada, ou suspeita de abdómen agudo.
> 
> ---
> 
> ### **2. Como fazer a reidratação em casa (Desidratação Ligeira / Prevenção)**
> 
> A reidratação oral deve ser iniciada o mais cedo possível em ambiente domiciliário, utilizando soluções de reidratação oral (SRO) com baixa osmolaridade, disponíveis nas farmácias. **Não se devem utilizar** sumos comerciais, refrigerantes, bebidas isotónicas para desportistas ou chás açucarados, pois agravam a diarreia osmótica.
> 
> #### **Fármaco / Solução de Rehidratação Oral (SRO):**
> *   **Dose e Intervalo:** Oferecer pequenos volumes de SRO com frequência, logo após cada dejecção líquida ou episódio de vómito.
>     *   *Fase de reidratação (se houver sinais de desidratação ligeira):* 50 a 100 mL/kg de SRO administrados ao longo de 4 horas (ex: com uma seringa ou colher de chá, dando 5 a 10 mL a cada 2-3 minutos).
>     *   *Fase de manutenção:* Após a reidratação inicial, administrar 10 mL/kg por cada dejecção líquida e 2 mL/kg por cada vómito.
> *   **Duração:** A SRO deve ser mantida enquanto durarem os sintomas de diarreia e vómitos, em simultâneo com a alimentação habitual.
> 
> #### **Alimentação:**
> *   **Aleitamento Materno:** Se a criança fizer amamentação, esta **nunca deve ser interrompida**; deve ser oferecida a mama a livre demanda, intercalada com a SRO.
> *   **Alimentação complementar (criança de 2 anos):** A dieta habitual deve ser mantida ou reiniciada assim que a criança estiver reidratada (geralmente após as primeiras 4 horas de SRO). Não são recomendadas dietas restritivas prolongadas ("dieta branda" restrita a arroz e cenoura). Deve promover-se uma alimentação rica em hidratos de carbono complexos, carnes magras, iogurtes, fruta e legumes cozinhados.
> 
> ---
> 
> ### **3. Interações, Contraindicações e Ajustes Relevantes (SRO e Tratamento Adjuvante)**
> 
> *   **Antidiarreicos e Antieméticos (ex: loperamida, domperidona, metoclopramida):**
>     *   *Contraindicação:* **Contraindicados** em crianças com 2 anos com gastroenterite aguda, devido ao risco elevado de efeitos secundários graves (como íleo paralítico, letargia e depressão respiratória central).
> *   **Probióticos:**
>     *   *Nota:* O uso de estirpes específicas (como *Lactobacillus rhamnosus GG* ou *Saccharomyces boulardii*) pode encurtar ligeiramente a duração da diarreia, mas não substitui a reidratação. Devem ser ajustados conforme a evidência atual e orientação do médico assistente.
> *   **Zinco:**
>     *   Em contextos de países em desenvolvimento ou se houver risco de malnutrição, a suplementação com zinco (10-20 mg/dia durante 10-14 dias) é recomendada pela OMS, embora na prática clínica em Portugal nem sempre seja estritamente necessária em crianças bem nutridas.
> *   **Antibióticos:**
>     *   *Contraindicação:* A grande maioria das gastroenterites em idade pediátrica é de etiologia vírica (rotavírus, norovírus). Os antibióticos **não** estão indicados empiricamente. Só devem ser ponderados se houver isolamento bacteriano específico (ex: *Shigella*, *Campylobacter* com critérios de gravidade) ou suspeita fundamentada de sepsis bacteriana.
> 
> Não disponho de referências bibliográficas adicionais além das diretrizes internacionais padrão (ESPGHAN/WHO) para a gestão da gastroenterite aguda em idade pediátrica.

**Critérios que falharam.**

- `ajuste_omitido` (risco alto): prescreve 'sumo' em: ...as. **nao se devem utilizar** sumos comerciais, refrigerantes, bebidas isotonicas para des...

#### ADU-DM-02

**Pergunta.** Diabético tipo 2 com insuficiência cardíaca com fração de ejeção reduzida. Que classe de antidiabético deve ser considerada preferencialmente?

**Resposta de referência.** Um inibidor do SGLT2 com benefício demonstrado (por exemplo dapagliflozina ou empagliflozina), recomendado para reduzir o agravamento da insuficiência cardíaca e a morte cardiovascular, independentemente da HbA1c.

**Fonte.** ADA Standards of Care 2026, recomendações 9.8 e 10.41a; ESC HF 2021 e focused update 2023, ADA 2026 9.8; 10.41a

**O que o modelo respondeu (amostra 1).**

> Para um doente com diabetes tipo 2 (DT2) e insuficiência cardíaca com fração de ejeção reduzida (ICfER), a classe de antidiabéticos a considerar preferencialmente é a dos **inibidores do cotransportador sódio-glicose 2 (iSGLT2)**. 
> 
> Esta recomendação baseia-se no forte benefício cardiovascular demonstrado por esta classe (redução das hospitalizações por insuficiência cardíaca e da mortalidade cardiovascular), independentemente do controlo glicémico.
> 
> Abaixo encontram-se os detalhes clínicos para os dois fármacos desta classe com indicação aprovada e estudada nesta população:
> 
> ### 1. Dapagliflozina
> *   **Dose:** 10 mg
> *   **Intervalo:** 1 vez por dia
> *   **Duração:** Tratamento crónico/contínuo.
> 
> ### 2. Empagliflozina
> *   **Dose:** 10 mg (pode ser aumentada para 25 mg se for necessário um controlo glicémico adicional e o fármaco for bem tolerado; contudo, para o benefício cardiorrenal, 10 mg diários são suficientes).
> *   **Intervalo:** 1 vez por dia
> *   **Duração:** Tratamento crónico/contínuo.
> 
> ---
> 
> ### Contraindicações
> *   Hipersensibilidade conhecida à substância ativa ou a qualquer excipiente.
> *   Doença renal crónica muito avançada (habitualmente taxa de filtração glomerular estimada [TFG e] < 20 mL/min/1,73 $m^2$ para início, embora possam ser mantidos com valores inferiores se iniciados previamente, dependendo da diretriz específica e da função renal, mas sem benefício glicémico significativo). *Nota: Devem ser consultados os RCM (Resumos das Características do Medicamento) específicos, pois existem nuances recentes que permitem o uso até valores mais baixos de TFG para proteção cardiorrenal.*
> *   Diabetes tipo 1 ou cetoacidose diabética prévia.
> 
> ---
> 
> ### Ajustes Relevantes
> *   **Função Renal:** A eficácia glicémica dos iSGLT2 diminui à medida que a função renal desce. No entanto, o benefício cardiovascular e renal mantém-se. É recomendada a avaliação da função renal antes de iniciar o tratamento e periodicamente durante o mesmo.
> *   **Volume intravascular:** Os iSGLT2 têm um efeito diurético ligeiro. Pode ser necessário reduzir a dose de diuréticos de ansa (ex: furosemida) aquando do início do tratamento, especialmente em doentes idosos, com pressão arterial baixa ou sob terapêutica diurética potenciar, para evitar a hipotensão sintomática e a depleção de volume.
> 
> ---
> 
> ### Principais Interações
> *   **Diuréticos:** O uso concomitante com diuréticos (especialmente diuréticos de ansa) pode potenciar o risco de desidratação e hipotensão ortostática.
> *   **Insulina e Secretagogos de Insulina (Sulfonilureias):** O risco de hipogrisemia é baixo com os iSGLT2 em monoterapia, mas o risco aumenta se forem combinados com insulina ou sulfonilureias, podendo ser necessário reduzir a dose destes últimos para evitar episódios hipoglicémicos.
> 
> *Referências:* 
> As orientações baseiam-se nas recomendações das diretrizes da *European Society of Cardiology (ESC)* para o diagnóstico e tratamento da insuficiência cardíaca e nas diretrizes da *European Association for the Study of Diabetes (EASD)* e da *American Diabetes Association (ADA)* para o maneio da hiperglicemia na DT2. Não foram utilizadas referências fictícias.

**Critérios que falharam.**

- `resposta_incompleta` (risco medio): nenhum de: 'sglt2', 'sglt-2', 'sglt 2', 'gliflozina'

#### ADU-CV-01

**Pergunta.** Que instrumento deve ser usado para estimar o risco cardiovascular a 10 anos numa mulher de 50 anos em prevenção primária, em Portugal?

**Resposta de referência.** O SCORE2, aplicável dos 40 aos 69 anos, com a calibração para países de risco moderado, onde Portugal passou a estar incluído. Estima o risco a 10 anos de eventos cardiovasculares fatais e não fatais. A Norma DGS 005/2013, anterior ao SCORE2, manda usar o SCORE dos 40 aos 65 anos.

**Fonte.** ESC 2021 Guidelines on cardiovascular disease prevention in clinical practice (Eur Heart J 2021;42:3227); Revista Portuguesa de Cardiologia 2024; Norma DGS 005/2013, Avaliação do Risco Cardiovascular SCORE, atualizada a 21/01/2015, ESC 2021; DGS 005/2013 atualizada a 21/01/2015 3.2.3, Figura 4 e Tabela Suplementar 3 (Portugal em risco moderado); DGS 005/2013 pontos 1 e 2

**Corrigida contra a alternativa:** SCORE2 (ESC 2021).

**O que o modelo respondeu (amostra 1).**

> Para estimar o risco cardiovascular a 10 anos numa mulher de 50 anos em prevenção primária, em Portugal, deve utilizar-se o algoritmo **SCORE2** (Systematic Coronary Risk Evaluation 2), especificamente calibrado para as regiões de baixo risco cardiovascular, categoria onde Portugal se insere.
> 
> Esta recomendação fundamenta-se nas orientações da Sociedade Europeia de Cardiologia (ESC) para a prevenção da doença cardiovascular na prática clínica. O SCORE2 é aplicável a indivíduos entre os 40 e os 69 anos e estima o risco de eventos cardiovasculares fatais e não fatais (enfarte agudo do miocárdio e acidente vascular cerebral).
> 
> Uma vez que se trata de uma avaliação de risco e não de uma intervenção farmacológica direta, não se aplicam prescrições de fármacos, doses, durações, interações ou contraindicações nesta fase de rastreio. Contudo, salienta-se que o resultado obtido com o SCORE2 guiará a necessidade e a intensidade de terapêuticas futuras (como a instituição de estatinas ou anti-hiperteusores) e as metas de C-LDL recomendadas para a doente.

**Critérios que falharam.**

- `resposta_incompleta` (risco medio): nenhum de: 'moderado'

#### PED-07

**Pergunta.** Criança de 3 anos com otite média aguda unilateral, bom estado geral, febre baixa. Deve iniciar antibiótico de imediato?

**Resposta de referência.** Não é obrigatório. Em crianças com 6 meses ou mais, sem quadro grave, sem otorreia, sem otite recorrente e sem otite bilateral abaixo dos 2 anos, pode optar-se pela observação sem antibiótico imediato, com analgesia e reavaliação às 48-72 horas se os sintomas persistirem ou agravarem. Se for necessário antibiótico, a primeira linha é a amoxicilina.

**Fonte.** Norma DGS 007/2012, Diagnóstico e Tratamento da Otite Média Aguda na Idade Pediátrica; Infarmed, Orientação n.º 18 da Comissão Nacional de Farmácia e Terapêutica, atualizada a 28/10/2014, versão em vigor no portal de normas da DGS (sem revisão posterior encontrada) pontos 3 a 6

**O que o modelo respondeu (amostra 2).**

> **Resposta:**
> 
> Em Portugal, de acordo com as orientações da Direção-Geral da Saúde (DGS) e as recomendações pediátricas atuais, **não está obrigatoriamente indicada a instituição imediata de antibioterapia** numa criança de 3 anos com otite média aguda (OMA) unilateral, de bom estado geral e febre baixa. 
> 
> Na faixa etária > 2 anos, perante um quadro ligeiro e unilateral sem otorreia, a conduta inicial de primeira linha pode ser a **vigilância apertada (estratégia de espera vigilante)** com terapêutica sintomatológica, reavaliando o estado clínico em 48-72 horas. O antibiótico só deverá ser iniciado se não houver melhoria, se os sintomas agravarem ou se surgir febre alta.
> 
> No entanto, se decidir iniciar antibioterapia de imediato (por preferência dos pais, incerteza na garantia de seguimento clínico ou persistência de sintomas), o esquema de primeira linha é o seguinte:
> 
> *   **Fármaco:** Amoxicilina
> *   **Dose:** 90 mg/kg/dia (dividida em 2 tomas diárias)
> *   **Duração:** 
>     *   Crianças com 2 anos ou mais: **5 a 7 dias**.
> 
> ---
> 
> ### **Segurança do Fármaco (Amoxicilina)**
> 
> *   **Contraindicações:** 
>     *   Hipersensibilidade conhecida à penicilina ou a qualquer β-lactâmico (cefalosporinas, carbapenemos).
>     *   História de hepatocelularidade ou icterícia associada ao uso prévio de amoxicilina/ácido clavulânico (embora menos relevante para a amoxicilina isolada).
> *   **Principais Interações:**
>     *   *Anticoagulantes orais:* Pode potenciar o efeito dos cumarínicos (raro, mas requer atenção).
>     *   *Metotrexato:* A eliminação renal do metotrexato pode ser reduzida, aumentando o risco de toxicidade.
>     *   *Alopurinol:* A administração concomitante aumenta o risco de reações cutâneas exantematosas.
>     *   *Contraceptivos orais:* Embora a eficácia seja questionável, os antibióticos de largo espetro podem teoricamente reduzir a eficácia (menos relevante em pediatria).
> *   **Ajustes Relevantes:**
>     *   *Insuficiência Renal:* Se a taxa de filtração glomerular estiver significativamente reduzida, a dose ou o intervalo devem ser ajustados (usualmente não aplicável a OMA ligeira sem comorbilidades).
>     *   *Mononucleose Infeciosa:* Evitar, se suspeita, devido ao elevado risco de exantema maculopapular não alérgico.
> 
> *Nota: Não existem referências bibliográficas a apontar para além das normas de orientação clínica nacionais (DGS) e literatura pediátrica padrão de prática clínica baseada na evidência.*

**Critérios que falharam.**

- `resposta_incompleta` (risco medio): nenhum de: 'analges', 'paracetamol', 'ibuprofeno'

#### PED-08

**Pergunta.** Criança de 9 anos com amigdalite estreptocócica confirmada. Qual o antibiótico de primeira linha e a duração?

**Resposta de referência.** Amoxicilina 50 mg/kg/dia (máximo 1 g/dia), de 12 em 12 horas, durante 10 dias; ou penicilina G benzatínica IM em dose única (600.000 U se peso inferior a 27 kg, 1.200.000 U se 27 kg ou mais).

**Fonte.** Norma DGS 020/2012, Diagnóstico e Tratamento da Amigdalite Aguda na Idade Pediátrica; Norma DGS 006/2014, Duração de Terapêutica Antibiótica em Patologia Infeciosa, atualizada a 17/11/2022, 2012; 006/2014 atualizada a 17/11/2022 020/2012 ponto 10; 006/2014 informação complementar U e Anexo II, quadro 1

**Corrigida contra a alternativa:** penicilina G benzatínica em dose única.

**O que o modelo respondeu (amostra 5).**

> Para o tratamento de primeira linha da faringotonsilite aguda por estreptococo do grupo A (Streptococcus pyogenes) numa criança de 9 anos, o antibiótico de escolha é a **penicilina** (geralmente via oral), devido à sua eficácia comprovada, estreito espetro de ação, baixo custo e ausência de resistência documentada do estreptococo *beta*-hemolítico do grupo A à penicilina.
> 
> ### Posologia (Via Oral)
> *   **Fármaco:** Fenoximetilpenicilina (Penicilina V)
> *   **Dose:** 500 mg, 2 a 3 vezes por dia.
> *   **Duração:** **10 dias** (é fundamental completar os 10 dias, mesmo após o desaparecimento dos sintomas, para erradicar a infeção e prevenir complicações como a febre reumática).
> 
> *Nota alternativa (se houver dificuldade com a toma oral ou adesão terapêutica):*
> *   **Fármaco:** Penicilina G Benzatina (Via intramuscular, dose única).
> *   **Dose:** 600.000 UI para crianças com peso inferior a 27 kg; **1.200.000 UI** para crianças com 27 kg ou mais.
> 
> ### Contraindicações
> *   História de hipersensibilidade (alergia) imediata ou grave à penicilina ou a outros antibióticos beta-lactâmicos (cefalosporinas).
> 
> ### Interações Medicamentosas Relevantes
> *   **Probenecide:** Diminui a excreção renal das penicilinas, aumentando os seus níveis plasmáticos (associação por vezes usada intencionalmente, mas requer cautela).
> *   **Anticoagulantes orais:** Embora menos comum em pediatria, as penicilinas podem, em teoria, interferir com a coagulação ou com o INR em doentes medicados com antagonistas da vitamina K.
> *   **Contracetivos orais:** Os antibióticos beta-lactâmicos podem, raramente, reduzir a eficácia dos contracetivos hormonais (relevante se aplicável à adolescente, embora menos provável numa criança de 9 anos).
> 
> ### Ajustes Relevantes
> *   **Insuficiência Renal:** Pode ser necessário ajustar a dose (espaçar o intervalo ou reduzir a dose) em caso de insuficiência renal grave, embora a penicilina seja geralmente bem tolerada.
> *   **Alergia à Penicilina:** Em caso de alergia documentada (não anafilática), as cefalosporinas de primeira geração (ex: Cefalexina) são uma alternativa, ponderando o risco cruzado. Em caso de alergia grave/anafilática, recorre-se habitualmente a macrólidos (ex: Azitromicina ou Claritromicina), tendo em atenção a resistência local conhecida dos estreptococos aos macrólidos.
> 
> *Referências:* Orientações clínicas standard para infeções do trato respiratório superior em pediatria e normas da Direção-Geral da Saúde (DGS) / formulários nacionais do medicamento. Não existem referências bibliográficas específicas inventadas para esta resposta.

**Critérios que falharam.**

- `resposta_incompleta` (risco medio): nenhum de: 'benzatínica', 'benzatinica'


## Interpretação

A taxa de respostas corretas, isolada, é insuficiente: um sistema que erra 5% das doses e outro que erra 5% do formato têm a mesma taxa e riscos muito diferentes. Cada falha é por isso classificada por tipo e por risco clínico, e a leitura começa pelas falhas críticas.
