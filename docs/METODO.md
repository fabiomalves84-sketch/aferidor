# Método

Este documento descreve como o Aferidor mede e onde o método falha. O
`README.md` descreve o projeto e a sua utilização.

## Fontes dos casos

Apenas fontes públicas e citáveis, com a referência registada em cada caso, e
com prioridade para a fonte portuguesa oficial:

- Normas de orientação clínica da Direção-Geral da Saúde
- Resumos das Características do Medicamento e circulares do Infarmed; textos
  da EMA
- Guia de Bolso de Antibioterapia em Ambulatório da APMGF, na ausência de norma
  da DGS ou como complemento
- Diretrizes internacionais (ESC, ADA, NICE) na ausência de fonte portuguesa,
  ou quando a norma portuguesa é anterior à evidência atual

Quando duas fontes reconhecidas divergem e ambas são defensáveis, o caso aceita
as duas como alternativas, com a justificação registada. O levantamento das
normas da DGS e das divergências encontradas está em `casos/FONTES_DGS.md`.

Nenhum caso entra sem fonte identificável.

## Correção

A correção é textual e determinista. Um corretor baseado noutro modelo de
linguagem colocaria dois sistemas em avaliação, sem forma de determinar qual
errou. O custo é a exigência na redação de cada critério, incorrido uma única
vez, quando o caso é escrito.

**Alternativas.** Quando a fonte aceita mais do que um esquema de primeira
linha (amoxicilina durante dez dias ou penicilina benzatínica em dose única),
cada esquema é uma alternativa com referência e critérios próprios. A resposta
é correta se cumprir os critérios comuns e todos os de pelo menos uma
alternativa. Um critério único para ambos os esquemas aceitaria uma dose
errada de amoxicilina apenas por a resposta mencionar a benzatínica. Uma
resposta incorreta é avaliada contra a alternativa mais próxima (menor número
de falhas), que o relatório identifica; em caso de empate, prevalece a
alternativa com a falha de risco mais alto, para que um empate nunca oculte
uma falha crítica.

Esta regra tem um limite: uma alternativa com menos critérios (por exemplo,
cuja fonte não indica dose) pode ficar mais próxima de uma resposta que não a
seguiu e ocultar a falha crítica de outra. Ordenar primeiro pelo risco também
não resolve, porque atribuiria falhas críticas a esquemas que a resposta não
seguiu. A regra de redação é: **uma verificação crítica que deve valer em
qualquer esquema pertence aos critérios comuns, não a uma alternativa.** No
ATB-DPOC-002, "não 1000 mg" é um critério comum por esse motivo.

**Normalização.** Acentos e espaçamento são normalizados (`1000mg` equivale a
`1000 mg`). Um termo exclusivamente numérico tem de aparecer isolado; caso
contrário, `5` seria encontrado em `500 mg` e uma dose errada passaria por uma
duração correta.

**Verificação do corretor.** `python3 -m aferidor verificar` avalia a resposta
de referência de cada caso contra os seus próprios critérios. Um caso cuja
referência não passa está defeituoso no sentido mais grave: classifica como
errado um modelo que acertou. O mesmo comando verifica o sentido inverso: para
cada critério, constrói a partir da referência uma resposta errada no ponto
exato que o critério avalia (remove os termos exigidos por `contem`, duplica
ou divide o valor de `valor_numerico`, acrescenta a prescrição proibida por
`nao_prescreve`) e exige que o veredicto registe a falha. Nenhum conteúdo
clínico é inventado; apenas se altera o que já existe. Estes controlos não
detetam um termo contido acidentalmente noutra palavra de uma resposta real;
isso só se observa com respostas reais. O comando avisa também, sem falhar,
quando um critério positivo se cumpre só com o texto da pergunta, porque não
distingue uma resposta de uma repetição da pergunta; corrigi-lo é reescrever
o critério, com a razão no commit. Para os critérios negativos há dois
controlos adicionais: uma recusa seguida do termo proibido, porque um marcador
de recusa não pode ocultar uma prescrição, e, em `nao_prescreve`, a afirmação
de que o fármaco não está contraindicado. A verificação corre também na
bateria de testes.

## Estados e veredicto por caso

Cada caso é colocado várias vezes a cada modelo; cada resposta é uma amostra.
Um caso é **sempre correto** (todas as amostras corretas), **parcialmente
correto** ou **nunca correto**. O veredicto binário por caso segue uma de três
regras, fixada no protocolo: `todas` (todas as amostras corretas; regra por
omissão), `maioria_sem_critica` (maioria correta e nenhuma falha crítica) ou
`nenhuma_critica` (nenhuma falha crítica). As falhas críticas são contadas à
parte: um caso nunca correto pode não ter nenhuma, e um caso parcialmente
correto pode ter uma.

## Critério de aprovação prévio

Os critérios de cada caso determinam se uma resposta é correta, não se um
modelo é aceitável. Essa decisão é definida num protocolo, antes do ensaio:

```
python3 -m aferidor protocolo --nome "ensaio de outubro" --saida protocolos/outubro.json
git add protocolos/outubro.json && git commit    # antes de correr
python3 -m aferidor ensaio ... --protocolo protocolos/outubro.json
```

O protocolo fixa o máximo de casos com falha crítica, o máximo de casos
parcialmente corretos, a taxa mínima de amostras corretas, o número de
amostras por caso, a temperatura e a regra do caso (`regra_do_caso`), e
regista o SHA-256 do banco. O relatório indica, por modelo, aprovado ou
reprovado e o motivo. Assinala também quando o protocolo não constitui um
critério prévio: data posterior à primeira resposta, banco diferente, ou
amostras e temperatura diferentes. Um modelo só é aprovado se tiver respondido
a todos os casos do banco em todas as amostras; por isso, `--protocolo` não
aceita `--limite`, e o protocolo é lido antes do primeiro pedido. A data no
ficheiro é declarativa; a prova é
o commit do protocolo antes do ensaio. O comando recusa reescrever um
protocolo existente.

## Validação do corretor por um clínico

O `verificar` demonstra que cada critério aceita a resposta correta e rejeita
uma resposta errada construída. Não mede a concordância do corretor com um
clínico em respostas reais.

```
python3 -m aferidor revisao --respostas <ficheiro> --n 60   # folha para julgar
python3 -m aferidor concordancia --revisao relatorios/revisao.csv
```

O primeiro comando seleciona uma amostra reprodutível (metade aprovada e
metade reprovada pelo corretor) e escreve uma folha de cálculo cega: mostra a
pergunta, a referência e a resposta, mas não o veredicto nem o modelo, que
ficam num ficheiro-chave separado. O avaliador escreve "certa" ou "errada" em
cada linha. O segundo comando apresenta, por esta ordem, as aprovações
indevidas (respostas julgadas erradas que o corretor aprovou), as reprovações
indevidas, a concordância e o kappa de Cohen; as três primeiras com
intervalo de confiança a 95%. A amostra é estratificada (metade aprovada e
metade reprovada pelo corretor), pelo que a concordância e o kappa descrevem a
amostra e não a execução; as taxas de aprovações e reprovações indevidas,
condicionais ao juízo do avaliador, são as que se aplicam à execução. Respostas a uma formulação diferente da pergunta são excluídas da
amostra; respostas antigas, sem registo do texto enviado, são incluídas com
aviso.

## Português europeu

O relatório indica, por modelo, quantas respostas usam formas do português do
Brasil ("você", "equipe", "estar fazendo", "crônico") e quantas usam a grafia
anterior ao Acordo Ortográfico ("infecção", "contracepção"). É um indicador
independente e não um tipo de falha, porque a contagem de falhas críticas deve
refletir apenas risco clínico. A lista é curta e explícita (`aferidor/lingua.py`)
e exclui formas também usadas em Portugal, como "antibioticoterapia", que a DGS
utiliza. Subestima a frequência real.

## Relatório

`python3 -m aferidor relatorio` produz um documento em Markdown ou HTML. As
falhas críticas surgem antes da percentagem de respostas corretas, porque a
percentagem isolada oculta o que importa.

Cada resposta incorreta é apresentada com a pergunta, a referência, a fonte, a
resposta do modelo e o critério não cumprido, para que qualquer veredicto
possa ser verificado e contestado. O relatório indica as condições de
obtenção: ficheiro e SHA-256 do banco e, por modelo, datas de recolha,
temperatura, limite de tokens e versão do Aferidor. Quando um ficheiro mistura
condições, todos os valores são apresentados.

Casos sem resposta são identificados e excluídos das contagens. Enquanto as
fontes não estiverem confirmadas por uma pessoa, o relatório sinaliza-o no topo,
com uma etiqueta "fontes por confirmar" que liga ao aviso completo, que vem logo
a seguir aos cartões dos modelos.

## Limites conhecidos

**`valor_numerico`** aceita a resposta se algum número com a unidade indicada
coincidir, sem exigir que seja o único: "500 mg ou 1000 mg" passa num critério
de 1000 mg.

**`contem`** não interpreta negações: "Não usar amoxicilina" passa num
critério `contem amoxicilina`.

**`nao_prescreve`** distingue prescrever um fármaco de o mencionar para o
excluir através de uma heurística: procura uma expressão de exclusão explícita
próxima do nome do fármaco e na mesma frase. Falha nos dois sentidos. Dá como
excluído um fármaco quando a expressão de exclusão pertence a outro ("Não usar
amoxicilina, dar cefuroxima"); dá como prescrito um fármaco quando a exclusão
usa uma forma ausente da lista ("não são alternativa") ou está noutra frase
("Não usar amoxicilina. Nem a cefuroxima."). A negação de uma exclusão ("não
está contraindicada", "sem contraindicação") conta como prescrição. A
expressão de exclusão pode vir depois do nome até ao fim da frase, porque em
português o predicado segue o sujeito inteiro ("Os DOAC (…) estão
contraindicados"). Uma menção posterior a um fármaco que a resposta já excluiu
só conta como prescrição se tiver perto, na mesma frase, uma dose, um verbo
de prescrever ou a negação da exclusão; sem isso, é a resposta a explicar a
exclusão. Continua a errar no sentido conservador em construções como "ao
contrário da bupropiona, [a vareniclina] não está contraindicada". É preferível ao comportamento
anterior, que tratava qualquer menção como prescrição e reprovava respostas
corretas que incluíam um aviso. Não constitui compreensão de texto.

**Duas falhas falsas conhecidas, deixadas como estão por decisão.** Ambas dão
errado, no corretor atual, um modelo que acertou em substância: a direção que
mais custa.

- *ADU-HTA-02, amostra 4 do Gemma 4 26B A4B (consulta).* A resposta lista os ARA
  II sob um título de contraindicações absolutas na gravidez, mas o título fica
  fora da janela de 70 carateres que antecede o nome do fármaco, e o corretor
  não o liga ao losartan. A regra de título de lista (um marcador num título
  que vale para os itens abaixo) não foi implementada.
- *INT-COL-016, amostra 3 do Gemma 4 26B A4B (banco principal).* A resposta
  escreve "se for inevitável (ex.: claritromicina…)" antes de dizer "evitar a
  combinação". O `nao_prescreve` falha qualquer menção que não esteja excluída
  nessa frase, e a primeira o não está. O desenho não foi alterado.

Ambas já falhavam antes da afinação; passaram por coincidência com um
marcador demasiado largo e voltaram à falha quando as correções de fronteira de
frase e de início de palavra o desfizeram. Estão descritas nas mensagens dos
commits `f202e37` e `886f637`.

**`nao_prescreve` e o marcador `evit`: um falso passe, a direção que deixa passar
um erro.** O marcador `evit` conta como exclusão em qualquer ponto da janela do
fármaco (até 70 carateres antes do nome, até 200 depois, dentro da mesma frase),
sem exigir que o "evitar" diga respeito ao fármaco. Executado a 10/10/2026 contra
um `nao_prescreve claritromicina`:

- "Pode usar claritromicina 500 mg 12/12h; evitar tomar em jejum." passa
  (`nenhum fármaco excluído foi prescrito`).
- "A claritromicina é uma boa opção, sem problemas, evitando atrasos no
  tratamento." passa.

São frases construídas, não respostas de modelos. Para saber quanto pesa nas
respostas reais, corrigiram-se as 1400 respostas dos `ensaios/` que têm
`casos.json` com o `evit` retirado da lista, só em memória: 19 veredictos mudam,
todos de passa para falha. Os 19 foram lidos um a um, **por leitura do Claude
Code, sem revisão clínica**:

- *16 exclusões legítimas* (o `evit` está a fazer o que deve): por exemplo, "Deve-se
  evitar a utilização de ibuprofeno em crianças com varicela" (PED-04, Gemma 4
  31B, amostra 2), "Evitar sumos de fruta, refrigerantes e
  bebidas desportivas" (PED-09, Gemma 4 26B A4B) e "deve-se evitar a
  claritromicina" (INT-COL-016, Gemma 4 26B A4B).
- *2 discutíveis*, exclusões parciais: PED-09, Gemini 3.5 Flash Lite, amostra 2
  ("evitando açúcares refinados e sumos hiperosmolares") e PED-09, Gemma 4 31B,
  amostra 2 ("evitando-se apenas sumos excessivamente doces"). A referência manda
  evitar sumos em geral.
- *1 provável falso passe*: PED-04, Gemini 3.5 Flash Lite, amostra 5. A resposta
  diz "deve utilizar-se **paracetamol** (ou ibuprofeno, embora o paracetamol seja
  frequentemente preferido em fases iniciais da varicela, devendo evitar-se o
  ibuprofeno em caso de suspeita de infeção bacteriana secundária da pele)".
  Apresenta o ibuprofeno como opção, e o critério crítico do caso é que o
  ibuprofeno se evita na varicela. O `evit` da segunda metade da frase desculpa a
  primeira.

Não se encontrou nenhuma resposta que prescreva claramente o fármaco proibido.
O marcador não pode simplesmente sair: 16 de 19 são exclusões que dependem dele.

*Uma inconsistência no mesmo caso.* No `vereditos.json` gravado do ensaio de
29/09 (Gemini no banco de consulta, corretor anterior às afinações), a amostra 4
do PED-04 está como falha `contraindicacao_omitida`, e é uma exclusão clara
("Deve ser evitado o uso de anti-inflamatórios não esteroides (AINEs), como o
ibuprofeno"); a amostra 5, que oferece o ibuprofeno como opção, passou. O corretor
falhou a resposta certa e passou a duvidosa. Com o corretor atual as cinco
amostras passam: a 4 deixou de falhar com as afinações posteriores, a 5 continua a
passar.

*O que mudaria se a amostra 5 fosse falha, e em que base.* O "4 de 30" do README
e da tabela de ensaios deste documento é a base do **corretor atual** (nota ¹); o
"6 de 30" do README e do relatório da pasta do ensaio
(`ensaios/2026-09-29-gemini-consulta/`) é a dos **veredictos gravados**, e
nela o PED-04 já conta como falha crítica por causa da amostra 4.

| Base | Casos com falha crítica | Casos parcialmente corretos | Amostras corretas | Se a amostra 5 fosse falha |
|---|---|---|---|---|
| Veredictos gravados | 6 de 30 (10% a 37%) | 10 | 122 de 150 | o destaque **não muda**; só as amostras corretas passam a 121 de 150 |
| Corretor atual | 4 de 30 (5% a 30%) | 8 | 126 de 150 | 5 de 30 (7% a 34%), 9 parcialmente corretos, 125 de 150 |

O protocolo continua reprovado nas duas bases, e o p do McNemar entre o Gemini e o
Gemma 4 31B no banco de consulta fica em 1,000 (corretor atual: discordantes 2 e 2
passam a 1 e 2). Nada foi reclassificado, e os ensaios registados não foram
alterados.

*O que o `verificar` não apanha.* Os controlos negativos do `nao_prescreve`
acrescentam "Iniciar X" à referência (e variantes com recusa e com "não está
contraindicado"), nunca uma prescrição com "evitar" na mesma frase, por isso este
limite passa nos controlos todos. Não se propõe aqui nenhuma alteração ao corretor.

**Dois identificadores da versão: o `build_id` e o `grader_id`.** O `build_id` é a versão mais os primeiros 12 caracteres do SHA-256 de todos os `aferidor/*.py` (`code_digest`, em `aferidor/__init__.py`). Está gravado em cada resposta (campo `versao`) e é o que um protocolo com `--congelar-corretor` fixa em `versao_corretor`. Muda com qualquer edição a qualquer módulo, incluindo o relatório HTML, a folha de estilo e as traduções: um protocolo congelado assim diz "o corretor mudou depois do protocolo" mesmo quando só mudou a apresentação, e recusa um `ensaio` novo. Os dois protocolos do Gemma 4 26B A4B fixaram o `build_id` e continuam a dizê-lo. O `grader_id` (`0.1.0+corretor.` seguido de 12 caracteres) é o SHA-256 de seis ficheiros apenas: `checks.py`, `grading.py`, `models.py`, `risk.py`, `storage.py` e `protocolo.py` (a lista `GRADER_FILES`, em `aferidor/__init__.py`). Um teste cobre os seis ficheiros de `GRADER_FILES`: o que importam, direta ou indiretamente, tem de estar na lista, com uma única exceção declarada, `protocolo.py`, que pode importar `__init__` (para o `build_id`) e `traducao` (para redigir mensagens), porque nenhum dos dois entra na regra de aprovação. Cada resposta nova grava-o também (campo `corretor`), e `--congelar-correcao` fixa-o no protocolo (`corretor_id`). **Recomenda-se `--congelar-correcao`: só muda quando muda um destes seis ficheiros, por isso um aviso «o corretor mudou» deixa de ser provocado por edições ao relatório, à interface ou às traduções.** O que o `grader_id` **não** cobre: os critérios, que são dados (`casos/*.json`) e ficam cobertos pelo `banco_sha256` do protocolo; e o texto do pedido, que fica coberto pelo `prompt_sha256` de cada resposta. Também muda com edições a esses seis ficheiros que não afetam a correção (a estatística de `grading.py`, a leitura e a escrita de respostas em `storage.py`, os avisos de `protocolo.py`): prefere-se avisar a mais do que a menos. O `build_id` inteiro continua gravado em cada resposta, por isso continua a ser possível saber se o pacote mudou.

Um protocolo com `corretor_id`, aplicado a respostas registadas antes de este campo existir (sem `corretor`), avisa uma vez por cada modelo com essas respostas: não dizem com que versão do corretor foram obtidas, e por isso não se pode confirmar nem desmentir que o corretor fixado é o que estava em vigor. O aviso diz que não há registo, e não que o corretor mudou. É só aviso: não altera quem fica aprovado.

**Protocolo escrito no mesmo dia da primeira resposta.** `protocolo.warnings` só
acusa um protocolo posterior se a data for estritamente posterior à da primeira
resposta (`written_on > first_answer.date()`). Um protocolo escrito no mesmo dia,
depois da primeira resposta, passa sem aviso, e a data do ficheiro é declarativa.
A prova é o commit do protocolo. Verificado a 10/10/2026 com o `git log` de cada
protocolo contra a primeira resposta do ensaio (hora de Lisboa; `asked_at` não
tem fuso e assumiu-se o do commit):

| Protocolo | Commit do protocolo | Primeira resposta | Anterior? |
|---|---|---|---|
| 2026-09-27-locais-12-14b | `b71d72b`, 27/09 23:44:40 | 27/09 23:52:11 | sim, 7 min |
| 2026-09-28-gemini-flash | `826cbea`, 28/09 12:43:11 | 28/09 18:26:04 | sim, 5 h |
| 2026-09-29-gemini-consulta | `afbd43f`, 29/09 11:06:53 | 29/09 11:07:07 | sim, 14 s |
| 2026-09-29-gemma4-31b-casos | `414c859`, 29/09 12:46:50 | 29/09 12:54:06 | sim, 7 min |
| 2026-09-29-gemma4-31b-consulta | `414c859`, 29/09 12:46:50 | 29/09 21:40:21 | sim, 9 h |
| 2026-10-01-gemma4-26b-casos | `caa28a3`, 01/10 10:58:37 | 01/10 11:22:09 | sim, 24 min |
| 2026-10-01-gemma4-26b-consulta | `caa28a3`, 01/10 10:58:37 | 03/10 14:20:36 | sim, 2 dias |

Os sete protocolos são anteriores à primeira resposta. Em todos, a data do ficheiro
é a do dia da primeira resposta ou anterior, e o aviso do código não os distinguiria
de um protocolo escrito depois no mesmo dia. O commit prova a ordem no histórico
local; não prova que o relógio da máquina estava certo.

**Comparação entre modelos: o par é escolhido depois dos dados.**
`grading.compare_critical` ordena os modelos pelo número de casos com falha
crítica e aplica o teste de McNemar exato aos dois primeiros. O par é, portanto,
escolhido pelo resultado, e o p calculado nele não conta com essa seleção. O
README já diz que não há correção para comparações múltiplas; o p lê-se como
descrição dos dois melhores, não como teste de uma hipótese fixada antes.

**Relatório HTML: o que ainda não está tratado.** Diagnóstico de 09/10/2026
sobre o exemplo público (banco principal, 4 modelos, 5 idiomas), medido em Brave
154 e por leitura do código. São limites conhecidos, sem código que os corrija.

- *Peso.* A página tem 1,54 MB e 90% (1394 KB) são o detalhe de "Casos com
  falha": 26 `<details>` com 397 respostas completas. Cada língua é um ficheiro
  completo, 5 × cerca de 1,6 MB, com o mesmo texto português dos casos.
- *Grelha de resultados.* Em 390 px a tabela tem 1025 px de largura dentro de um
  contentor de 356 px (regras `table.grade` em `html_estilo.py`) e a primeira
  coluna não fica fixa: ao rolar para ver outro modelo, as células perdem o
  rótulo do caso.
- *Eixo da comparação em telemóvel.* Em 390 px os cinco rótulos (0% a 100%)
  sobrepõem-se e leem-se como "0%25%50%75%100%" (regras `.comp-ticks` em
  `html_estilo.py`); as linhas dos intervalos ficam com cerca de 80 px.
- *Barra fixa e páginas.* O relatório são oito páginas, mostradas uma de cada
  vez só com CSS (`main > .painel` em `html_estilo.py`). A barra fixa
  (navegação, controlos e o aviso de triagem) tem a altura que declara
  (`--barra`, em `BAR_HEIGHT`: 4,8rem, 7rem abaixo de 62rem, 8,6rem abaixo de
  46rem e 9,4rem abaixo de 24rem), e o `scroll-padding-top` da página usa a mesma
  variável, por isso um separador ou uma âncora abre logo por baixo dela, em
  qualquer língua. Declarar em vez de medir foi uma correção: na primeira versão
  as alturas estavam medidas à mão a 1280 e 390 px e a 768 px a navegação
  quebrava em duas linhas, a barra crescia 26 a 43 px e o título de 4 das 6
  páginas ficava por baixo dela. Agora a navegação não quebra (desloca-se para
  o lado, com uma sombra na margem que ainda tem mais separadores).
  Medido a 10/10/2026 em Chromium, com cliques reais em cada separador, a 14
  larguras (320 a 1920 px) nas cinco línguas: nenhum título escondido e nenhum
  texto da barra a transbordar; o mesmo, em Chromium, Firefox e WebKit, a 320,
  390, 768 e 1024 px em português e alemão. A 1280 e 390 px, nos três motores,
  `#corpo-<caso>` abre o painel Casos e o `<details>` do caso. **Em telemóvel a
  barra mede 138 px** (cerca de um sexto do ecrã) e fica por afinar. A frase da
  barra cabe numa linha a partir de 600 px (de 768 px em alemão); abaixo disso
  ocupa duas linhas, e três em alemão a 320 e 360 px. As alturas declaradas já o
  assumem, e se o texto da barra mudar tem de se remedir.
- *Navegação sem `aria-current`.* A navegação é uma lista de ligações e não
  marca a página atual para tecnologias de apoio, porque sem script o estado
  não se mantém e marcar uma página que deixou de o ser diria uma coisa falsa.
  O `<h2>` de cada página (o `<h1>` no Início) é o que indica onde se está, e as
  páginas ocultas saem da árvore de acessibilidade. A ligação atual só se
  distingue visualmente. Sem `:has()` (navegadores anteriores a 2022 a 2023) as
  oito páginas ficam visíveis em sequência.
- *Tradução automática.* O inglês, o espanhol, o francês e o alemão foram
  traduzidos por uma máquina e nenhum falante nativo os reviu; só o português é
  a versão de referência. Dizem-no no cimo de cada página e no rodapé
  (`UNREVIEWED` em `aferidor/traducao.py`), e não na barra fixa, para a barra
  ter a mesma altura em todas as línguas. Rever uma língua é tirá-la dessa
  lista.
- *Blocos de resposta.* 382 dos 397 `<blockquote>` têm `max-height` e
  `overflow:auto` (regras `blockquote` e `.erro-par blockquote` em
  `html_estilo.py`): scroll dentro do scroll, e não são focáveis, por isso não
  se rolam com o teclado.
- *Cartões de falhas por tipo.* Em 360 px estendem-se até 389 px
  (`minmax(22rem, 1fr)` na regra `.falhas-grelha` de `html_estilo.py`); em
  390 px cabem.
- *Informação só em `title`.* 311 elementos (segmentos das barras, pontos de
  amostra, pergunta cortada) que não aparecem em toque.
- *Testes de contraste.* Cobrem as cores de texto sobre o fundo, o cartão, o
  segundo cartão e o realce, nos dois temas (`test_every_text_colour_reads_on_the_page_and_on_cards_in_both_themes`, em
  `tests/test_html_theme.py`), e o destaque a 3:1 como elemento gráfico
  (`test_what_is_not_text_stands_out_at_3_to_1`). Não cobrem o contraste das
  cores clínicas dos segmentos contra o cartão (WCAG 1.4.11, 3:1): no tema claro `warning` 1,83,
  `serious` 2,64, `neutral` 2,41 e `good` 3,35; no escuro `critical` 3,55 e
  `neutral` 3,16. São as cores dos segmentos das barras e das legendas, que
  levam também ícone e texto. O texto sobre fundos translúcidos (mínimo medido
  5,33) e sobre os círculos (4,80 a 10,73) passa, mas sem teste.
- *Estrutura.* Sem ligação para saltar para o conteúdo, e 173
  elementos com `tabindex=0` (os termos do glossário) antes de qualquer secção.
  As tabelas têm `scope` mas não `<caption>` (`_areas()` e `_grid()`, em
  `html_report.py`). Não foi verificado se os leitores de ecrã anunciam o
  `aria-label` do `<abbr>` dos códigos de caso (`_case_code()`).
- *Movimento e impressão.* `scroll-behavior: smooth` sem
  `prefers-reduced-motion` (`html_estilo.py:43`). Ao imprimir, os 31 `<details>`
  ficam fechados e o detalhe dos casos não sai (a regra `@media print` só evita
  quebras de página).

Não testado: leitor de ecrã, telemóvel real. A dúvida sobre a página arrastar
para o lado em 390 px ficou respondida a 10/10/2026, com uma janela real de
390 px (Playwright): o `scrollWidth` do documento é 875 px no painel Casos em
Chromium e em WebKit (914 px em alemão), e 390 px nos restantes painéis; no
Firefox não passa de 390 px. A causa provável continua a ser a dos elementos
`.vh` dentro da grelha, não confirmada.

**Fontes.** As fontes estão marcadas como confirmadas desde 27/09/2026 com
dois níveis de evidência, identificados em `casos/VERIFICACAO.md`: dez casos
de infeção confirmados nos PDF das normas da DGS, um a um; 24 declarados
confirmados em grupo nos documentos da DGS e do Infarmed, sem registo de
página por caso. Os 24 restantes citam outras fontes (APMGF, ESC, ADA, NICE,
EMA, SNS) e aguardam confirmação por uma pessoa: todos foram lidos no documento
original por ferramenta e coincidem com a referência.

O enquadramento normativo (ISO/IEC 42001, ISO 13485, Regulamento de
Dispositivos Médicos) está em `docs/APRESENTACAO.md`.

## Ensaios registados

`ensaios/` contém as execuções realizadas, com respostas em bruto, veredictos e
relatório. Cada pasta tem um README com o procedimento, as limitações e os
resultados, e um `MANIFESTO.sha256` com o SHA-256 de cada ficheiro, que se
verifica com `shasum -a 256 -c MANIFESTO.sha256` ou `aferidor manifesto
--verificar`. Os manifestos dos ensaios até 28/09 foram escritos a 29/09,
sobre os ficheiros tal como estavam commitados; o histórico do git prova que
não mudaram entre o ensaio e essa data.

| Ensaio | Descrição |
|---|---|
| `2026-09-14-agente/` | Primeira execução, através de uma sessão de assistente. Um caso dado como falhado revelou uma referência desatualizada, e não um erro do modelo; o caso foi reescrito contra a fonte em vigor. |
| `2026-09-16-comparacao-local-invalida/` | Medição invalidada por defeito do instrumento: o limite de tokens truncava as respostas de um modelo que raciocina antes de responder, e o corretor contava-as como erros. Mantida como registo. |
| `2026-09-16-comparacao-local/` | A mesma comparação em condições válidas: dois modelos locais, 27 casos, 5 amostras. Reclassificada a 27/09 com o corretor corrigido, sem repetir perguntas nem alterar os originais. |
| `2026-09-27-locais-12-14b/` | Primeiro ensaio com o instrumento completo: protocolo commitado antes da primeira pergunta, condições registadas em cada resposta, casos de infeção com fontes da DGS. Gemma 3 12B e Phi-4 14B, 27 casos, 5 amostras; 270 de 270 respostas; ambos reprovados pelo protocolo. |
| `2026-09-28-gemini-flash/` | Primeiro ensaio com um modelo comercial: Gemini 3.5 Flash Lite pela API gratuita, com protocolo commitado antes da primeira resposta. 27 casos, 5 amostras; 135 de 135 respostas; 11 de 27 casos com falha crítica; reprovado pelo protocolo. |
| `2026-09-29-gemini-consulta/` | Primeiro ensaio do banco de consulta: Gemini 3.5 Flash Lite, 30 casos, 5 amostras, protocolo prévio. 150 de 150 respostas; 4 de 30 casos com falha crítica¹ (6 à data do ensaio); reprovado pelo protocolo. As respostas levaram a afinar o `nao_prescreve` (commit `3fc49ba`), antes de registar os resultados. |
| `2026-09-29-gemma4-31b-casos/` | Gemma 4 31B (modelo aberto, pela API gratuita) no banco principal, protocolo prévio. 135 de 135 respostas; 8 de 27 casos com falha crítica¹ (10 à data do ensaio); reprovado. |
| `2026-09-29-gemma4-31b-consulta/` | Gemma 4 31B no banco de consulta, protocolo prévio. 150 de 150 respostas; 4 de 30 casos com falha crítica; reprovado. Levou a afinar o `nao_prescreve` (commit `0cbfda6`). |
| `2026-10-01-gemma4-26b-casos/` e `2026-10-01-gemma4-26b-consulta/` | Primeiro ensaio com o corretor congelado no protocolo (`versao_corretor`): Gemma 4 26B A4B nos dois bancos, 290 de 290 respostas; 12 de 27 e 5 de 31 casos com falha crítica; reprovado. Publicado sem afinação; os falsos positivos do corretor estão descritos no README de cada pasta e não alteram os números. |

Depois de 27/09, vários casos mudaram de fonte e de formulação. Os resultados
registados em cada ensaio correspondem ao instrumento da altura e não são
comparáveis com ensaios posteriores.

### Que números levam o corretor atual

Nas tabelas do `README.md` e nesta, um só critério decide: o ensaio tinha, ou
não, um compromisso escrito de congelar o corretor no protocolo
(`versao_corretor`). Os ensaios sem esse compromisso (Gemma 4 31B, Gemini 3.5
Flash Lite, Gemma 3 12B, Phi-4 14B) mostram os números com o corretor atual,
marcados com ¹, e quando diferem da data do ensaio a data vem entre parênteses.
O ensaio com compromisso (Gemma 4 26B A4B, 01/10) mostra o número tal como foi
publicado, com os seus intervalos, e isso não é uma inconsistência: reclassificá-lo
tiraria o sentido ao congelamento. A diferença fica sempre dita na nota, e `ensaios/` guarda os relatórios com os números da data.

¹ Corretor atual: o das afinações `83d951b`, `f202e37`, `3fa7e65` e `886f637`;
a razão de cada uma está na mensagem do respetivo commit.

## Roteiro

- [x] **Fase 1** Modelo de caso, critérios de aceitação e armazenamento
- [x] **Fase 2** Conjunto inicial de casos com fontes verificadas
- [x] **Fase 3** Executor: envio, recolha e registo
- [x] **Fase 4** Classificadores e taxonomia de falhas
- [x] **Fase 5** Relatório e métricas por categoria de risco
- [x] **Fase 6** Documentação e apresentação
- [x] **Fase 7** Robustez do instrumento (27/09/2026): controlos negativos,
  condições registadas em cada resposta, esquemas alternativos, fontes da DGS,
  indicador de português europeu, intervalos de confiança
- [x] **Fase 8** Ferramentas de validação (27/09/2026): protocolo de aprovação
  prévio e folha cega para revisão clínica
- [ ] **Fase 9** Validação: revisão clínica de uma amostra de respostas reais e
  confirmação das fontes restantes (o ensaio pela API com protocolo prévio foi
  feito a 28/09/2026)
