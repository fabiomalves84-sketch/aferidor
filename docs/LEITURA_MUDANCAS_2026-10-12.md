# Leitura das mudanças de falha crítica, 12/10/2026

Compara o corretor publicado até 12/10 (`0.1.0+corretor.8edda161bd4e`, veredictos em `docs/exemplo/antes-8edda161.json`) com o
corrigido (`0.1.0+corretor.8404de4a7c95`), sobre as respostas guardadas dos sete ensaios da tabela da página de exemplo: o banco
principal (27 casos) e o de consulta (30 e 31 casos), para os cinco modelos. Um caso **muda de estado** para um modelo quando passa a
ter, ou deixa de ter, uma falha crítica em alguma das amostras; cada mudança está numa linha, e li todas, sem amostrar. As
respostas citadas são as originais; `ATB-PIEL-006` e os outros casos aqui são lidos contra a referência do caso.

**Resultado: 11 mudanças de estado, todas de «passa a ter falha crítica»; nenhuma deixa de a ter. Classes: (a) 9, (b) 2, (c) 0.**
Quem leu foi uma só pessoa, sem revisão. É triagem automática, sem validação clínica. Os ensaios mais antigos (agente e 16 de setembro)
não entram aqui.

Classes: **a** mudança correta (a resposta dá a dose ou o intervalo de outro fármaco, de um ajuste, ou de um fármaco que a norma
citada não inclui); **b** falso falhanço ou falso passe; **c** ambígua.

| Modelo | Caso | Amostras | Critério | Frase da resposta | Classe |
|---|---|---|---|---|---|
| `local:gemma3:12b` | ATB-PIEL-006 | 1, 2, 3, 4, 5 | intervalo 12/12, ancorado à cefuroxima | «Dose Ciprofloxacino: 500 mg, de 12 em 12 horas.» (a1); nas outras, cotrimoxazol, «2x ao dia» e «12/12 horas», e nenhuma cefuroxima | a |
| `local:gemma3:12b` | ATB-DPOC-012 | 1 | intervalo 8/8 | «Dose: 300-450 mg de 8 em 8 horas.» (clindamicina) | a |
| `local:gemma3:12b` | AJU-APX-025 | 4 | dose 2,5 mg | «uma dose mais baixa (2,5 mg duas vezes ao dia) em doentes com fatores de risco»; a dose recomendada é 5 mg duas vezes ao dia | a |
| `local:phi4:14b` | ATB-PIEL-006 | 1, 2, 3, 4, 5 | intervalo 12/12, ancorado à cefuroxima | «Dose: 1 g via oral a cada 12 horas.» (cefalexina, a1); nas outras, co-trimoxazol «duas vezes ao dia» | a |
| `gemini:gemini-3.5-flash-lite` | ATB-PIEL-006 | 1, 2, 3, 4, 5 | intervalo 12/12, ancorado à cefuroxima | «Ciprofloxacina: 500 mg a 750 mg, de 12 em 12 horas, durante 7 dias.» (a2) | a |
| `gemini:gemini-3.5-flash-lite` | ATB-FAR-014 | 1, 2, 3, 4, 5 | dose 250 mg e intervalo 12/12, ancorados à cefuroxima | «Dose: 500 mg por via oral, a cada 12 horas (ou 250 mg a cada 6 horas).» (cefalexina, a2; a norma citada é omissa e o caso está ancorado à cefuroxima) | a |
| `gemini:gemini-3.5-flash-lite` | ATB-FAR-004 | 1 | dose 500 mg, ancorada à azitromicina | «Dose: 500 mg por via oral, em toma única diária.», sob «Opção 1: Azitromicina», com a penicilina nomeada na frase entre o cabeçalho e a dose | b |
| `gemini:gemma-4-31b-it` | ATB-PAC-001 | 1, 2, 3, 4, 5 | dose 500 mg, ancorada à amoxicilina | «ClCr 10-30 mL/min: 250 mg a 500 mg de 12 em 12 horas.» (a1); a dose principal é «1 g» | a |
| `gemini:gemma-4-31b-it` | ATB-PIEL-006 | 1, 2, 3, 4, 5 | intervalo 12/12, ancorado à cefuroxima | «Intervalo: de 12 em 12 horas» (Opção A, ciprofloxacina) | a |
| `gemini:gemma-4-26b-a4b-it` | ATB-FAR-004 | 2 | dose 500 mg, ancorada à azitromicina | «Dose: 500 mg.» é da claritromicina; a azitromicina («500 mg no 1.º dia») perde a dose por uma comparação com a claritromicina que não está na lista fechada | b |
| `gemini:gemma-4-26b-a4b-it` | ATB-PIEL-006 | 1, 2, 3, 4, 5 | intervalo 12/12, ancorado à cefuroxima | «Intervalo: De 12 em 12 horas.» (Opção A, ciprofloxacina) | a |

## O que os dois (b) mudam nos números da página

Os dois (b) são o padrão (i) das limitações: um fármaco nomeado na frase que abre a secção fica com a dose que vem a seguir. Cada
um é a única causa de falha crítica de ATB-FAR-004 para o seu modelo, por isso cada um sobe de um número a tabela do banco principal:

- **Gemini 3.5 Flash Lite, banco principal:** 14 no corrigido; sem o (b) de ATB-FAR-004 seriam **13**. O McNemar exato entre os dois
  melhores passaria de p = 0,125 (0 contra 4) para p = 0,25 (0 contra 3).
- **Gemma 4 26B, banco principal:** 13 no corrigido; sem o (b) seriam **12**.
- Os outros números da tabela não mudam, e o melhor modelo é o mesmo.

Nada disto se ajustou: nem as regras nem os critérios. Fica escrito.
