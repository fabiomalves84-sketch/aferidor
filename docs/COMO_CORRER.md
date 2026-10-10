# Execução contra um modelo real

Guia de execução com um fornecedor real. Todos os comandos funcionam também
com `--fornecedor falso`, sem chave e sem custo.

## 1. Chave de API

- **OpenAI:** platform.openai.com, secção API keys. Requer saldo prévio.
- **Anthropic:** console.anthropic.com, secção API keys. Requer saldo prévio.
- **Google Gemini:** aistudio.google.com, secção API keys. Tem um nível
  gratuito, sem cartão, com limites por modelo consultáveis em
  aistudio.google.com/rate-limit. Os modelos Flash permitem 20 pedidos por
  dia, insuficientes para 27 casos × 5 amostras; os Flash Lite permitem 500.
  O fornecedor `gemini` espaça os pedidos 13 segundos (limite de 5 por
  minuto); para modelos com limites mais altos, o intervalo reduz-se com
  `AFERIDOR_GEMINI_INTERVALO`. Pedidos recusados por sobrecarga (503) também
  contam para o limite diário. Fora do Espaço Económico Europeu, a Google pode
  usar os pedidos do nível gratuito para melhorar os seus produtos.

As subscrições do ChatGPT e do Claude não incluem acesso à API.

## 2. Chave no ambiente, nunca no projeto

```
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export GEMINI_API_KEY="..."
```

A variável vale apenas para a sessão de terminal. Uma chave escrita num
ficheiro do projeto fica no histórico do git de forma permanente. Para uma
configuração persistente, as linhas podem ser acrescentadas a `~/.zshrc`, que
não pertence ao projeto.

## 3. Modelos disponíveis

```
python -m aferidor modelos --fornecedor openai
python -m aferidor modelos --fornecedor anthropic
python -m aferidor modelos --fornecedor gemini
```

A lista é obtida do fornecedor e não é mantida no projeto, porque os nomes de
modelos mudam com frequência.

## 4. Banco de casos

`casos/casos.json` (27 casos: antibioterapia, interações, gravidez e ajuste de
dose) é o banco por omissão. `casos/consulta.json` (31 casos de consulta de
adulto, criança e cessação tabágica) seleciona-se com `--casos`:

```
python -m aferidor verificar --casos casos/consulta.json
python -m aferidor ensaio --fornecedor <fornecedor> --modelo <nome> --casos casos/consulta.json --limite 3
```

Recomenda-se usar ficheiros de saída próprios (`--saida`, `--vereditos`,
`--relatorio`) para cada banco.

## 5. Protocolo, antes do ensaio

O critério de aprovação, opcional, define-se antes de ver qualquer resposta:

```
python -m aferidor protocolo --nome "<nome do ensaio>" --saida protocolos/<nome>.json
```

Os limites em `criterios_de_aprovacao` começam no valor mais exigente (zero
casos com falha crítica); qualquer alívio deve ser uma decisão explícita. O
protocolo deve ser commitado **antes** do ensaio e passado ao comando com
`--protocolo`.

Com `--congelar-corretor`, o protocolo fixa também a versão do corretor
(`versao_corretor`). O código deve estar commitado antes de escrever o
protocolo. O relatório assinala qualquer resposta obtida, ou correção feita,
com outra versão: um corretor afinado depois de ver as respostas deixa de
passar despercebido.

## 6. Execução

```
python -m aferidor ensaio --fornecedor openai --modelo <nome>
python -m aferidor ensaio --fornecedor openai --modelo <nome> --limite 3   # teste curto
```

O comando executa, corrige e escreve o relatório. Antes do primeiro pedido,
confirma que todos os casos cumprem os próprios critérios e que cada critério
deteta uma resposta errada construída; se algum falhar, interrompe sem custo.

As respostas ficam em `data/respostas.jsonl`, e uma nova execução retoma os
casos em falta desse modelo. A retoma recusa condições diferentes
(`--temperatura`, `--tokens-max` ou texto de um caso alterado); para uma nova
medição, usar `--recomecar` ou outro `--saida`. Com 27 perguntas curtas, o
custo nos modelos correntes é da ordem dos cêntimos.

## 7. Afinação de critérios

Com respostas reais (parágrafos, listas, tabelas, avisos), é normal que alguns
critérios reprovem respostas corretas. A afinação não tem custo:

```
python -m aferidor classificar
```

O comando volta a corrigir as respostas já guardadas com os critérios atuais,
sem novos pedidos. Para ver exatamente que veredictos uma alteração muda,
resposta a resposta, antes de a commitar:

```
python -m aferidor comparar-vereditos --casos <casos.json> --respostas <respostas.jsonl> --vereditos <vereditos.json>
```

O resumo (quantos passam a passar, quantos passam a falhar) entra na mensagem
de commit, junto com a razão.

**Regra:** alargar um critério que penaliza outra forma de dizer a mesma coisa
é afinação; alargá-lo para o modelo passar não é aceitável. Cada alteração a
um critério é registada no commit com a justificação.

## 8. Amostras repetidas

```
python -m aferidor ensaio --fornecedor openai --modelo <nome> --repeticoes 5 --temperatura 1.0
```

Um modelo que acerta a dose em 4 de 5 amostras erra a dose na prática: o
médico observa uma única resposta. Por isso o relatório conta casos com falha
crítica em pelo menos uma amostra.

**Recomenda-se `--temperatura 1.0`.** A temperatura 0 devolve sempre a
resposta mais provável e oculta a variabilidade que o ensaio pretende medir;
os produtos reais raramente usam temperatura 0.

## 9. Comparação de modelos

```
python -m aferidor ensaio --fornecedor openai --modelo <nome>
python -m aferidor ensaio --fornecedor anthropic --modelo <nome>
```

As respostas dos vários modelos coexistem no mesmo ficheiro e o relatório
inclui uma tabela de comparação: casos com falha crítica, casos corretos pela
regra do relatório, casos parcialmente corretos e amostras corretas, cada um
com intervalo de confiança. As três primeiras colunas contam casos; a última
conta respostas.

## 10. Limite de tokens e modelos que raciocinam

`--tokens-max` (por omissão 4096) limita o tamanho de cada resposta. Um modelo
que raciocina antes de responder (por exemplo, `qwen3:8b`) consome parte desse
limite antes do texto da resposta. No ensaio de 16/09/2026, com o limite
anterior de 1024, 35 de 135 respostas do `qwen3:8b` chegaram vazias e 75
truncadas (ver `ensaios/2026-09-16-comparacao-local-invalida/README.md`).
Para estes modelos, recomenda-se:

```
python -m aferidor ensaio --fornecedor local --modelo qwen3:8b --tokens-max 8192
```

Uma resposta truncada fica por responder e não é repetida automaticamente com
mais tokens, para não misturar duas medições no mesmo ficheiro. A solução é
repetir o ensaio desde o início com um `--tokens-max` maior.

**Os modelos de raciocínio da OpenAI (`o1`, `o3`, `gpt-5` e semelhantes)
aceitam apenas `--temperatura 1.0`** e usam `max_completion_tokens` em vez de
`max_tokens`. O `OpenAIProvider` envia o parâmetro correto, verificado apenas
com pedidos simulados; recomenda-se confirmar com `--limite 1`
antes de uma execução completa.

## 11. Ensaio de comparação completo

Três modelos, cinco amostras por caso, temperatura 1,0.

**Modelos locais, através do Ollama** (sem custo e sem envio de dados para o
exterior). Após instalar o Ollama (ollama.com) e descarregar os modelos
(`ollama list` confirma que está ativo):

```
python -m aferidor ensaio --fornecedor local --modelo <nome-a> --repeticoes 5 --temperatura 1.0 --tokens-max 8192
python -m aferidor ensaio --fornecedor local --modelo <nome-b> --repeticoes 5 --temperatura 1.0 --tokens-max 8192
python -m aferidor ensaio --fornecedor local --modelo <nome-c> --repeticoes 5 --temperatura 1.0 --tokens-max 8192
python -m aferidor relatorio --formato html
```

São 405 pedidos (27 × 5 × 3). Num portátil, a duração depende do hardware e do
modelo; recomenda-se registar o tempo total no README do ensaio.
`relatorios/relatorio.html` é um ficheiro único, com a grelha de estados por
caso e um ponto por amostra. Com `--linguas pt,en,es,fr,de`, o relatório é
gerado também nas outras línguas, cada uma num ficheiro ao lado
(`relatorio.en.html`...), com um menu 🌐 entre elas.

**APIs comerciais.** Para medir os modelos que o utilizador final usa,
substituir `--fornecedor local` por `openai`, `anthropic` ou `gemini`. O custo
de 405 pedidos nos modelos correntes é da ordem dos cêntimos a poucos euros.

## 12. Validação por um clínico

Antes de apresentar resultados, um clínico deve julgar uma amostra das
respostas:

```
python -m aferidor revisao --respostas data/respostas.jsonl --n 60
```

Enviar `relatorios/revisao.csv`, **nunca** `revisao-chave.json`, que contém as
decisões do corretor. Com a coluna `juizo` preenchida:

```
python -m aferidor concordancia --revisao relatorios/revisao.csv
```

O primeiro valor apresentado é o mais relevante: o número de respostas erradas
aprovadas pelo corretor. Se for elevado, os resultados do ensaio sobrestimam o
modelo.

## 13. Recomeçar do zero

```
python -m aferidor ensaio --fornecedor openai --modelo <nome> --recomecar
```

Descarta as respostas anteriores do modelo e repete todos os pedidos, com o
custo correspondente. As novas respostas não serão iguais às anteriores.

## 14. Regenerar o relatório de exemplo

O relatório publicado em `docs/exemplo/` (o que o README liga) não é de um
ensaio só: junta as respostas de quatro modelos no banco principal atual, vindas
de três ensaios. Corrigem-se com o corretor de hoje, pelo que os números mudam
quando o corretor muda e o exemplo tem de ser regenerado, não editado.

```
cat ensaios/2026-09-29-gemma4-31b-casos/respostas.jsonl \
    ensaios/2026-09-28-gemini-flash/respostas.jsonl \
    ensaios/2026-09-27-locais-12-14b/respostas.jsonl > /tmp/exemplo-respostas.jsonl
python -m aferidor relatorio --formato html --linguas pt,en,es,fr,de \
  --casos casos/casos.json --respostas /tmp/exemplo-respostas.jsonl \
  --saida docs/exemplo/index.html
```

Cria `index.html` (português) e `index.en.html`, `index.es.html`,
`index.fr.html` e `index.de.html` ao lado. En, es, fr e de levam o aviso de
tradução não revista, e rever uma língua é tirá-la de `UNREVIEWED`, em
`aferidor/traducao.py`. A data no topo é a do dia em que se corre. Fica de fora o Gemma 4 26B A4B, cujo corretor está congelado no
protocolo.

A captura `docs/imagens/resumo.png`, usada no README, não se gera por comando:
tira-se a partir de `index.html` aberto no navegador, e confere-se que mostra os
mesmos números do relatório.

O README do ensaio `2026-09-16-comparacao-local` tem uma receita mais antiga
para o mesmo exemplo, com só esse ensaio. Ficou como registo da altura e não
produz o exemplo atual.
