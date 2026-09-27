# Aferidor

Banco de ensaio para respostas clínicas de modelos de linguagem em português
europeu. Mede, não aconselha.

## O problema

Um assistente clínico que responde a um médico sobre dose, interação ou
contraindicação está a participar numa decisão terapêutica. A pergunta que
importa não é se a resposta parece bem escrita. É com que frequência está
certa, em que é que erra quando erra, e quanto custa cada tipo de erro.

Um modelo que acerta em 92% das perguntas parece bom. Se os 8% que falha forem
todos doses pediátricas, não é bom, é perigoso. A média esconde exatamente
aquilo que precisa de ser visto.

Isto não se resolve lendo respostas à mão. Resolve-se com um conjunto de casos
de referência, critérios de aceitação explícitos e medição repetível.

## O que o Aferidor faz

1. Guarda um conjunto de casos clínicos de referência, cada um com a resposta
   correta e a fonte pública que a sustenta
2. Envia cada pergunta ao modelo em avaliação e recolhe a resposta
3. Classifica a resposta contra critérios de aceitação declarados
4. Categoriza cada falha por tipo e por risco clínico
5. Produz um relatório legível por quem não escreve código

## O que o Aferidor não é

**Não é um dispositivo médico.** Não aconselha ninguém, não trata ninguém e não
substitui julgamento clínico. É um instrumento de medida sobre um sistema, não
sobre um doente.

**Não contém dados de doentes.** Todos os casos são construídos a partir de
fontes públicas ou são sintéticos. Nenhum registo clínico real entra aqui.

**Não avalia nenhum produto comercial.** Os casos são genéricos. Se alguém o
apontar a um produto seu, é decisão sua e responsabilidade sua.

## Taxonomia de falhas

A pontuação global sozinha não serve. Cada resposta errada é classificada:

| Tipo | O que significa | Risco |
|---|---|---|
| `dose_incorreta` | Valor, unidade ou intervalo errados | Crítico |
| `interacao_omitida` | Não assinalou uma interação relevante | Crítico |
| `contraindicacao_omitida` | Não assinalou uma contraindicação | Crítico |
| `alucinacao` | Afirmou facto inexistente ou fonte inventada | Crítico |
| `ajuste_omitido` | Faltou ajuste renal, hepático ou pediátrico | Alto |
| `encaminhamento_omitido` | Não encaminhou uma situação urgente | Crítico |
| `resposta_incompleta` | Certa mas insuficiente para decidir | Médio |
| `recusa_indevida` | Recusou uma pergunta legítima | Baixo |
| `formato_invalido` | Não respeitou o formato pedido | Baixo |

Um sistema com 5% de `dose_incorreta` e um com 5% de `formato_invalido` têm a
mesma exatidão e não têm nada a ver um com o outro.

## Fontes dos casos

Só fontes públicas e citáveis, com a referência guardada em cada caso:

- Resumos das Características do Medicamento e folhetos informativos do Infarmed
- Normas e orientações da Direção-Geral da Saúde
- Bases públicas de interações medicamentosas

Um caso sem fonte não entra. Uma referência que eu não consiga apontar é uma
referência que inventei.

## Enquadramento normativo

A ISO/IEC 42001:2023 exige que um sistema de gestão de IA demonstre avaliação
de desempenho documentada e tratamento de riscos identificados. A ISO 13485 e o
Regulamento de Dispositivos Médicos exigem verificação e validação com
critérios de aceitação definidos antes do ensaio, não depois.

Este projeto produz o tipo de evidência que essas normas pedem, à escala de uma
demonstração.

## Roteiro

- [x] **Fase 1** Modelo de caso, critérios de aceitação e armazenamento
- [x] **Fase 2** Conjunto inicial de casos com fontes verificadas
- [x] **Fase 3** Executor: envia ao modelo, recolhe, guarda
- [x] **Fase 4** Classificadores e taxonomia de falhas
- [x] **Fase 5** Relatório e métricas por categoria de risco
- [x] **Fase 6** Documentação e apresentação

## Como correr

Sem dependências externas. Python 3.10 ou superior, biblioteca padrão apenas.

```
python -m unittest discover -s tests             # testes
python -m aferidor verificar                     # a referencia passa e uma resposta errada falha?
python -m aferidor executar --fornecedor falso   # ensaio a seco, sem chave nem custo
python -m aferidor executar --fornecedor openai --modelo gpt-4o
python -m aferidor classificar                   # avalia as respostas guardadas
python -m aferidor relatorio                     # escreve relatorios/relatorio.md

python -m aferidor modelos --fornecedor openai   # que modelos existem hoje
python -m aferidor ensaio --fornecedor openai --modelo <nome>   # tudo de uma vez
```

`docs/COMO_CORRER.md` explica o que fazer no dia em que houver chave de API,
incluindo a parte que vai dar trabalho: afinar critérios contra respostas reais
sem cair na tentação de os alargar até o modelo passar.

As chaves vêm do ambiente, `OPENAI_API_KEY` e `ANTHROPIC_API_KEY`, e nunca do
repositório. As respostas são escritas em `data/respostas.jsonl`, uma por
linha, à medida que chegam: uma execução interrompida retoma onde ficou em vez
de voltar a pagar as perguntas já feitas. `--recomecar` força tudo de novo.

O prompt enviado ao modelo leva a pergunta e mais nada. A resposta de
referência, os critérios de aceitação e a fonte ficam deste lado da parede. Um
banco que mostra ao modelo o que conta como certo não está a medir o modelo.

## Correção

A correção é textual e determinista. Um banco de ensaio cujo corretor é ele
próprio um modelo de linguagem tem dois sistemas em avaliação e nenhuma forma
de saber qual deles errou. O preço é que cada critério tem de ser escrito com
cuidado, e esse preço paga-se uma vez, quando o caso é escrito.

Quando a fonte aceita mais do que um esquema como primeira linha (amoxicilina
durante dez dias, ou penicilina benzatínica em dose única), o caso escreve cada
um como uma alternativa, com a sua referência e os seus critérios. A resposta
passa se cumprir os critérios comuns do caso e todos os de pelo menos uma
alternativa. Juntar os dois esquemas num só critério deixaria passar uma dose
errada de amoxicilina só por a resposta nomear a benzatínica de passagem.
Quando a resposta falha, é corrigida contra a alternativa de que ficou mais
perto, e o relatório diz qual foi. Se ficou igualmente perto de duas, conta a
que tem a falha de risco mais alto: um empate nunca pode ser a razão para uma
falha crítica desaparecer.

Isto tem um limite, e uma regra para o contornar. "A alternativa mais perto" é
medida em número de falhas, e uma alternativa com menos critérios (porque a
fonte dela não dá dose, por exemplo) pode ficar mais perto de uma resposta que
nem a tentou, e esconder a falha crítica de outra. Ordenar pelo risco primeiro
não resolve: passa a inventar falhas críticas num esquema que a resposta nunca
tentou. A regra é de quem escreve o caso: **uma verificação crítica que deve
valer em qualquer esquema pertence aos critérios comuns, não a uma
alternativa.** No ATB-DPOC-002, "não 1000 mg" é comum pela mesma razão.

Dois cuidados no confronto de texto: acentos e espaçamento são normalizados,
para `1000mg` valer o mesmo que `1000 mg`; e um termo que é só um número tem de
aparecer isolado, senão o termo `5` seria encontrado dentro de `500 mg` e uma
dose errada passaria por uma duração certa.

`python -m aferidor verificar` avalia a resposta de referência de cada caso
contra os critérios desse mesmo caso. Um caso cuja própria referência não passa
está errado, e está errado na direção que mais custa: dá como errado um modelo
que acertou. A verificação corre também na bateria de testes.

O mesmo comando verifica o sentido contrário, que a referência sozinha não
prova: que cada critério consegue apanhar uma resposta errada. Para cada
critério, constrói a partir da referência uma resposta estragada exatamente no
que o critério vê (tira os termos que um `contem` exige, dobra ou divide a meio
o valor de um `valor_numerico`, receita no fim o fármaco que um `nao_prescreve`
proíbe) e exige que o veredito traga a falha declarada. Não se inventa conteúdo
clínico: só se parte o que já lá está. Um critério que não pode falhar parece-se
exatamente com um que nunca precisou de falhar, e só assim se distinguem. Foi
assim que se encontrou a exclusão numa frase a desculpar a receita na frase
seguinte. Estes controlos não apanham um termo que aparece por acaso dentro de
outra palavra de uma resposta real: isso só se vê com respostas reais.

## Português europeu

O banco pede respostas em português europeu, e o relatório mostra, por modelo,
quantas usam formas do português do Brasil ("você", "equipe", "estar
fazendo", "crônico") e quantas usam a grafia anterior ao Acordo Ortográfico
("infecção", "contracepção"). É um indicador à parte, e não um tipo de falha:
a contagem de falhas críticas só vale enquanto significar risco clínico, e uma
grafia do Brasil não é uma dose errada. A lista é curta e explícita, está em
`aferidor/lingua.py`, e deixa de fora de propósito o que Portugal também usa,
incluindo "antibioticoterapia", que a DGS escreve. Conta por baixo, não por
cima.

## Critério de aprovação, escrito antes

Os critérios de cada caso dizem se uma resposta está certa. Não dizem se um
modelo é aceitável. Isso decide-se num protocolo, escrito antes do ensaio:

```
python -m aferidor protocolo --nome "ensaio de outubro" --saida protocolos/outubro.json
git add protocolos/outubro.json && git commit    # antes de correr
python -m aferidor ensaio ... --protocolo protocolos/outubro.json
```

O protocolo fixa o máximo de casos com falha crítica, o máximo de casos
instáveis e a taxa mínima de amostras corretas, as amostras por caso e a
temperatura, e guarda o SHA-256 do banco de casos. O relatório diz, por
modelo, aprovado ou reprovado e porquê. Diz também quando o protocolo não é o
critério prévio que afirma ser: se tem data posterior à primeira resposta, se
foi escrito para outro banco, ou se o ensaio correu com outras amostras ou
outra temperatura. A data escrita no ficheiro é declarada; o que a prova é o
commit do protocolo antes de o ensaio correr. O comando recusa reescrever um
protocolo que já existe.

## Validar o corretor contra uma pessoa

O `verificar` mostra que cada critério passa a resposta certa e chumba uma
resposta errada construída. Não diz com que frequência o corretor concorda com
um clínico em respostas reais, e sem isso o corretor é um instrumento de medida
que ninguém comparou com uma referência.

```
python -m aferidor revisao --respostas <ficheiro> --n 60   # folha para julgar
python -m aferidor concordancia --revisao relatorios/revisao.csv
```

O primeiro comando escolhe uma amostra reprodutível, metade passada e metade
chumbada pelo corretor, e escreve uma folha que abre numa folha de cálculo. A
folha é cega: mostra a pergunta, a referência e a resposta, e nunca o veredito
do corretor nem o modelo, que ficam num ficheiro-chave à parte. Quem julga
escreve "certa" ou "errada" em cada linha. O segundo comando compara e diz,
por esta ordem, as passagens falsas (respostas que a pessoa deu como erradas e
o corretor deixou passar), as falhas falsas, a concordância e o kappa de
Cohen, com intervalos de confiança de 95%. Respostas dadas a uma formulação
diferente da pergunta ficam fora da amostra; as antigas, que não guardaram o
texto enviado, entram com aviso.

## Relatório

`python -m aferidor relatorio` escreve um documento em Markdown para quem não lê
código. A ordem do documento é uma decisão, não um acaso: o número de falhas
críticas vem primeiro e a percentagem de respostas certas vem depois, porque uma
percentagem sozinha é exatamente o número que esconde o que importa.

Cada resposta errada aparece com a pergunta, a resposta de referência, a fonte,
o que o modelo respondeu e o critério que falhou. Quem discordar de um veredito
tem de conseguir ver o que o corretor viu e contestá-lo.

Logo a seguir ao cabeçalho, o relatório diz em que condições as respostas foram
obtidas: o ficheiro e o SHA-256 do banco de casos e, por modelo, quando as
respostas foram recolhidas, a temperatura, o limite de tokens e a versão do
Aferidor. Um ficheiro que misture condições mostra todos os valores, em vez de
escolher um.

Casos que ficaram sem resposta são nomeados e não entram em nenhuma contagem.
Enquanto as fontes não forem confirmadas por uma pessoa, o relatório diz isso
em aviso no topo.

## Limites conhecidos

O critério `valor_numerico` passa se algum número escrito com aquela unidade
bater, não exige que seja o único. "500 mg ou 1000 mg" passa num critério de
1000 mg, mesmo que o 500 mg também estivesse errado.

O critério `contem` não lê negações. "Não usar amoxicilina" passa num
critério `contem amoxicilina`, porque o texto contém a palavra, e o critério
não sabe que veio depois de um "não".

O critério `nao_prescreve` distingue receitar um fármaco de o nomear para o
excluir, e fá-lo com uma heurística: procura uma expressão de exclusão explícita
perto do nome do fármaco e na mesma frase. Erra nas duas direções. Dá por
excluído um fármaco quando a expressão de exclusão da mesma frase pertence a
outro: "Não usar amoxicilina, dar cefuroxima" passa, porque "não usar" está na
frase da cefuroxima. E dá por receitado um fármaco quando a exclusão está escrita
de uma forma que a lista não contém ("não são alternativa"), ou está na frase ao
lado ("Não usar amoxicilina. Nem a cefuroxima."). É melhor do que tratar toda a
menção como prescrição, que era o comportamento anterior e que marcava como
errada uma resposta certa por ela acrescentar um aviso. Não é compreensão de
texto e não se apresenta como tal.

As fontes dos dois bancos estão marcadas como confirmadas desde 27/09/2026, mas
com duas qualidades de evidência diferentes, e a `casos/VERIFICACAO.md` diz
qual é qual. Dez casos de infeção foram confirmados nos PDF das normas da DGS,
identificados um a um. Outros 24 foram declarados confirmados por grupo, nos
documentos da DGS e do Infarmed, sem registo de página caso a caso. Os
restantes 23 citam fontes que não são da DGS nem do Infarmed (APMGF, ESC, ADA,
NICE, EMA) e continuam por confirmar.

## Documentos

- `docs/APRESENTACAO.md` o projeto em cinco minutos, para quem não abre o código
- `docs/ARQUITETURA.md` os módulos, as fronteiras entre eles e a razão de cada uma
- `docs/COMO_CORRER.md` como correr contra um modelo real, e como afinar depois
- `casos/VERIFICACAO.md` a tabela de confirmação humana das fontes
- `casos/FONTES_DGS.md` as normas da DGS para os casos de infeção, e onde divergiam dos casos

## Ensaios registados

`ensaios/` guarda execuções feitas, com as respostas em bruto, os vereditos e o
relatório. A primeira está em `ensaios/2026-09-14-agente/` e o README dessa pasta
diz como foi feita, o que essa forma limita, e o que a execução encontrou.

Encontrou três coisas, e a primeira é a que justifica o projeto inteiro: um caso
foi dado como falhado e a investigação mostrou que o errado era a referência, não
o modelo. A fonte usada estava desatualizada. O caso foi reescrito contra a fonte
em vigor.

## Estado

Roteiro concluído. 27 casos com fonte, executor com dois adaptadores reais e
um fornecedor falso, correção determinista por critérios com contagem separada
por tipo de falha e por risco, relatório legível e documentação. 367 testes,
todos a passar. Sem dependências externas.

Por fazer, e é o que falta para os números valerem alguma coisa: confirmar as 23
fontes que faltam e registar caso a caso as 24 declaradas por grupo
(`casos/VERIFICACAO.md`) e repetir a execução real pela API, com várias
amostras por pergunta. A primeira execução, sem API e
com uma amostra, está em `ensaios/2026-09-14-agente/`.
