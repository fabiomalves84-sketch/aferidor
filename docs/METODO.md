# Método

O que está por trás de cada número do Aferidor, e onde ele erra. O `README.md`
diz o que o projeto é e como o correr; este documento diz como mede.

## Fontes dos casos

Só fontes públicas e citáveis, com a referência guardada em cada caso, e a
fonte portuguesa oficial primeiro sempre que existe:

- Normas de orientação clínica da Direção-Geral da Saúde
- Resumos das Características do Medicamento e circulares do Infarmed, e textos
  da EMA
- O Guia de Bolso de Antibioterapia em Ambulatório da APMGF, onde a DGS não tem
  norma ou ao lado dela
- Diretrizes internacionais (ESC, ADA, NICE) onde não há fonte portuguesa, ou
  onde a norma portuguesa é anterior à evidência atual

Quando duas fontes reconhecidas dão respostas diferentes e ambas defensáveis, o
caso aceita as duas como alternativas, com a razão escrita. O levantamento das
normas da DGS, o que dizem e onde divergiam dos casos está em
`casos/FONTES_DGS.md`.

Um caso sem fonte não entra. Uma referência que eu não consiga apontar é uma
referência que inventei.

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

## Enquadramento normativo

A ISO/IEC 42001:2023 exige que um sistema de gestão de IA demonstre avaliação
de desempenho documentada e tratamento de riscos identificados. A ISO 13485 e o
Regulamento de Dispositivos Médicos exigem verificação e validação com
critérios de aceitação definidos antes do ensaio, não depois.

Este projeto produz o tipo de evidência que essas normas pedem, à escala de uma
demonstração.

## Ensaios registados

`ensaios/` guarda execuções feitas, com as respostas em bruto, os vereditos e o
relatório. A primeira está em `ensaios/2026-09-14-agente/` e o README dessa pasta
diz como foi feita, o que essa forma limita, e o que a execução encontrou.

Encontrou três coisas, e a primeira é a que justifica o projeto inteiro: um caso
foi dado como falhado e a investigação mostrou que o errado era a referência, não
o modelo. A fonte usada estava desatualizada. O caso foi reescrito contra a fonte
em vigor.

A segunda, em `ensaios/2026-09-16-comparacao-local-invalida/`, é uma medição
que falhou por culpa do instrumento: o limite de tokens cortava as respostas de
um modelo que raciocina antes de responder, e o corretor contava-as como erros.
Ficou guardada e explicada, e a terceira, em
`ensaios/2026-09-16-comparacao-local/`, é a mesma comparação feita em condições
(dois modelos locais, 27 casos, 5 amostras cada). Foi reclassificada a 27/09
com o corretor corrigido, sem repetir nenhuma pergunta e sem tocar nos
originais.

O quarto, em `ensaios/2026-09-27-locais-12-14b/`, é o primeiro feito com o
instrumento completo: protocolo de aprovação commitado antes da primeira
pergunta, condições gravadas em cada resposta, instrução com acentos e os casos
de infeção com as fontes da DGS. Dois modelos abertos maiores (Gemma 3 12B e
Phi-4 14B), 27 casos, 5 amostras. 270 de 270 respostas completas; os dois
modelos ficam reprovados pelo protocolo.

Depois de 27/09 vários casos mudaram de fonte e de pergunta (os de infeção
passaram para as normas da DGS). As respostas desses ensaios foram dadas às
perguntas de então, e os números que os READMEs dos ensaios registam são os do
instrumento dessa altura. Não servem para comparar com um ensaio novo.

## Roteiro

- [x] **Fase 1** Modelo de caso, critérios de aceitação e armazenamento
- [x] **Fase 2** Conjunto inicial de casos com fontes verificadas
- [x] **Fase 3** Executor: envia ao modelo, recolhe, guarda
- [x] **Fase 4** Classificadores e taxonomia de falhas
- [x] **Fase 5** Relatório e métricas por categoria de risco
- [x] **Fase 6** Documentação e apresentação
- [x] **Fase 7** Robustez do instrumento (27/09/2026): controlos negativos no
  `verificar`, condições de obtenção gravadas em cada resposta, esquemas
  alternativos, fontes da DGS, indicador de português europeu, intervalos de
  confiança
- [x] **Fase 8** Ferramentas de validação (27/09/2026): protocolo com critério
  de aprovação escrito antes, e folha cega para um clínico julgar o corretor
- [ ] **Fase 9** Validação: um clínico julga uma amostra de respostas reais, as
  fontes que faltam são confirmadas, e corre um ensaio pela API com protocolo
  feito antes
