# Banco de casos clínicos, versão 1.4

## O que é

Trinta perguntas clínicas em português europeu, do tipo que um médico de família faz a um assistente: consulta de adulto (12), consulta de criança (10) e cessação tabágica (8). Cada caso tem uma resposta de referência, os elementos que uma resposta certa tem de conter, os erros que a tornam perigosa, um nível de risco e a fonte de onde tudo isto vem, com versão, secção e data de verificação.

O ficheiro é `casos/consulta.json`. Os critérios que o Aferidor usa para corrigir estão dentro de cada caso.

## Porque é que estes casos

Foram escolhidos para apanhar os erros que custam caro, não os que são fáceis de medir:

- **Armadilhas com alternativa errada plausível.** Trocar um IECA por um ARA II na gravidez; propor um anticoagulante direto a quem tem prótese valvular mecânica; dar ibuprofeno como alternativa à aspirina numa criança com varicela.
- **Doses por peso em pediatria**, onde um modelo que responde com a dose de adulto comete o erro mais grave que existe.
- **Contexto português**, onde a resposta certa em Portugal difere da de outros países: o SCORE2 calibrado para região de risco moderado, a posição da DGS sobre cigarro eletrónico (mais restritiva do que a NICE), o PNV.

## Fontes

27 casos têm fonte primária (RCM, norma da DGS, guideline da ESC, ADA ou NICE, comunicado da EMA, ensaio original) e 3 têm fonte secundária (PED-04, PED-06 e PED-10). Todos têm data de verificação.

## Limites, ditos às claras

- **Não houve revisão clínica independente.** Os casos foram construídos a partir de fontes públicas por quem não é clínico. Nesta revisão corrigiram-se dois casos que já estavam marcados como revistos: uma imprecisão sobre o trimestre da gravidez (ADU-HTA-02) e uma omissão sobre o ibuprofeno na varicela (PED-04). É o passo que mais falta. A 27/09/2026 as fontes foram declaradas confirmadas, com uma médica presente, mas em bloco e sem registo caso a caso (PED-08 à parte, confirmado na norma da DGS); ver `casos/VERIFICACAO.md`.
- **Ainda não foi corrido contra um modelo real.** Os critérios foram testados contra as próprias respostas de referência (30/30) e contra respostas erradas escritas de propósito, mas não contra a forma como um modelo real escreve. Conta-se com falsos erros no primeiro ensaio.
- **A correção é textual.** Um critério procura palavras e números; não percebe raciocínio. É uma escolha deliberada (um corretor que é outro modelo introduz um segundo sistema sob teste), mas tem o custo de exigir critérios bem escritos.
- **Trinta casos medem padrões, não taxas.** Chegam para mostrar onde um modelo falha; não chegam para dizer com precisão quanto falha.
- **Algumas fontes envelhecem.** A norma da otite é de 2014, o programa-tipo de cessação tabágica de 2007, e o PNV mudou em outubro de 2025.
