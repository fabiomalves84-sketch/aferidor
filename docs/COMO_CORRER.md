# Correr contra um modelo a sério

Guia para o dia em que houver chave de API. Até lá, tudo o que está aqui
funciona com `--fornecedor falso`, sem chave e sem custo.

## 1. Obter a chave

**OpenAI:** platform.openai.com, secção API keys. É preciso carregar saldo
primeiro; o mínimo costuma ser cinco ou dez euros.

**Anthropic:** console.anthropic.com, secção API keys. Igual, saldo à parte.

A subscrição do ChatGPT ou do Claude não serve. A API é paga em separado.

## 2. Pôr a chave no ambiente, nunca no projeto

No terminal, antes de correr:

```
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
```

Isto vale só para aquela janela do terminal e desaparece quando a fechas, que é
exatamente o que se quer. Uma chave escrita num ficheiro do projeto acaba no
histórico do git, e do histórico do git não sai. O `.gitignore` já ignora `.env`,
mas a forma segura é esta.

Se a quiseres permanente, põe as linhas no fim de `~/.zshrc`. Esse ficheiro não
faz parte do projeto.

## 3. Ver que modelos existem

```
python -m aferidor modelos --fornecedor openai
python -m aferidor modelos --fornecedor anthropic
```

A lista vem do próprio fornecedor. Não está escrita em lado nenhum deste projeto
de propósito: uma lista de nomes de modelos escrita num documento está errada
dentro de meses, e apontar a um modelo retirado dá um erro que não tem nada a ver
com o banco de ensaio.

## 4. Correr

Um comando faz tudo: pergunta, corrige e escreve o relatório.

```
python -m aferidor ensaio --fornecedor openai --modelo <nome-da-lista>
```

Antes de gastar um cêntimo, ele confirma que os 27 casos passam nos próprios
critérios. Se algum estiver partido, para e não pergunta nada. Descobrir um caso
errado depois de pagar a execução obriga a pagá-la outra vez.

Para experimentar sem gastar tudo:

```
python -m aferidor ensaio --fornecedor openai --modelo <nome> --limite 3
```

## 5. Custo

Vinte e sete perguntas curtas com respostas de um ou dois parágrafos. Nos modelos
correntes isto fica em cêntimos, não em euros. O que custa dinheiro é repetir a
execução muitas vezes, e o projeto foi feito para não precisar disso: as
respostas ficam guardadas em `data/respostas.jsonl` e uma segunda execução salta
os casos que já foram respondidos por aquele modelo.

## 6. O passo que vai dar trabalho

Até hoje o banco só foi corrido contra respostas de mentira, curtas e limpas. Um
modelo a sério responde com parágrafos, listas, tabelas e avisos.

**Conta com critérios a dar como errado respostas que estão certas.** Não é
falha do modelo nem sinal de que o banco não presta. É o trabalho normal de
afinar um instrumento de medida contra dados reais.

O importante é que afinar não custa dinheiro:

```
python -m aferidor classificar
```

Este comando volta a corrigir as respostas **já guardadas**, com os critérios
como estão nesse momento. Editas um critério em `casos/casos.json`, voltas a
correr, vês o efeito. Quantas vezes quiseres, sem perguntar nada a ninguém.

A regra ao afinar: alarga um critério quando ele castiga uma forma diferente de
dizer a mesma coisa. Não o alargues para o modelo passar. A diferença entre as
duas coisas é a única que interessa neste projeto inteiro, e quem afina é sempre
tentado a esquecê-la.

Cada critério que alargares fica registado no git com a razão. É isso que
distingue afinar de fazer batota.

## 7. Repetir a mesma pergunta

```
python -m aferidor ensaio --fornecedor openai --modelo <nome> --repeticoes 5 --temperatura 1.0
```

Um modelo que acerta a dose 4 vezes em 5 é, na prática, um modelo que erra a
dose: o médico só vê uma resposta e não escolhe qual das cinco lhe calha. É
por isso que o relatório passa a contar casos com falha crítica em pelo menos
uma amostra, não respostas certas em média.

**Usa `--temperatura 1,0` para isto, não o valor por omissão.** A temperatura
0 pede ao modelo a resposta mais provável sempre, e por isso esconde
exatamente a variabilidade que um ensaio de consistência quer medir. Um
produto real, o que o utilizador final usa, normalmente não corre a
temperatura 0. Medir a 0 e reportar como se fosse o produto é medir outra
coisa.

## 8. Comparar dois modelos

Corre os dois. As respostas dos dois convivem no mesmo ficheiro, separadas por
modelo, e o relatório passa a trazer uma tabela de comparação no topo.

```
python -m aferidor ensaio --fornecedor openai --modelo <nome>
python -m aferidor ensaio --fornecedor anthropic --modelo <nome>
```

A tabela mostra a taxa de acerto e as falhas críticas lado a lado. Ler a segunda
coluna antes da primeira.

## 9. Ensaio de comparação

O ensaio completo, para uma candidatura ou uma decisão a sério: três modelos,
cinco amostras por caso, a temperatura que esconde menos variabilidade.

```
python -m aferidor ensaio --fornecedor openai --modelo <nome-a> --repeticoes 5 --temperatura 1.0
python -m aferidor ensaio --fornecedor openai --modelo <nome-b> --repeticoes 5 --temperatura 1.0
python -m aferidor ensaio --fornecedor anthropic --modelo <nome-c> --repeticoes 5 --temperatura 1.0
python -m aferidor relatorio --formato html
```

**Custo aproximado: 27 casos × 5 repetições × 3 modelos = 405 pedidos.** Nos
modelos correntes isto continua em cêntimos ou poucos euros, não em dezenas,
mas é bom saber o número antes de o correr, não depois.

O último comando escreve `relatorios/relatorio.html`, um ficheiro só que abre
com duplo clique: a grelha de casos por modelo, com o estado de cada um,
estável certo, estável errado ou instável, é mais fácil de ler ali do que na
tabela em Markdown.

## 10. Recomeçar do zero

```
python -m aferidor ensaio --fornecedor openai --modelo <nome> --recomecar
```

Só quando quiseres mesmo perguntar tudo de novo, porque paga-se tudo de novo. E
a resposta que vem à segunda não é a mesma que veio à primeira.
