# Instruções do projeto

Este ficheiro é lido automaticamente por qualquer sessão do Claude Code aberta
nesta pasta. Vale para todas.

## O que é o Aferidor

Um banco de ensaio que mede respostas clínicas de modelos de linguagem em
português europeu contra casos de referência com fonte pública. Mede, não
aconselha. Não é dispositivo médico e não contém dados de doentes.

Lê o `README.md` e o `docs/ARQUITETURA.md` antes de mexer em código. As
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

**Alargar um critério porque ele castiga uma forma diferente de dizer a mesma
coisa é afinar. Alargá-lo para o modelo passar é batota.** As duas parecem iguais
às três da manhã. O que as separa é o commit: cada alteração a um critério leva
a razão escrita na mensagem.

**O fornecedor nunca vê a resposta de referência nem os critérios.** Há um teste
que fixa esta fronteira. Se alguma vez falhar, não o contornes.

**A taxonomia não pode prometer o que nenhum caso mede.** Há um teste que falha
se algum tipo de falha ficar sem caso. Se acrescentares um tipo, acrescenta o
caso.

## Mensagens de commit

Explicam a decisão, não listam ficheiros. Corre `git log` e lê duas ou três
antes de escreveres a primeira. O histórico deste projeto é metade do que ele
demonstra.

## Como correr

```
python3 -m unittest discover -s tests   # 171 testes
python3 -m aferidor verificar           # 27/27 casos coerentes
python3 -m aferidor ensaio --fornecedor falso
```

`docs/COMO_CORRER.md` cobre a execução contra um modelo real.

## Divisão de trabalho entre sessões

Este projeto é trabalhado por duas sessões ao mesmo tempo, com papéis separados
de propósito. Respeita o teu papel e não invadas o outro.

**Sessão Opus, na aplicação Claude:** decide o desenho, investiga fontes,
escreve o `BRIEFING.md`. Escreve ficheiros. **Não corre comandos git.**

**Sessão Sonnet, no terminal:** lê o `BRIEFING.md`, escreve código, corre os
testes, **commita e faz push**. É a única que mexe no git.

A razão é concreta e não é teórica: no dia 14 de setembro de 2026 as duas
sessões correram comandos git ao mesmo tempo e deixaram ficheiros de bloqueio
presos em `.git`, que travaram todos os commits seguintes. E uma escreveu uma
fase inteira que a outra já tinha escrito.

Se encontrares ficheiros `.lock` presos dentro de `.git` sem nenhum git a
correr, apaga-os. Foi isso que aconteceu.

## Passagem de testemunho

`BRIEFING.md` é o caderno entre as duas sessões. Não entra no repositório. A
sessão executora faz o que está em TAREFA, escreve em FEITO o que fez, e põe
TAREFA a "nada pendente".
