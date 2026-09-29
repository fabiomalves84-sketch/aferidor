# Aferidor

Banco de ensaio para respostas clínicas de modelos de linguagem em português
europeu. Avalia; não aconselha.

**Relatório de exemplo:**
https://fabiomalves84-sketch.github.io/aferidor/exemplo/ (Gemini 3.5 Flash Lite
pela API e dois modelos locais, 27 casos, 5 amostras por caso, ensaios de 27 e
28/09/2026; em português, inglês, espanhol, francês e alemão).

## Instalação e primeira execução

Requer Python 3.10 ou superior. Não tem dependências externas.

```
git clone https://github.com/fabiomalves84-sketch/aferidor.git
cd aferidor
python3 -m unittest discover -s tests          # 455 testes
python3 -m aferidor verificar                  # coerência dos casos e do corretor
python3 -m aferidor ensaio --fornecedor falso  # ensaio de demonstração, sem chave nem custo
```

O último comando escreve `relatorios/relatorio.md`; `relatorio --formato html`
gera a versão HTML, e `--linguas pt,en,es,fr,de` gera-a também em inglês,
espanhol, francês e alemão, com um menu entre elas (só a interface é
traduzida; casos e respostas ficam em português). Para atualizar uma cópia
existente: `git pull`.

A execução contra um modelo real (OpenAI, Anthropic, Google Gemini ou local
através do Ollama) está descrita em `docs/COMO_CORRER.md`. As chaves de API
são lidas do ambiente e nunca do repositório.

## O problema

Um assistente que responde a um médico sobre dose, interação ou
contraindicação participa numa decisão terapêutica. Um modelo com 92% de
respostas corretas parece adequado; se os 8% de erros forem doses pediátricas,
é perigoso. A média oculta precisamente o que importa.

## Funcionamento

1. Mantém casos clínicos de referência, cada um com a resposta correta, a
   fonte pública e critérios de aceitação definidos antes de qualquer ensaio.
2. Coloca cada pergunta ao modelo várias vezes e regista cada resposta com as
   condições em que foi obtida. O modelo nunca vê a resposta de referência.
3. Corrige cada resposta contra os critérios, de forma textual e determinista,
   e classifica cada falha por tipo e por risco clínico.
4. Produz um relatório que começa pelos casos com falha crítica, com
   intervalos de confiança e as condições do ensaio.
5. Prepara a validação pelo especialista: cada falha com a pergunta, a
   referência, a fonte e a resposta do modelo, e uma folha cega para julgar
   uma amostra de respostas sem conhecer o veredicto do corretor.

**A ferramenta faz a triagem; o especialista valida.** O veredicto do corretor
é uma proposta. A decisão sobre a adequação de um modelo é clínica, e o
Aferidor concentra o tempo do especialista nas respostas relevantes. A
concordância entre ambos é medida (`revisao` e `concordancia`, kappa de
Cohen).

O instrumento é verificado antes do ensaio: cada critério tem de aceitar a
resposta de referência e rejeitar uma resposta errada construída para o
efeito.

## Âmbito

**Não é um dispositivo médico.** Não aconselha, não trata e não substitui o
julgamento clínico. **Não contém dados de doentes:** todos os casos provêm de
documentos públicos ou são sintéticos.

## Taxonomia de falhas

| Tipo | Significado | Risco |
|---|---|---|
| `dose_incorreta` | Valor, unidade ou intervalo errados | Crítico |
| `interacao_omitida` | Interação relevante não assinalada | Crítico |
| `contraindicacao_omitida` | Contraindicação não assinalada | Crítico |
| `alucinacao` | Facto inexistente ou fonte inventada | Crítico |
| `encaminhamento_omitido` | Situação urgente não encaminhada | Crítico |
| `ajuste_omitido` | Ajuste renal, hepático ou pediátrico em falta | Alto |
| `resposta_incompleta` | Correta, mas insuficiente para decidir | Médio |
| `recusa_indevida` | Recusa de uma pergunta legítima | Baixo |
| `formato_invalido` | Formato pedido não respeitado | Baixo |

## Estado

**O instrumento está completo; a validação clínica está por fazer.**

- Dois bancos, 57 casos: antibioterapia, interações, gravidez e ajuste de dose
  (`casos/casos.json`); consulta de adulto, criança e cessação tabágica
  (`casos/consulta.json`). Os casos de infeção seguem as normas da DGS.
- `verificar`: 27/27 e 30/30 casos coerentes; 307/307 e 138/138 controlos
  negativos detetados. 455 testes, em Python 3.10 a 3.14 na integração
  contínua.
- Fontes: 34 de 57 confirmadas por uma pessoa; das restantes, 16 lidas no
  documento original e 7 por confirmar. Detalhe em `casos/VERIFICACAO.md`.

O primeiro ensaio pela API, com protocolo definido antes da execução, mediu o
Gemini 3.5 Flash Lite (`ensaios/2026-09-28-gemini-flash/`). Em falta: a revisão
de uma amostra de respostas por um clínico, que ainda não tem revisor (a folha
cega gera-se com `aferidor revisao` e fica pronta para quando houver), e a
confirmação das fontes restantes.

## Documentação

- `docs/APRESENTACAO.md`: apresentação do projeto, para leitura sem código
- `docs/METODO.md`: método de medição, limites conhecidos e ensaios registados
- `docs/ARQUITETURA.md`: módulos, fronteiras entre eles e respetiva justificação
- `docs/COMO_CORRER.md`: execução contra um modelo real e afinação de critérios
- `casos/VERIFICACAO.md`: confirmação das fontes, caso a caso
- `casos/FONTES_DGS.md`: normas da DGS utilizadas e divergências encontradas
- `ensaios/`: execuções registadas, cada uma com o respetivo README
