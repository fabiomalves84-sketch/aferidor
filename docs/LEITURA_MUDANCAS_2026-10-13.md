# Leitura das mudanças de falha crítica, 13/10/2026

Compara o corretor publicado até 12/10 (`0.1.0+corretor.8edda161bd4e`, veredictos em `docs/exemplo/antes-8edda161.json`) com o
corrigido a 13/10 (`0.1.0+corretor.be194b638f32`), sobre as respostas guardadas dos sete ensaios da tabela da página de exemplo: o
banco principal (27 casos) e o de consulta (30 e 31 casos), para os cinco modelos. Um caso **muda de estado** para um modelo quando
passa a ter, ou deixa de ter, uma falha crítica em alguma das amostras; cada mudança está numa linha, e li todas, sem amostrar. As
respostas citadas são as originais; `ATB-PIEL-006` e os outros casos aqui são lidos contra a referência do caso.

**Resultado: 9 mudanças de estado, todas de «passa a ter falha crítica»; nenhuma deixa de a ter.**

Classes: (a) 9, (b) 0, (c) 0.

Quem leu foi uma só pessoa, sem revisão. É triagem automática, sem validação clínica. Os ensaios mais antigos (agente e 16 de setembro)
não entram aqui.

Significado das classes: **a** mudança correta (a resposta dá a dose ou o intervalo de outro fármaco, de um ajuste, ou de um fármaco que a norma
citada não inclui); **b** falso falhanço ou falso passe; **c** ambígua.

| Modelo | Caso | Amostras | Critério | Frase da resposta | Classe |
|---|---|---|---|---|---|
| `local:gemma3:12b` | ATB-PIEL-006 | 1, 2, 3, 4, 5 | intervalo 12/12, ancorado à cefuroxima | «Dose Ciprofloxacino: 500 mg, de 12 em 12 horas.» (a1); nas outras, cotrimoxazol, «2x ao dia» e «12/12 horas», e nenhuma cefuroxima | a |
| `local:gemma3:12b` | ATB-DPOC-012 | 1 | intervalo 8/8 | «Dose: 300-450 mg de 8 em 8 horas.» (clindamicina) | a |
| `local:gemma3:12b` | AJU-APX-025 | 4 | dose 2,5 mg | «uma dose mais baixa (2,5 mg duas vezes ao dia) em doentes com fatores de risco»; a dose recomendada é 5 mg duas vezes ao dia | a |
| `local:phi4:14b` | ATB-PIEL-006 | 1, 2, 3, 4, 5 | intervalo 12/12, ancorado à cefuroxima | «Dose: 1 g via oral a cada 12 horas.» (cefalexina, a1); nas outras, co-trimoxazol «duas vezes ao dia» | a |
| `gemini:gemini-3.5-flash-lite` | ATB-PIEL-006 | 1, 2, 3, 4, 5 | intervalo 12/12, ancorado à cefuroxima | «Ciprofloxacina: 500 mg a 750 mg, de 12 em 12 horas, durante 7 dias.» (a2) | a |
| `gemini:gemini-3.5-flash-lite` | ATB-FAR-014 | 1, 2, 3, 4, 5 | dose 250 mg e intervalo 12/12, ancorados à cefuroxima | «Dose: 500 mg por via oral, a cada 12 horas (ou 250 mg a cada 6 horas).» (cefalexina, a2; a norma citada é omissa e o caso está ancorado à cefuroxima) | a |
| `gemini:gemma-4-31b-it` | ATB-PAC-001 | 1, 2, 3, 4, 5 | dose 500 mg, ancorada à amoxicilina | «ClCr 10-30 mL/min: 250 mg a 500 mg de 12 em 12 horas.» (a1); a dose principal é «1 g» | a |
| `gemini:gemma-4-31b-it` | ATB-PIEL-006 | 1, 2, 3, 4, 5 | intervalo 12/12, ancorado à cefuroxima | «Intervalo: de 12 em 12 horas» (Opção A, ciprofloxacina) | a |
| `gemini:gemma-4-26b-a4b-it` | ATB-PIEL-006 | 1, 2, 3, 4, 5 | intervalo 12/12, ancorado à cefuroxima | «Intervalo: De 12 em 12 horas.» (Opção A, ciprofloxacina) | a |

## O que mudou em relação à leitura de 12/10

A leitura de 12/10 (`docs/LEITURA_MUDANCAS_2026-10-12.md`) tinha 11 mudanças, 9 corretas e 2 falsos falhanços, os dois de ATB-FAR-004
(Gemini e Gemma 4 26B), o padrão (i) das limitações. A 13/10 tratou-se o padrão (i) (regra P4 do `docs/METODO.md`: numa secção cujo
cabeçalho nomeia um só fármaco, a dose e o intervalo seguintes são desse fármaco; um cabeçalho que nomeia vários não abre secção). Os dois
falsos falhanços desaparecem, e as 9 mudanças que ficam são as mesmas 9 corretas. A frase e o critério de cada amostra destas 9 são
idênticos nos dois corretores (comparados por código nas 37 amostras), por isso a classe (a) de 12/10 aplica-se sem nova leitura da
resposta. Nenhuma mudança nova de estado apareceu.

Efeito na tabela: Gemini 3.5 Flash Lite, banco principal, **13** (era 14 no corrigido de 12/10); Gemma 4 26B, banco principal, **12**
(era 13); os outros números não mudam. O McNemar exato entre os dois melhores passa a p = 0,25 (0 contra 3).

Fica por tratar o caso de ATB-DPOC-012 do Phi-4 (amostra 4): sob o cabeçalho «Amoxicilina/Ampicilina» o intervalo «a cada 8 horas» é da
amoxicilina, mas um cabeçalho com dois fármacos não abre secção, e o corretor continua a falhá-lo. É uma limitação escrita, não uma
regra a ajustar.
