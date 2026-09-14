# Ensaio de 14 de setembro de 2026

Primeira execução do Aferidor contra um modelo de linguagem real, e não contra o
fornecedor falso.

## Como foi feito, e o que isso limita

O modelo respondeu através de uma sessão do assistente, não através da API. Isso
tem consequências que é preciso dizer antes dos números:

- **Não houve controlo de temperatura.** Os adaptadores de API deste projeto
  pedem temperatura 0; aqui não foi possível fixá-la.
- **Uma amostra por pergunta.** Não há repetições, portanto não há forma de
  distinguir um erro sistemático de um acaso.
- **A identificação do modelo é a que a sessão declarava.** O modelo que serviu
  de facto cada resposta pode diferir.
- **As 18 perguntas foram repartidas por seis instâncias, três cada.** A
  repartição foi feita de propósito para que nenhuma instância visse os dois
  lados de um par: pneumonia com e sem comorbilidades, exacerbação ligeira e
  grave, hipersensibilidade tipo I e não tipo I. Se uma só instância respondesse
  a tudo, a segunda pergunta de cada par era respondida por quem já tinha visto a
  primeira, e o par deixava de medir a distinção.
- **As instâncias receberam apenas o enunciado.** Não viram as respostas de
  referência, nem os critérios de aceitação, nem este repositório.

**Isto não substitui uma execução pela API** e não deve ser apresentado como
tal. Serve para duas coisas: provar a cadeia inteira contra prosa real, e afinar
os critérios contra a forma como um modelo escreve de facto.

## Resultado

16 de 18 corretas. 2 respostas com falha de risco crítico, ambas do mesmo tipo.

## O que a execução encontrou, por ordem de importância

**1. Uma referência desatualizada, não um erro do modelo (AJU-MET-018).**

O caso da metformina em doente com depuração de 40 ml/min foi dado como falhado.
A investigação da divergência mostrou que o errado era o caso. Tinha sido escrito
a partir de uma circular do Infarmed de 2016, que dava 1500 mg/dia entre 60 e 30
ml/min. O RCM harmonizado europeu, posterior à revisão desse ano, dá 2000 mg/dia
entre 45 e 59 e 1000 mg/dia entre 30 e 44. O modelo respondeu 1000 mg/dia e tinha
razão.

O caso foi reescrito contra a fonte em vigor. O aviso sobre a validade desta
fonte já estava escrito em `casos/VERIFICACAO.md` antes da execução, e existia
precisamente para isto.

**2. Um critério que castigava a forma e não o conteúdo (INT-CLA-015).**

O critério exigia o radical `contraindicad`, que casa com "contraindicado" e
"contraindicada" mas não com "contraindicação". O modelo escreveu "classificada
como contraindicação", que é a resposta certa, e levou uma falha crítica de
interação omitida. O critério passou a usar o radical `contraindica`.

Esta é a correção que mais facilmente se transforma em batota, e por isso vale a
pena dizer onde está a linha: alargou-se o critério porque ele estava a castigar
uma flexão da mesma palavra, não porque o modelo precisava de passar.

**3. Duas divergências reais, que ficaram como falha (ATB-PAC-011, ATB-FAR-014).**

Na pneumonia com comorbilidades, o guia da APMGF dá amoxicilina 1000 mg com
azitromicina; o modelo respondeu amoxicilina com ácido clavulânico 875/125 mg com
macrólido. Na faringite com hipersensibilidade não tipo I, o guia dá cefuroxima
250 mg; o modelo respondeu cefadroxil 1 g.

Nenhuma das duas respostas é disparatada, e ambas são defensáveis noutras
orientações. Mas divergem da referência declarada, e este banco mede conformidade
com uma referência nomeada, não plausibilidade clínica geral. Ficaram como falha.

**Fica em aberto, e é decisão de quem escreve os casos:** estas duas divergências
estão hoje classificadas como `dose_incorreta`, que carrega risco crítico. O
modelo não errou uma dose, escolheu outro esquema. Classificar uma escolha de
esquema como erro crítico de dose inflaciona a contagem que mais importa, e a
contagem de falhas críticas só vale enquanto significar o que diz. A taxonomia
não tem hoje um tipo para divergência de norma.
