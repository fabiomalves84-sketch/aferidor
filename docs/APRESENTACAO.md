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
resposta contra critérios definidos previamente e classifica cada falha por
tipo e por risco clínico.

O relatório apresenta, antes de qualquer percentagem, os casos com falha de
risco crítico, cada um com a pergunta, a resposta de referência, a fonte e o
texto do modelo.

## Utilização: triagem pela ferramenta, validação pelo especialista

O Aferidor não substitui o clínico que avalia um modelo; prepara-lhe o
trabalho. Coloca cada caso várias vezes, corrige todas as respostas de forma
determinista e ordena as falhas por risco. O especialista recebe primeiro as
falhas críticas, com a evidência necessária para confirmar ou contestar cada
veredicto. A folha cega (`aferidor revisao`) permite-lhe julgar uma amostra de
respostas sem conhecer a decisão do corretor, e `aferidor concordancia` mede o
acordo entre ambos. Essa medida indica o grau de confiança que a triagem
automática merece em ensaios seguintes.

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
- **Critério de aprovação prévio**, definido num protocolo. O relatório indica
  aprovado ou reprovado e assinala protocolos escritos depois do ensaio.
- **Folha cega para revisão clínica** e medida de concordância com o corretor.
- Intervalos de confiança nos resultados principais e um indicador de
  português europeu independente das falhas clínicas.
- Adaptadores para OpenAI, Anthropic, Google Gemini e modelos locais através
  do Ollama.
- 528 testes automáticos, sem dependências externas.

Limitações conhecidas:

- **A validação pelo especialista ainda não foi feita nos ensaios
  registados.** O circuito está pronto e a folha cega gera-se com um comando;
  falta um clínico disponível para a julgar. Até lá, os resultados
  correspondem à triagem do corretor, e os relatórios dizem-no no topo.
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
do ensaio. O projeto produz, à escala de uma demonstração, esse tipo de
evidência:

| Exigência | Implementação |
|---|---|
| Critérios de aceitação prévios | critérios de cada caso, alterados apenas com justificação no commit; protocolo de aprovação (`aferidor protocolo`) |
| Rastreabilidade à fonte | documento e página em cada caso |
| Verificação dos dados de origem | `casos/VERIFICACAO.md` e comando `verificar` |
| Classificação de falhas por risco | `aferidor/risk.py` |
| Registo íntegro dos resultados | `data/respostas.jsonl`, escrito à medida que as respostas chegam; em cada ensaio registado, `MANIFESTO.sha256` com o SHA-256 de cada ficheiro (`aferidor manifesto --verificar`) |
| Relatório para revisão humana | `relatorios/relatorio.md` e `.html`, com condições do ensaio e intervalos de confiança |
| Validação do método de medida | `aferidor revisao` e `concordancia`: corretor contra clínico, às cegas |
| Requisitos rastreáveis e gestão de riscos | `docs/QUALIDADE.md`: 25 requisitos ligados aos testes que os verificam, 12 riscos do instrumento com mitigação e risco residual; um teste garante que os testes citados existem |

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
python -m unittest discover -s tests   # 528 testes
python -m aferidor verificar           # 27/27 casos, 319/319 controlos negativos
python -m aferidor verificar --casos casos/consulta.json   # 31/31, 140/140
python -m aferidor executar --fornecedor falso
python -m aferidor relatorio           # escreve relatorios/relatorio.md
```

Nenhum destes comandos requer chave de API nem ligação à internet.

Para ler o código, a ordem recomendada é `risk.py`, `models.py` e `checks.py`,
que concentram as decisões principais. `docs/ARQUITETURA.md` descreve as
fronteiras entre módulos.
