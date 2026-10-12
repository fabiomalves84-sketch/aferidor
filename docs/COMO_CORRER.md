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
não pertence ao projeto. Na falta da variável, o Aferidor lê também um ficheiro
`.env` na raiz do repositório, que o git ignora (ver a secção 15).

## 3. Modelos disponíveis

```
python3 -m aferidor modelos --fornecedor openai
python3 -m aferidor modelos --fornecedor anthropic
python3 -m aferidor modelos --fornecedor gemini
```

A lista é obtida do fornecedor e não é mantida no projeto, porque os nomes de
modelos mudam com frequência.

## 4. Banco de casos

`casos/casos.json` (27 casos: antibioterapia, interações, gravidez e ajuste de
dose) é o banco por omissão. `casos/consulta.json` (31 casos de consulta de
adulto, criança e cessação tabágica) seleciona-se com `--casos`:

```
python3 -m aferidor verificar --casos casos/consulta.json
python3 -m aferidor ensaio --fornecedor <fornecedor> --modelo <nome> --casos casos/consulta.json --limite 3
```

Recomenda-se usar ficheiros de saída próprios (`--saida`, `--vereditos`,
`--relatorio`) para cada banco.

## 5. Protocolo, antes do ensaio

O critério de aprovação, opcional, define-se antes de ver qualquer resposta:

```
python3 -m aferidor protocolo --nome "<nome do ensaio>" --saida protocolos/<nome>.json
```

Os limites em `criterios_de_aprovacao` começam no valor mais exigente (zero
casos com falha crítica); qualquer alívio deve ser uma decisão explícita. O
protocolo deve ser commitado **antes** do ensaio e passado ao comando com
`--protocolo`.

Com `--congelar-correcao`, o protocolo fixa também a versão só dos ficheiros que
decidem a correção (`corretor_id`: `checks`, `grading`, `models`, `risk`, `storage`
e `protocolo`); editar o relatório, a interface ou as traduções não a muda. É a
opção recomendada. Com `--congelar-corretor`, fixa a versão do pacote inteiro
(`versao_corretor`), que muda com qualquer edição ao código; as duas não se usam
juntas. O código deve estar commitado antes de escrever o protocolo. O relatório
assinala qualquer resposta obtida, ou correção feita, com outra versão: um
corretor afinado depois de ver as respostas deixa de passar despercebido. Com
`corretor_id`, as respostas registadas antes de o campo existir avisam que não
há registo da versão, e o `ensaio` recusa-se a correr se mudou um dos seis
ficheiros.

## 6. Execução

```
python3 -m aferidor ensaio --fornecedor openai --modelo <nome>
python3 -m aferidor ensaio --fornecedor openai --modelo <nome> --limite 3   # teste curto
```

O comando executa, corrige e escreve o relatório. Antes do primeiro pedido,
confirma que todos os casos cumprem os próprios critérios e que cada critério
deteta uma resposta errada construída; se algum falhar, interrompe sem custo.

As respostas ficam em `data/respostas.jsonl`, e uma nova execução retoma os
casos em falta desse modelo. A retoma recusa condições diferentes
(`--temperatura`, `--tokens-max` ou texto de um caso alterado); para uma nova
medição, usar `--recomecar` ou outro `--saida`. O custo depende do modelo: nos
pequenos pode ser da ordem dos cêntimos, mas nos de topo do catálogo, com várias
amostras por caso e respostas longas, pode chegar a dezenas de euros. Antes de
gastar, `--a-seco` estima-o; um modelo do catálogo não arranca sem `--teto-eur`
(secção 15).

## 7. Afinação de critérios

Com respostas reais (parágrafos, listas, tabelas, avisos), é normal que alguns
critérios reprovem respostas corretas. A afinação não tem custo:

```
python3 -m aferidor classificar
```

O comando volta a corrigir as respostas já guardadas com os critérios atuais,
sem novos pedidos. Para ver exatamente que veredictos uma alteração muda,
resposta a resposta, antes de a commitar:

```
python3 -m aferidor comparar-vereditos --casos <casos.json> --respostas <respostas.jsonl> --vereditos <vereditos.json>
```

O resumo (quantos passam a passar, quantos passam a falhar) entra na mensagem
de commit, junto com a razão.

**Regra:** alargar um critério que penaliza outra forma de dizer a mesma coisa
é afinação; alargá-lo para o modelo passar não é aceitável. Cada alteração a
um critério é registada no commit com a justificação.

## 8. Amostras repetidas

```
python3 -m aferidor ensaio --fornecedor openai --modelo <nome> --repeticoes 5 --temperatura 1.0
```

Um modelo que acerta a dose em 4 de 5 amostras erra a dose na prática: o
médico observa uma única resposta. Por isso o relatório conta casos com falha
crítica em pelo menos uma amostra.

**Recomenda-se `--temperatura 1.0`.** A temperatura 0 devolve sempre a
resposta mais provável e oculta a variabilidade que o ensaio pretende medir;
os produtos reais raramente usam temperatura 0.

## 9. Comparação de modelos

```
python3 -m aferidor ensaio --fornecedor openai --modelo <nome>
python3 -m aferidor ensaio --fornecedor anthropic --modelo <nome>
```

As respostas dos vários modelos coexistem no mesmo ficheiro e o relatório
inclui uma tabela de comparação: casos com falha crítica, casos corretos pela
regra do relatório, casos inconsistentes e amostras corretas, cada um
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
python3 -m aferidor ensaio --fornecedor local --modelo qwen3:8b --tokens-max 8192
```

Uma resposta truncada fica por responder e não é repetida automaticamente com
mais tokens, para não misturar duas medições no mesmo ficheiro. A solução é
repetir o ensaio desde o início com um `--tokens-max` maior.

**Os modelos de raciocínio da OpenAI (`o1`, `o3`, `gpt-5` e semelhantes)
costumam aceitar apenas `--temperatura 1.0`** e usar `max_completion_tokens` em
vez de `max_tokens`. O `OpenAIProvider` envia `max_completion_tokens`, verificado
apenas com pedidos simulados, e nenhuma destas duas regras está confirmada na
documentação oficial da OpenAI, cujas páginas da API não abriram quando se
tentou (ficam «por confirmar» no catálogo). Recomenda-se confirmar com
`--limite 1`, ou com o piloto da secção 15, antes de uma execução completa.

## 11. Ensaio de comparação completo

Três modelos, cinco amostras por caso, temperatura 1,0.

**Modelos locais, através do Ollama** (sem custo e sem envio de dados para o
exterior). Após instalar o Ollama (ollama.com) e descarregar os modelos
(`ollama list` confirma que está ativo):

```
python3 -m aferidor ensaio --fornecedor local --modelo <nome-a> --repeticoes 5 --temperatura 1.0 --tokens-max 8192
python3 -m aferidor ensaio --fornecedor local --modelo <nome-b> --repeticoes 5 --temperatura 1.0 --tokens-max 8192
python3 -m aferidor ensaio --fornecedor local --modelo <nome-c> --repeticoes 5 --temperatura 1.0 --tokens-max 8192
python3 -m aferidor relatorio --formato html
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

## 12. Validação por um clínico (ainda sem revisor)

Não há hoje um revisor clínico, por isso nenhum resultado foi validado. Quando
houver, deve julgar uma amostra das respostas antes de se apresentarem
resultados:

```
python3 -m aferidor revisao --respostas data/respostas.jsonl --n 60
```

Enviar `relatorios/revisao.csv`, **nunca** `revisao-chave.json`, que contém as
decisões do corretor. Com a coluna `juizo` preenchida:

```
python3 -m aferidor concordancia --revisao relatorios/revisao.csv
```

O primeiro valor apresentado é o mais relevante: o número de respostas erradas
aprovadas pelo corretor. Se for elevado, os resultados do ensaio sobrestimam o
modelo.

## 13. Recomeçar do zero

```
python3 -m aferidor ensaio --fornecedor openai --modelo <nome> --recomecar
```

Descarta as respostas anteriores do modelo e repete todos os pedidos, com o
custo correspondente. As novas respostas não serão iguais às anteriores. Num
modelo pago, pede confirmação escrita e o gasto anterior continua a contar para
o teto (secção 15).

## 14. Regenerar o relatório de exemplo

O relatório publicado em `docs/exemplo/` (o que o README liga) não é de um
ensaio só: junta as respostas de quatro modelos no banco principal atual, vindas
de três ensaios. Corrigem-se com o corretor de hoje, pelo que os números mudam
quando o corretor muda e o exemplo tem de ser regenerado, não editado.

```
cat ensaios/2026-09-29-gemma4-31b-casos/respostas.jsonl \
    ensaios/2026-09-28-gemini-flash/respostas.jsonl \
    ensaios/2026-09-27-locais-12-14b/respostas.jsonl > /tmp/exemplo-respostas.jsonl
python3 -m aferidor relatorio --formato html --linguas pt,en,es,fr,de \
  --casos casos/casos.json --respostas /tmp/exemplo-respostas.jsonl \
  --antes docs/exemplo/antes-8edda161.json --saida docs/exemplo/index.html
```

O `--antes` põe o publicado e o corrigido lado a lado em Resultados e conta, em Método, o que a correção de
12/10/2026 tocou: lê os veredictos do corretor publicado em `docs/exemplo/antes-8edda161.json` (que se gera com
`scripts/antes_8edda161.py` num `git worktree` do commit `e272ab9`, só de leitura) e volta a corrigir, com o corretor de
hoje, as respostas guardadas de `ensaios/` que esse ficheiro lista, recusando o ficheiro se o SHA-256 de alguma já não
for o que ele leu. A reclassificação de cada ensaio, em ficheiros novos ao lado dos originais, faz-se com
`python3 scripts/reclassificar.py 2026-10-12`.

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

## 15. Correr modelos de fornecedores

Esta secção cobre os modelos que o `aferidor/catalogo.json` lista (hoje, a
Anthropic, a OpenAI, o Google e a Amália num servidor próprio). Só houve, a 2026-10-11,
um piloto de 3 casos por 2 amostras com a Amália em GGUF e com o Gemini 3.8 Flash, e nenhum ensaio
completo: o resto do que aqui se descreve foi testado com respostas simuladas, escritas à mão a partir
da documentação oficial.

**1. Chaves.** Uma variável de ambiente por fornecedor (`ANTHROPIC_API_KEY`,
`OPENAI_API_KEY`, `GEMINI_API_KEY`) ou, na falta dela, uma linha `NOME=valor` num
ficheiro `.env` na raiz do repositório. O `.env` está no `.gitignore`; confirma
com `git check-ignore .env`. A chave nunca vai para o repositório, nem para uma
opção da linha de comandos (não existe nenhuma), nem para uma conversa. O
Aferidor não a imprime: um erro nomeia a variável que falta, nunca o valor.

**2. O catálogo.** `aferidor/catalogo.json` guarda, por modelo, o id, os preços
por período com a página de onde vieram e o dia em que foram lidos, e os
parâmetros. Os ids e os preços não estão no código. Três palavras a saber:
`verificado_em_execucao: false` quer dizer que o id e o preço ainda não foram
confrontados com o que o fornecedor lista; «desconhecido» é o que ninguém sabe
ainda; e `por_confirmar` lista o que a documentação oficial lida não diz, por
modelo. Onde não se sabe como o fornecedor conta os tokens de raciocínio, cada
chamada conta-se pelo pior caso. Lê o catálogo e confirma os preços nas páginas
dos fornecedores antes de gastar, porque mudam.

**3. Estimar sem gastar.**

```
python3 -m aferidor executar --fornecedor anthropic --modelo claude-opus-5-5 --a-seco --tokens-max 8192 --repeticoes 5
```

Mede os prompts reais, estima o custo em três cenários de saída e sai com 0. Não
chama ninguém, não precisa de chave e não escreve nada. A entrada
estima-se por caracteres a dividir por três, e esse fator depende do tokenizador: no piloto de 2026-10-11
sobrestimou o Gemini (1,2 vezes) e subestimou a Amália em GGUF no Ollama (ficou a cerca de metade do declarado), por isso
não é um limite superior. A saída depende de quanto o modelo escreve e raciocina, por isso o cenário maior é o que o teto
protege.

**4. O teto.** `--teto-eur` é obrigatório para um modelo do catálogo, sem valor
por omissão (só o que custa zero, a Amália, dispensa-o). Antes de cada chamada,
o gasto acumulado mais o pior caso dessa chamada tem de caber no teto; senão a
corrida pára antes de chamar. O teto é do ensaio inteiro: soma todos os modelos
que correram na mesma pasta. O gasto fica no `custos.jsonl`, ao lado das
respostas, que só acrescenta.

**5. O piloto.**

```
python3 -m aferidor executar --fornecedor anthropic --modelo claude-opus-5-5 --piloto --teto-eur 5 --temperatura 1.0 --tokens-max 8192
```

Pergunta três casos (ATB-PAC-001, PED-OMA-021 ou, se não existir, ATB-FAR-004, e
GRA-VPA-024), duas vezes cada, e diz quais escolheu. Serve para ver o custo real,
as recusas, as respostas truncadas, se o modelo aceita a temperatura pedida e se
o tempo limite chega (os 60 s herdados podem ser curtos para modelos que
raciocinam; está no catálogo, em `tempo_limite_s`). Grava tudo numa subpasta
`piloto/`, com respostas, livro e proveniência próprios, para não gastar as
amostras do ensaio. Tem por isso um teto próprio, e o gasto máximo efetivo de
piloto mais ensaio é a soma dos dois tetos. `ensaio --piloto` não existe: o
piloto corre-se com `executar`.

**6. O ensaio.** Com o protocolo escrito e commitado antes (secção 5):

```
python3 -m aferidor ensaio --fornecedor anthropic --modelo claude-opus-5-5 --teto-eur 50 --temperatura 1.0 --tokens-max 8192 --repeticoes 5 --protocolo protocolos/<nome>.json
python3 -m aferidor executar --fornecedor google --modelo <id do catálogo> --teto-eur 50 ...
python3 -m aferidor executar --fornecedor local-compativel --modelo amalia-9b-0626-dpo --base-url http://localhost:8000/v1 ...
```

Sem `--temperatura`, um modelo cuja temperatura o catálogo fixa corre a 1,0, e um
valor diferente é recusado antes de qualquer pedido. Os da Anthropic do catálogo
não aceitam outra temperatura que não a 1,0: a chamada vai sem temperatura, o que
a proveniência regista como pedida 1,0 e aplicada «ausente». Os Gemini 3.x do
catálogo correm a 1,0 por recomendação da Google (que a recomenda, e a API aceitaria
outro valor): o pedido leva 1,0 e a proveniência regista pedida 1,0 e aplicada 1,0.
O piloto do Gemini de 2026-10-11 correu a **0,0**, contra a recomendação da Google para os modelos Gemini 3 (manter a temperatura em 1,0, o valor por omissão; fonte: https://ai.google.dev/gemini-api/docs/gemini-3, lida inteira a 2026-10-11, que a recomenda sem a impor e não indica a gama válida). As corridas seguintes dos Gemini 3.x do catálogo correm a 1,0, fixo, e recusam outro valor. Por isso as respostas do piloto do Gemini e as das corridas seguintes não se comparam sem esta ressalva. O valor por omissão do projeto é 0,0 (foi o do piloto da Amália), os ensaios registados correram a 1,0 e a diferença para o Gemini vem da recomendação do fabricante, não de uma escolha do Aferidor sobre o que mede melhor. `--fornecedor gemini` é o endpoint compatível dos ensaios guardados e pede sempre
`--modelo`; `google` é a API própria do Google. O servidor compatível (um vLLM,
por exemplo) pergunta a `/models` o que tem carregado e recusa se o modelo pedido
não estiver lá.

**7. Códigos de saída.** 0: completo. 1: houve casos por responder. 2: o comando
recusou arrancar (falta o teto, falta uma chave, as condições da retoma diferem,
um modelo não aceita a temperatura pedida). 3: a
corrida parou de propósito, porque o teto seria ultrapassado ou porque o
fornecedor serviu outro modelo que não o pedido. Com 3, o que já estava guardado
fica, e o `ensaio` não classifica nem escreve o relatório.

**8. Quando uma corrida fica a meio.**

- Uma amostra que deu tempo limite pode ter sido cobrada, por isso não se repete
  sozinha. `--repetir-incertas` pede de novo as amostras sem resposta guardada
  cujo resultado ficou incerto (tempo limite, ou reservadas e nunca liquidadas);
  cada repetição custa de novo, fica ligada à anterior, e o teto conta as duas.
- Uma resposta truncada, recusada pelo fornecedor ou vazia foi paga, fica escrita
  e não se repete, nem com a flag. Se se deve repetir é uma decisão que o Fábio
  ainda não tomou.
- `--recomecar` num modelo pago mostra o gasto acumulado, pede que escrevas
  `RECOMECAR` e uma razão, regista o recomeço no livro e só depois apaga as
  respostas. O livro não se apaga: o gasto anterior continua a contar para o
  teto. Sem terminal para confirmar, recusa.

**9. O que o relatório mostra.** Ao lado das contagens, sem as mudar: as amostras
não respondidas por modelo (um modelo com mais de 10% fica marcado «não
comparável com os restantes»), as condições em que cada modelo correu (pedido e
servido, temperatura pedida e aplicada, contagem do custo, preço, taxa e SHA-256
do catálogo) e o custo em euros, com o piloto à parte. Se as temperaturas
aplicadas diferem entre modelos, diz que a comparação não é em condições
idênticas.

**Avisos.**

- Não correr dois processos ao mesmo tempo no mesmo ensaio: uma reserva ainda a
  meio de uma chamada de outro processo parece uma reserva órfã, e
  `--repetir-incertas` pagaria duas vezes.
- Não renomear a pasta de um ensaio pago: o id do ensaio no livro é o nome da
  pasta, e o livro deixaria de reconhecer o que já se gastou.
- O custo que o Aferidor mostra é o pior caso onde não se sabe como o fornecedor
  conta, e um máximo não é uma fatura. A fatura confirma-se na consola do
  fornecedor, e o piloto é a ocasião de comparar as duas.
- A estimativa de tokens da entrada não foi comparada com a de nenhum
  fornecedor, e o bloqueio do livro só foi testado no caminho POSIX, em macOS.
