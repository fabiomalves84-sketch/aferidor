# Aferidor

Banco de ensaio para respostas clínicas de modelos de linguagem em português
europeu. Mede, não aconselha.

**Ver um relatório de exemplo:**
https://fabiomalves84-sketch.github.io/aferidor/exemplo/ (dois modelos locais,
27 casos, 5 amostras por caso, ensaio de 16/09/2026).

## Começar

Precisa de Python 3.10 ou superior e de nada mais: só a biblioteca padrão.

```
git clone https://github.com/fabiomalves84-sketch/aferidor.git
cd aferidor
python3 -m unittest discover -s tests          # 375 testes
python3 -m aferidor verificar                  # os casos e o corretor estão coerentes?
python3 -m aferidor ensaio --fornecedor falso  # ensaio a seco, sem chave nem custo
```

O último comando escreve `relatorios/relatorio.md`. Com `relatorio --formato
html` sai o mesmo relatório num ficheiro HTML. Para atualizar uma cópia já
clonada: `git pull`.

Para correr contra um modelo real (OpenAI, Anthropic, ou local pelo Ollama),
ver `docs/COMO_CORRER.md`. As chaves vêm do ambiente, nunca do repositório.

## O problema

Um assistente clínico que responde a um médico sobre dose, interação ou
contraindicação está a participar numa decisão terapêutica. Um modelo que acerta
92% das perguntas parece bom; se os 8% que falha forem todos doses pediátricas, é
perigoso. A média esconde exatamente aquilo que precisa de ser visto.

## O que faz

1. Guarda casos clínicos de referência, cada um com a resposta correta, a fonte
   pública que a sustenta e critérios de aceitação escritos antes de correr
   qualquer modelo.
2. Envia cada pergunta ao modelo, várias vezes, e guarda cada resposta com as
   condições em que foi obtida. O modelo nunca vê a resposta de referência.
3. Corrige cada resposta contra os critérios, de forma textual e determinista,
   e classifica cada falha por tipo e por risco clínico.
4. Produz um relatório que começa pelos casos com falha crítica, e não pela
   percentagem de acerto, com intervalos de confiança e as condições do ensaio.

O próprio instrumento é verificado: cada critério tem de aceitar a resposta
certa e de rejeitar uma resposta errada construída de propósito, e há uma
ferramenta para comparar o corretor com um clínico, às cegas.

## O que não é

**Não é um dispositivo médico.** Não aconselha, não trata e não substitui
julgamento clínico. Mede um sistema, não um doente. **Não contém dados de
doentes:** todos os casos vêm de documentos públicos ou são sintéticos.

## Taxonomia de falhas

| Tipo | O que significa | Risco |
|---|---|---|
| `dose_incorreta` | Valor, unidade ou intervalo errados | Crítico |
| `interacao_omitida` | Não assinalou uma interação relevante | Crítico |
| `contraindicacao_omitida` | Não assinalou uma contraindicação | Crítico |
| `alucinacao` | Afirmou facto inexistente ou fonte inventada | Crítico |
| `encaminhamento_omitido` | Não encaminhou uma situação urgente | Crítico |
| `ajuste_omitido` | Faltou ajuste renal, hepático ou pediátrico | Alto |
| `resposta_incompleta` | Certa mas insuficiente para decidir | Médio |
| `recusa_indevida` | Recusou uma pergunta legítima | Baixo |
| `formato_invalido` | Não respeitou o formato pedido | Baixo |

Um sistema com 5% de `dose_incorreta` e um com 5% de `formato_invalido` têm a
mesma exatidão e não têm nada a ver um com o outro.

## Estado

**O instrumento está completo; a validação ainda não.**

- Dois bancos, 57 casos: antibioterapia, interações, gravidez e ajuste de dose
  (`casos/casos.json`), e consulta de adulto, criança e cessação tabágica
  (`casos/consulta.json`). Os casos de infeção seguem as normas da DGS.
- `verificar` dá 27/27 e 30/30 casos coerentes, e 206/206 e 83/83 respostas
  erradas construídas apanhadas. 375 testes, em Python 3.10 a 3.14 na CI.
- Fontes: 34 de 57 confirmadas por uma pessoa, com duas qualidades de
  evidência; das restantes, 16 lidas no original e 7 à espera de leitura
  humana. Tudo em `casos/VERIFICACAO.md`.

Por fazer, e é o que falta para os números valerem como evidência: um clínico
julgar uma amostra de respostas reais, confirmar as fontes que faltam, e um
ensaio pela API com um protocolo escrito antes de correr.

## Documentação

- `docs/APRESENTACAO.md` o projeto em cinco minutos, para quem não abre o código
- `docs/METODO.md` como mede: fontes, correção, protocolo, revisão por um
  clínico, relatório, limites conhecidos e ensaios registados
- `docs/ARQUITETURA.md` os módulos, as fronteiras entre eles e a razão de cada uma
- `docs/COMO_CORRER.md` como correr contra um modelo real, e como afinar depois
- `casos/VERIFICACAO.md` a confirmação das fontes, caso a caso
- `casos/FONTES_DGS.md` as normas da DGS usadas, e onde divergiam dos casos
- `ensaios/` as execuções registadas, cada uma com o seu README
