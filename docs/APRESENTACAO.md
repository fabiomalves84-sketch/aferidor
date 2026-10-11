# Aferidor: apresentação

Documento de apresentação do projeto, para leitura sem abrir o código.

## Contexto

Um assistente de inteligência artificial que responde a um médico sobre dose,
interação ou contraindicação participa numa decisão terapêutica. A questão
relevante não é a qualidade da redação, mas a frequência com que acerta, o
tipo de erro que comete e o custo clínico de cada erro.

Um sistema com 92% de respostas corretas parece adequado. Se os 8% de erros
forem doses pediátricas, é perigoso. A média oculta precisamente o que
importa.

## O projeto

O Aferidor é um instrumento de medida. Mantém perguntas clínicas com resposta
correta conhecida e citável, envia-as a um modelo de linguagem, corrige cada
resposta contra os critérios de cada caso, em código e com histórico de
alterações, e classifica cada falha por tipo e por risco clínico.

O relatório apresenta, antes de qualquer percentagem, os casos com falha de
risco crítico, cada um com a pergunta, a resposta de referência, a fonte e o
texto do modelo.

## Utilização: triagem automática, sem validação clínica

O Aferidor não substitui o clínico que avalia um modelo. Coloca cada caso
várias vezes, corrige todas as respostas de forma determinista e ordena as
falhas por risco, e quem lê o relatório vê primeiro as falhas críticas, com a
evidência para confirmar ou contestar cada veredicto. Não há revisor clínico: os
veredictos são triagem, sem validação. A folha cega (`aferidor revisao`) e a
medida de concordância (`aferidor concordancia`) estão preparadas para o dia em
que houver um revisor: a primeira dá a uma pessoa uma amostra de respostas sem a
decisão do corretor, a segunda mede o acordo entre ambos. Enquanto não houver,
essa medida não existe, e o grau de confiança que a triagem merece não está
medido.

## Âmbito

**Não é um dispositivo médico.** Não aconselha, não trata e não substitui o
julgamento clínico.

**Não contém dados de doentes.** Todos os casos provêm de documentos públicos
(normas portuguesas e diretrizes internacionais) ou são sintéticos.

**Não avalia nenhum produto comercial específico.** Os casos são genéricos.

## Estado atual

- **Dois bancos, 58 casos**, cada um com fonte pública identificada: 27 de
  antibioterapia, interações, gravidez e ajuste de dose; 31 de consulta de
  adulto, criança e cessação tabágica. Vários casos formam pares que testam
  uma distinção clínica (pneumonia com e sem comorbilidades; hipersensibilidade
  tipo I e não tipo I). Os casos de infeção seguem as normas da DGS; quando
  duas fontes reconhecidas divergem de forma defensável, o caso aceita ambas.
- **Corretor verificado nos dois sentidos.** A resposta de referência de cada
  caso tem de passar e uma resposta errada construída para cada critério tem
  de falhar: 319 e 140 controlos negativos, todos detetados.
- **Rastreabilidade.** Cada resposta regista o SHA-256 do texto enviado, a
  temperatura, o limite de tokens e a versão do código. Uma retoma recusa
  condições diferentes. O relatório indica o banco, as condições e as datas.
- **Critério de aprovação prévio, opcional**, definido num protocolo escrito
  antes do ensaio. Sem protocolo, o relatório usa o limiar de referência e diz
  que não é prévio; com protocolo, indica aprovado ou reprovado e assinala os
  escritos depois do ensaio.
- **Folha cega e medida de concordância com o corretor**, preparadas para uma
  revisão clínica que ainda não tem revisor.
- Intervalos de confiança nos resultados principais e um indicador de
  português europeu independente das falhas clínicas.
- Adaptadores para OpenAI, Anthropic, Google Gemini e modelos locais através
  do Ollama.
- 1157 testes automáticos, sem dependências externas.

Limitações conhecidas:

- **Não há validação clínica nem revisor.** O circuito está pronto e a folha
  cega gera-se com um comando, mas ninguém a julgou: os resultados dos ensaios
  registados são a triagem do corretor, sem validação, e os relatórios dizem-no
  no topo.
- **Fontes parcialmente confirmadas.** 10 casos confirmados nos PDF da DGS, um
  a um; 24 declarados confirmados em grupo; os 24 restantes lidos no
  documento original por ferramenta, todos coincidentes, à espera de
  confirmação por uma pessoa. Detalhe em
  `casos/VERIFICACAO.md`.
- **Um único modelo comercial medido.** O ensaio de 28/09 mediu o Gemini 3.5
  Flash Lite pela API gratuita (11 de 27 casos com falha crítica, reprovado pelo
  protocolo); os restantes ensaios usam modelos locais de 8 a 14 mil milhões de
  parâmetros.
- **A correção é textual.** A distinção entre prescrever um fármaco e
  mencioná-lo para o excluir é heurística; `docs/METODO.md` descreve onde falha.

## Relação com normas de qualidade

A ISO/IEC 42001 exige avaliação de desempenho documentada e tratamento dos
riscos identificados. A ISO 13485 e o Regulamento de Dispositivos Médicos
exigem verificação e validação com critérios de aceitação definidos **antes**
do ensaio. O limiar de referência dos relatórios sem protocolo não é um critério
prévio, e o corretor foi afinado depois de alguns ensaios; só os protocolos de
aprovação escritos antes do ensaio são prévios. O projeto produz, à escala de
uma demonstração, esse tipo de evidência:

| Exigência | Implementação |
|---|---|
| Critérios de aceitação prévios | critérios de cada caso, em código, com a razão de cada alteração no commit (o corretor foi afinado depois de alguns ensaios); protocolo de aprovação opcional (`aferidor protocolo`), escrito antes do ensaio |
| Rastreabilidade à fonte | documento e página em cada caso |
| Verificação dos dados de origem | `casos/VERIFICACAO.md` e comando `verificar` |
| Classificação de falhas por risco | `aferidor/risk.py` |
| Registo íntegro dos resultados | `data/respostas.jsonl`, escrito à medida que as respostas chegam; em cada ensaio registado, `MANIFESTO.sha256` com o SHA-256 de cada ficheiro (`aferidor manifesto --verificar`) |
| Relatório para revisão humana | `relatorios/relatorio.md` e `.html`, com condições do ensaio e intervalos de confiança |
| Validação do método de medida | `aferidor revisao` e `concordancia`, preparados e ainda sem revisor: corretor contra uma pessoa, às cegas |
| Requisitos rastreáveis e gestão de riscos | `docs/QUALIDADE.md`: 39 requisitos ligados aos testes que os verificam, 13 riscos do instrumento com mitigação e risco residual; um teste garante que os testes citados existem |

O comando `verificar` avalia a resposta de referência de cada caso contra os
seus próprios critérios. Na primeira execução detetou dois casos defeituosos
em dez, ambos no sentido mais grave: classificariam como errado um modelo que
acertou. Desde setembro de 2026 verifica também o sentido inverso: para cada
critério, altera a resposta de referência no ponto que o critério avalia e
exige que a falha seja detetada. Na primeira execução, dez respostas erradas
passaram (um fármaco contraindicado, prescrito na frase seguinte à
contraindicação, era dado como excluído). A correção foi feita no corretor,
não nos casos.

## Demonstração

```
python3 -m unittest discover -s tests   # 1157 testes
python3 -m aferidor verificar           # 27/27 casos, 319/319 controlos negativos
python3 -m aferidor verificar --casos casos/consulta.json   # 31/31, 140/140
python3 -m aferidor executar --fornecedor falso
python3 -m aferidor relatorio           # escreve relatorios/relatorio.md
```

Nenhum destes comandos requer chave de API nem ligação à internet.

Para ler o código, a ordem recomendada é `risk.py`, `models.py` e `checks.py`,
que concentram as decisões principais. `docs/ARQUITETURA.md` descreve as
fronteiras entre módulos.
