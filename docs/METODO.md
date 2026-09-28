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

**Verificação do corretor.** `python -m aferidor verificar` avalia a resposta
de referência de cada caso contra os seus próprios critérios. Um caso cuja
referência não passa está defeituoso no sentido mais grave: classifica como
errado um modelo que acertou. O mesmo comando verifica o sentido inverso: para
cada critério, constrói a partir da referência uma resposta errada no ponto
exato que o critério avalia (remove os termos exigidos por `contem`, duplica
ou divide o valor de `valor_numerico`, acrescenta a prescrição proibida por
`nao_prescreve`) e exige que o veredicto registe a falha. Nenhum conteúdo
clínico é inventado; apenas se altera o que já existe. Estes controlos não
detetam um termo contido acidentalmente noutra palavra de uma resposta real;
isso só se observa com respostas reais. Para os critérios negativos há dois
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
python -m aferidor protocolo --nome "ensaio de outubro" --saida protocolos/outubro.json
git add protocolos/outubro.json && git commit    # antes de correr
python -m aferidor ensaio ... --protocolo protocolos/outubro.json
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
python -m aferidor revisao --respostas <ficheiro> --n 60   # folha para julgar
python -m aferidor concordancia --revisao relatorios/revisao.csv
```

O primeiro comando seleciona uma amostra reprodutível (metade aprovada e
metade reprovada pelo corretor) e escreve uma folha de cálculo cega: mostra a
pergunta, a referência e a resposta, mas não o veredicto nem o modelo, que
ficam num ficheiro-chave separado. O avaliador escreve "certa" ou "errada" em
cada linha. O segundo comando apresenta, por esta ordem, as aprovações
indevidas (respostas julgadas erradas que o corretor aprovou), as reprovações
indevidas, a concordância e o kappa de Cohen, com intervalos de confiança a
95%. Respostas a uma formulação diferente da pergunta são excluídas da
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

`python -m aferidor relatorio` produz um documento em Markdown ou HTML. As
falhas críticas surgem antes da percentagem de respostas corretas, porque a
percentagem isolada oculta o que importa.

Cada resposta incorreta é apresentada com a pergunta, a referência, a fonte, a
resposta do modelo e o critério não cumprido, para que qualquer veredicto
possa ser verificado e contestado. O relatório indica as condições de
obtenção: ficheiro e SHA-256 do banco e, por modelo, datas de recolha,
temperatura, limite de tokens e versão do Aferidor. Quando um ficheiro mistura
condições, todos os valores são apresentados.

Casos sem resposta são identificados e excluídos das contagens. Enquanto as
fontes não estiverem confirmadas por uma pessoa, o relatório apresenta um
aviso no topo.

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
está contraindicada", "sem contraindicação") conta como prescrição. É preferível ao comportamento
anterior, que tratava qualquer menção como prescrição e reprovava respostas
corretas que incluíam um aviso. Não constitui compreensão de texto.

**Fontes.** As fontes estão marcadas como confirmadas desde 27/09/2026 com
dois níveis de evidência, identificados em `casos/VERIFICACAO.md`: dez casos
de infeção confirmados nos PDF das normas da DGS, um a um; 24 declarados
confirmados em grupo nos documentos da DGS e do Infarmed, sem registo de
página por caso. Os 23 restantes citam outras fontes (APMGF, ESC, ADA, NICE,
EMA) e estão por confirmar.

O enquadramento normativo (ISO/IEC 42001, ISO 13485, Regulamento de
Dispositivos Médicos) está em `docs/APRESENTACAO.md`.

## Ensaios registados

`ensaios/` contém as execuções realizadas, com respostas em bruto, vereditos e
relatório. Cada pasta tem um README com o procedimento, as limitações e os
resultados.

| Ensaio | Descrição |
|---|---|
| `2026-09-14-agente/` | Primeira execução, através de uma sessão de assistente. Um caso dado como falhado revelou uma referência desatualizada, e não um erro do modelo; o caso foi reescrito contra a fonte em vigor. |
| `2026-09-16-comparacao-local-invalida/` | Medição invalidada por defeito do instrumento: o limite de tokens truncava as respostas de um modelo que raciocina antes de responder, e o corretor contava-as como erros. Mantida como registo. |
| `2026-09-16-comparacao-local/` | A mesma comparação em condições válidas: dois modelos locais, 27 casos, 5 amostras. Reclassificada a 27/09 com o corretor corrigido, sem repetir perguntas nem alterar os originais. |
| `2026-09-27-locais-12-14b/` | Primeiro ensaio com o instrumento completo: protocolo commitado antes da primeira pergunta, condições registadas em cada resposta, casos de infeção com fontes da DGS. Gemma 3 12B e Phi-4 14B, 27 casos, 5 amostras; 270 de 270 respostas; ambos reprovados pelo protocolo. |

Depois de 27/09, vários casos mudaram de fonte e de formulação. Os resultados
registados em cada ensaio correspondem ao instrumento da altura e não são
comparáveis com ensaios posteriores.

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
- [ ] **Fase 9** Validação: revisão clínica de uma amostra de respostas reais,
  confirmação das fontes restantes e ensaio pela API com protocolo prévio
