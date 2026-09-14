# Arquitetura

O Aferidor é uma cadeia de quatro passos, cada um num módulo próprio, e cada
fronteira entre eles existe por uma razão que se pode dizer em voz alta.

```mermaid
flowchart LR
    A[casos.json<br/>perguntas com resposta certa] --> B[runner<br/>pergunta e guarda]
    B --> C[respostas.jsonl<br/>o que o modelo disse]
    C --> D[grading + checks<br/>corrige por critérios]
    A --> D
    D --> E[vereditos.json<br/>certo, errado, que falha]
    E --> F[report<br/>documento legível]
    B -.fala com.-> P[providers<br/>OpenAI, Anthropic, falso]
```

## Os módulos

| Ficheiro | Responsabilidade |
|---|---|
| `risk.py` | A taxonomia de falhas e o risco clínico de cada uma |
| `models.py` | Caso, fonte, critério, resposta, veredito |
| `storage.py` | Ler e escrever tudo isto em JSON legível |
| `providers.py` | Falar com um modelo, atrás de uma interface estreita |
| `runner.py` | Percorrer os casos, com retentativas e retoma |
| `checks.py` | Decidir se uma resposta cumpre um critério |
| `grading.py` | Produzir vereditos e contagens separadas por risco |
| `report.py` | Escrever o documento para quem não lê código |
| `cli.py` | Os quatro comandos de terminal |

## As fronteiras que interessam

**O fornecedor nunca vê a resposta de referência.** O `runner` constrói o
texto que segue para o modelo a partir da pergunta e de mais nada. Os critérios
de aceitação e a resposta correta ficam deste lado. Um banco que mostra ao
modelo o que conta como certo não está a medir o modelo, está a medir o seu
próprio prompt. Há um teste que verifica esta fronteira diretamente.

**O corretor não é um modelo de linguagem.** É confronto de texto,
determinista e repetível. A alternativa, pôr um modelo a julgar outro, tem
dois sistemas em avaliação e nenhuma forma de saber qual deles errou. O preço
é que cada critério tem de ser escrito com cuidado, e esse preço paga-se uma
vez, quando o caso é escrito, não a cada execução.

**Os critérios são escritos antes de qualquer modelo ser executado.** Decidir
depois do facto o que conta como resposta correta é a forma mais comum de um
exercício de validação se enganar a si próprio. É também o que a ISO 13485 e o
Regulamento de Dispositivos Médicos exigem: critérios de aceitação definidos
antes do ensaio.

**As respostas são escritas à medida que chegam.** Uma execução interrompida
retoma em vez de repetir. Repetir não é só desperdício de dinheiro: a segunda
resposta do modelo à mesma pergunta é outra, e o conjunto medido deixa
silenciosamente de ser o conjunto que foi escolhido.

**Nenhuma contagem mistura modelos.** `tally` recusa vereditos de modelos
diferentes na mesma contagem, em vez de os somar.

## Sem dependências externas

Biblioteca padrão do Python apenas, incluindo os adaptadores de HTTP. Um banco
de ensaio cujo resultado muda porque uma biblioteca de terceiros mudou entre
duas execuções não mede nada de forma repetível. O custo é algum código de HTTP
escrito à mão; o ganho é que uma execução de hoje e uma de daqui a um ano
diferem no modelo e em mais nada.

## Os dados em disco

- `casos/casos.json` escrito à mão, em português, com uma fonte por caso
- `casos/VERIFICACAO.md` a tabela de confirmação humana das fontes
- `data/respostas.jsonl` uma resposta por linha, para permitir a retoma
- `data/vereditos.json` o resultado da correção
- `relatorios/relatorio.md` o documento final

Os três últimos não entram no repositório. São produto de execução, não fonte.
