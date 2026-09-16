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
  57 min de soma das latências — quase sem sobreposição). Um processo morreu
  por falta de memória a meio e foi retomado uma vez; nada se perdeu, porque
  as respostas são gravadas no disco à medida que chegam.
- **`qwen3:8b`:** 135 respostas, entre 15:40 e 20:03 (4h23 de relógio, 3h46
  de soma das latências). A máquina esteve sob pressão de memória durante
  todo este ensaio — outra sessão do Claude Code e o próprio Ollama a
  disputarem RAM ao mesmo tempo — e o processo morreu e foi retomado **sete
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

## O que ainda falta para estes números valerem como evidência final

O aviso que o próprio relatório traz continua verdadeiro: as fontes dos 27
casos ainda não estão todas confirmadas por uma pessoa contra o documento
original (`casos/VERIFICACAO.md`). Este ensaio é válido como medição —
zero respostas truncadas, os dois modelos completos — mas os números só
contam como evidência apresentável depois dessa confirmação.
