# Ensaio de comparação local, 16 de setembro de 2026

27 casos × 5 amostras × 2 modelos, pelo Ollama, na mesma máquina.

## Como foi feito

- **Hardware.** MacBook Air, chip Apple M5, 16 GB de memória.
- **Ollama** 0.34.0.
- **Modelos:** `llama3.1:8b` (id `46e0c10c039e`, 4,9 GB) e `qwen3:8b`
  (id `500a1f067a9f`, 5,2 GB).
- **Parâmetros:** temperatura 1,0, 5 amostras por caso, `--tokens-max 8192`.
- **Comando:**

```
python -m aferidor ensaio --fornecedor local --modelo llama3.1:8b --repeticoes 5 --temperatura 1.0 --tokens-max 8192
python -m aferidor ensaio --fornecedor local --modelo qwen3:8b --repeticoes 5 --temperatura 1.0 --tokens-max 8192
python -m aferidor relatorio
python -m aferidor relatorio --formato html
```

- **`llama3.1:8b`:** 135 respostas, entre 14:40 e 15:38 (58 min de relógio,
  57 min de soma das latências, quase sem sobreposição). Um processo morreu
  por falta de memória a meio e foi retomado uma vez; nada se perdeu, porque
  as respostas são gravadas no disco à medida que chegam.
- **`qwen3:8b`:** 135 respostas, entre 15:40 e 20:03 (4h23 de relógio, 3h46
  de soma das latências). A máquina esteve sob pressão de memória durante
  todo este ensaio (outra sessão do Claude Code e o próprio Ollama a
  disputarem RAM ao mesmo tempo), e o processo morreu e foi retomado **sete
  vezes**. A diferença entre o tempo de relógio e a soma das latências
  (cerca de 37 minutos) é esse atrito: cada retoma tem de recarregar o
  modelo no Ollama antes de continuar. Nenhuma resposta se perdeu pela mesma
  razão do `llama3.1:8b`: gravação incremental.

## Zero respostas truncadas ou vazias

**270 de 270 respostas com `finish_reason` "stop" e texto não vazio.** É o
que distingue este ensaio do inválido do mesmo dia
(`ensaios/2026-09-16-comparacao-local-invalida/`), onde `max_tokens` a 1024
deixou 35 respostas do `qwen3:8b` completamente vazias e a maioria das
restantes cortada a meio da frase. Os dois ensaios juntos são a evidência
de método: uma medição falhada, diagnosticada e corrigida
(`ensaios/2026-09-16-comparacao-local-invalida/README.md`), e esta, feita
em condições depois da correção.

## O que saiu, sem interpretar

Os números abaixo são os que `relatorio.md` e `relatorio.html` (ambos
incluídos nesta pasta) escrevem. O que significam, clinicamente, é decisão
de quem escreve os casos, não desta execução.

| Modelo | Casos com falha crítica em alguma amostra | Casos instáveis | Taxa de amostras corretas |
|---|---|---|---|
| `local:llama3.1:8b` | 21 de 27 | 5 de 27 | 10% |
| `local:qwen3:8b` | 18 de 27 | 13 de 27 | 33% |

Falhas por tipo, `llama3.1:8b`: `dose_incorreta` 47, `resposta_incompleta`
57, `recusa_indevida` 36, `ajuste_omitido` 23, `interacao_omitida` 8,
`contraindicacao_omitida` 7, `alucinacao` 3, `formato_invalido` 1.

Falhas por tipo, `qwen3:8b`: `dose_incorreta` 42, `resposta_incompleta` 48,
`ajuste_omitido` 30, `contraindicacao_omitida` 12, `interacao_omitida` 6,
`alucinacao` 1.

## Reclassificação de 27/09/2026, depois da TAREFA 8

A TAREFA 8 corrigiu quatro erros no corretor (`checks.py`/`grading.py`,
passos A a D: números soltos dentro de decimais, dose por quilo confundida
com dose total, números escritos à portuguesa, e um aviso de cortesia
tratado como recusa). Depois desses quatro passos, `respostas.jsonl` desta
pasta foi reclassificado com o código atualizado, sem repetir nenhuma
pergunta ao modelo. **As respostas não mudaram; o instrumento que as lê,
mudou.** Os ficheiros novos, com o sufixo `-reclassificado-2026-09-27`, são
o resultado; `respostas.jsonl`, `vereditos.json`, `relatorio.md` e
`relatorio.html` originais ficam como estavam, tal como escritos em
16/09/2026.

Dos quatro passos, só o **D** (aviso de cortesia não é recusa) mudou algum
veredito neste ficheiro: confirmado comparando cada resposta contra o
corretor em cada um dos quatro passos, um de cada vez. Os passos A, B e C
não encontraram nenhum número solto dentro de um decimal, nenhuma dose por
quilo confundida com total, nem nenhum número escrito à portuguesa neste
conjunto de 270 respostas.

**Antes e depois, por modelo:**

| Modelo | Casos com falha crítica | Casos instáveis | Amostras corretas |
|---|---|---|---|
| `local:llama3.1:8b`, antes | 21 de 27 | 5 de 27 | 13 de 135 (10%) |
| `local:llama3.1:8b`, depois | 22 de 27 | 5 de 27 | 14 de 135 (10%) |
| `local:qwen3:8b`, antes | 18 de 27 | 13 de 27 | 44 de 135 (33%) |
| `local:qwen3:8b`, depois | 18 de 27 | 13 de 27 | 44 de 135 (33%) |

`qwen3:8b` não tem nenhuma resposta a mudar de veredito: as 15 respostas
que mudam são todas do `llama3.1:8b`.

**Falhas por tipo, `llama3.1:8b`, antes → depois:** `dose_incorreta` 47 → 57,
`resposta_incompleta` 57 → 64, `recusa_indevida` 36 → 21, `ajuste_omitido`
23 → 28, `contraindicacao_omitida` 7 → 9, `interacao_omitida` 8 (sem
mudança), `alucinacao` 3 → 4, `formato_invalido` 1 (sem mudança).

**Falhas por tipo, `qwen3:8b`:** sem nenhuma mudança em nenhum tipo.

**As 15 respostas que mudam de veredito, todas do `llama3.1:8b`, todas pelo
passo D:**

| Caso | Amostra | Antes | Depois |
|---|---|---|---|
| AJU-APX-025 | 4 | `recusa_indevida` | `dose_incorreta`, `ajuste_omitido` |
| AJU-APX-025 | 5 | `recusa_indevida` | `dose_incorreta`, `ajuste_omitido` |
| AJU-APX-026 | 2 | `recusa_indevida` | `dose_incorreta` |
| AJU-APX-026 | 3 | `recusa_indevida` | `dose_incorreta`, `resposta_incompleta` |
| ATB-DPOC-002 | 4 | `recusa_indevida` | `dose_incorreta`, `resposta_incompleta` |
| ATB-FAR-014 | 2 | `recusa_indevida` | `resposta_incompleta` |
| ATB-HP-007 | 5 | `recusa_indevida` | `resposta_incompleta` |
| COV-DEX-008 | 3 | `recusa_indevida` | *(passou)* |
| COV-DEX-008 | 5 | `recusa_indevida` | `dose_incorreta` |
| COV-JAN-010 | 3 | `recusa_indevida` | `alucinacao` |
| COV-TOC-009 | 1 | `recusa_indevida` | `ajuste_omitido` |
| GRA-CIST-022 | 4 | `recusa_indevida` | `dose_incorreta`, `resposta_incompleta` |
| PED-OMA-019 | 4 | `recusa_indevida` | `dose_incorreta`, `ajuste_omitido`, `resposta_incompleta` |
| PED-OMA-021 | 1 | `recusa_indevida` | `dose_incorreta`, `contraindicacao_omitida`, `ajuste_omitido`, `resposta_incompleta` |
| PED-OMA-021 | 4 | `recusa_indevida` | `dose_incorreta`, `contraindicacao_omitida` |

Das 36 respostas do `llama3.1:8b` que tinham um marcador de recusa, 21
continuam a ser recusa pura (nenhum número seguido de uma unidade de dose no
texto) e 15 tinham dose e mudam para os critérios do próprio caso.

## O que ainda falta para estes números valerem como evidência final

O aviso que o próprio relatório traz continua verdadeiro: as fontes dos 27
casos ainda não estão todas confirmadas por uma pessoa contra o documento
original (`casos/VERIFICACAO.md`). Este ensaio é válido como medição
(zero respostas truncadas, os dois modelos completos), mas os números só
contam como evidência apresentável depois dessa confirmação.

## Depois de 27/09/2026: os casos mudaram, as respostas não

Depois da reclassificação acima, vários casos do banco mudaram de fonte e, em
alguns, de pergunta: os casos de infeção passaram a seguir as normas da DGS
(ver `casos/FONTES_DGS.md`), e o ATB-PAC-001 passou de 1000 mg para 500 mg e a
dizer "previamente saudável". As respostas desta pasta foram dadas às
perguntas de 16/09, com a instrução de então, e nenhuma foi repetida.

Por isso os números desta página são os do instrumento e dos casos dessa
altura. Voltar a corrigir estas respostas com os casos de hoje mistura
perguntas que os modelos não leram com respostas que deram a outras, e não
serve para os comparar com um ensaio novo. Um ensaio novo começa do zero, com
protocolo escrito antes.

