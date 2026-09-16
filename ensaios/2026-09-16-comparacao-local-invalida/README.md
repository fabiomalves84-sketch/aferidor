# Ensaio de 16 de setembro de 2026 (inválido)

Ensaio de comparação completo: 27 casos × 5 amostras × 2 modelos locais pelo
Ollama (`llama3.1:8b` e `qwen3:8b`), temperatura 1,0. Correu até ao fim, sem
nenhum caso por responder por falha de rede ou de servidor. **Os números não
podem ser apresentados**, e a causa é do instrumento, não dos modelos.

## O que correu mal

O `max_tokens` da chamada ao modelo estava fixo em 1024, e nenhum dos dois
adaptadores locais avisava quando a resposta vinha cortada por esse limite.

O `qwen3:8b` raciocina em texto antes de escrever a resposta, e gasta nesse
raciocínio o orçamento de tokens quase todo:

- **35 das 135 respostas chegaram completamente vazias.** O raciocínio
  consumiu o limite antes de a resposta começar.
- **A maioria das restantes acaba a meio da frase.** Reproduzido à mão com
  `PED-OMA-019`: a 1024 tokens, `finish_reason` "length" e conteúdo vazio; a
  4096, `finish_reason` "stop" e resposta completa com 1857 caracteres.

O `llama3.1:8b` não raciocina em voz alta e por isso saiu muito menos
afetado, mas sofre do mesmo problema numa escala menor: um punhado das suas
135 respostas também ficou cortado a meio.

O corretor (`grading.grade`), tal como estava nesta altura, não distinguia
uma resposta vazia de uma resposta errada: contava uma dose nunca mencionada
como `dose_incorreta`, e uma resposta cortada a meio de uma frase como
`resposta_incompleta` — os dois tipos de falha de risco mais alto que o
banco mede. As contagens deste ensaio estão inflacionadas por um erro do
instrumento, não por erro dos modelos.

**É o mesmo erro da metformina (`AJU-MET-018`, corrigido a 14/09), noutro
sítio.** Da primeira vez a fonte de referência estava desatualizada; desta
vez foi o limite de tokens do instrumento. Nos dois casos o banco deu como
errado quem não tinha, de facto, errado.

## Porque fica, e não se apaga

Uma medição inválida detetada e documentada é evidência de método. Apagá-la
deixaria só o número, sem a explicação de que ele não vale nada — e um
ensaio destes correu, custou tempo de máquina real, e o que se aprendeu com
ele (`max_tokens` tem de acompanhar o modelo, e um caso sem resposta válida
não pode entrar em contagem nenhuma) já está no código: a flag `--tokens-max`
de `executar` e `ensaio`, descrita na secção 9 de `docs/COMO_CORRER.md`.

## O que está aqui

- `respostas.jsonl`: as 270 respostas (135 por modelo), exatamente como
  vieram do Ollama.
- `vereditos.json`: os vereditos que o corretor desta altura produziu contra
  essas respostas — inválidos pela razão acima, mantidos por completude.
- `relatorio.md`: o relatório escrito a partir desses vereditos.

## O que fazer a seguir

O ensaio é repetido do zero (`--recomecar`), com os mesmos dois modelos,
5 repetições, temperatura 1,0 e `--tokens-max` acima da omissão. Só depois
disso os números de uma comparação entre estes dois modelos contam. Quem
corre é o Fábio.
