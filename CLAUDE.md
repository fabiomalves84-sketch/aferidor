# Instruções do projeto

Este ficheiro é lido automaticamente por qualquer sessão do Claude Code aberta
nesta pasta. Vale para todas.

## O que é o Aferidor

Um banco de ensaio que mede respostas clínicas de modelos de linguagem em
português europeu contra casos de referência com fonte pública. Mede, não
aconselha. Não é dispositivo médico e não contém dados de doentes.

Lê o `README.md`, o `docs/METODO.md` e o `docs/ARQUITETURA.md` antes de mexer em código. As
fronteiras entre módulos existem por razões escritas, não por acaso.

## Língua

Português europeu em tudo o que uma pessoa lê: mensagens de commit, documentos,
mensagens de erro, e o texto que sai nos comandos. Sem travessões duplos.

Os comentários e docstrings dentro do código estão em inglês, por convenção.
Mantém assim, para não ficar metade e metade.

## As regras que não se quebram

**Nenhum caso conta como verificado enquanto uma pessoa não abrir o documento na
página indicada e confirmar o valor com os próprios olhos.** A tabela é
`casos/VERIFICACAO.md`. Nunca marques uma caixa dessa tabela. Só o Fábio a marca.

**Um caso cuja própria referência não passa nos seus critérios está partido**, e
está partido na direção que mais custa: dá como errado um modelo que acertou.
`python3 -m aferidor verificar` tem de dar 27 em 27 antes de qualquer execução
paga, e corre também na bateria de testes.

**Um critério que não apanha uma resposta errada também está partido**, na
direção contrária: deixa passar um erro. O mesmo `verificar` constrói, para
cada critério, uma resposta errada a partir da referência e exige que falhe.
Tem de dar todos os controlos negativos apanhados. Se um sobreviver, a correção
é no corretor ou no caso, com a razão escrita, nunca retirar o controlo.

**Alargar um critério porque ele castiga uma forma diferente de dizer a mesma
coisa é afinar. Alargá-lo para o modelo passar é batota.** As duas parecem iguais
às três da manhã. O que as separa é o commit: cada alteração a um critério leva
a razão escrita na mensagem.

**O fornecedor nunca vê a resposta de referência nem os critérios.** Há um teste
que fixa esta fronteira. Se alguma vez falhar, não o contornes.

**A taxonomia não pode prometer o que nenhum caso mede.** Há um teste que falha
se algum tipo de falha ficar sem caso. Se acrescentares um tipo, acrescenta o
caso.

**A contagem de testes escrita nos documentos tem de ser a verdadeira.** Já
aconteceu os documentos dizerem 181 com a bateria em 211. Qualquer tarefa que
acrescente ou remova testes atualiza o número no README, no
`docs/APRESENTACAO.md` e aqui, no mesmo commit que muda os testes.

## Mensagens de commit

Explicam a decisão, não listam ficheiros. Corre `git log` e lê duas ou três
antes de escreveres a primeira. O histórico deste projeto é metade do que ele
demonstra.

## Como correr

```
python3 -m unittest discover -s tests   # 521 testes
python3 -m aferidor verificar           # 27/27 casos, 319/319 controlos negativos
python3 -m aferidor verificar --casos casos/consulta.json   # 31/31, 140/140
python3 -m aferidor ensaio --fornecedor falso
```

`docs/COMO_CORRER.md` cobre a execução contra um modelo real.

## Uma sessão só, no VS Code

Desde 27 de setembro de 2026 o projeto é trabalhado numa sessão só, a do
Claude Code dentro do VS Code, com o Fábio. É essa sessão que decide o desenho
com ele, escreve o código, corre os testes, commita e faz push.

Até essa data havia duas sessões com papéis separados: uma na aplicação Claude
que decidia e escrevia o `BRIEFING.md`, e outra no terminal que executava e era
a única a mexer no git. A separação acabou porque o código passou a ser escrito
diretamente no VS Code. A regra que ela protegia continua a valer: **nunca duas
sessões a correr git ao mesmo tempo.** No dia 14 de setembro de 2026 isso
aconteceu, deixou ficheiros de bloqueio presos em `.git` que travaram todos os
commits seguintes, e uma sessão escreveu uma fase inteira que a outra já tinha
escrito. Se abrires outra sessão para ler ou pensar, ela não commita.

Se encontrares ficheiros `.lock` presos dentro de `.git` sem nenhum git a
correr, apaga-os. Foi isso que aconteceu.

## O caderno

`BRIEFING.md` não entra no repositório. Deixou de ser passagem de testemunho e
passou a ser o caderno do projeto: no topo, as decisões em aberto que ainda são
do Fábio; em baixo, o registo das tarefas antigas e do que foi feito em cada
uma. Quando uma decisão em aberto for tomada e feita, sai do topo e fica
registada em baixo, com os commits.
