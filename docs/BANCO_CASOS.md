# Banco de casos clínicos, versão 1.4

## Descrição

Trinta e uma perguntas clínicas em português europeu, do tipo colocado por um médico de família a um assistente: consulta de adulto (13, incluindo um caso de encaminhamento urgente, ADU-AVC-01, acrescentado a 30/09/2026), consulta de criança (10) e cessação tabágica (8). Cada caso inclui uma resposta de referência, os elementos obrigatórios de uma resposta correta, os erros que a tornam perigosa, um nível de risco e a fonte, com versão, secção e data de verificação.

O ficheiro é `casos/consulta.json`. Os critérios de correção estão definidos em cada caso.

## Critérios de seleção

Os casos privilegiam os erros de maior custo clínico, e não os mais fáceis de medir:

- **Alternativas erradas plausíveis.** Substituir um IECA por um ARA II na gravidez; propor um anticoagulante direto a um doente com prótese valvular mecânica; indicar ibuprofeno como alternativa à aspirina numa criança com varicela.
- **Doses por peso em pediatria**, em que a dose de adulto constitui o erro mais grave.
- **Contexto português**, em que a resposta correta difere da de outros países: o SCORE2 calibrado para região de risco moderado, a posição da DGS sobre o cigarro eletrónico (mais restritiva do que a do NICE) e o PNV.

## Fontes

28 casos têm fonte primária (RCM, norma da DGS, diretriz da ESC, ADA ou NICE, comunicado da EMA, ensaio original, portal do SNS) e 3 têm fonte secundária (PED-04, PED-06 e PED-10). Todos têm data de verificação.

## Limitações

- **Sem revisão clínica independente.** Os casos foram construídos a partir de fontes públicas por um não clínico. Nesta revisão foram corrigidos dois casos já marcados como revistos: uma imprecisão sobre o trimestre da gravidez (ADU-HTA-02) e uma omissão sobre o ibuprofeno na varicela (PED-04). A 27/09/2026, parte das fontes (DGS e Infarmed) foi declarada confirmada, com uma médica presente, sem registo caso a caso; as fontes da ESC, ADA, NICE e EMA foram lidas por ferramenta no documento original e coincidem, mas aguardam confirmação por uma pessoa. Ver `casos/VERIFICACAO.md`.
- **Ensaios reais recentes.** O banco correu pela primeira vez a 29 e 30/09/2026 (Gemini 3.5 Flash Lite e Gemma 4 31B, ver `ensaios/`), com os 30 casos da altura. Esses ensaios mostraram reprovações indevidas do corretor, corrigidas com a razão escrita; o caso ADU-AVC-01 ainda não foi corrido contra nenhum modelo.
- **Correção textual.** Os critérios procuram palavras e números e não avaliam raciocínio. A opção é deliberada (um corretor baseado noutro modelo introduziria um segundo sistema em avaliação), mas exige critérios bem redigidos.
- **Trinta e um casos identificam padrões, não taxas.** Permitem mostrar onde um modelo falha, mas não quantificar a frequência com precisão.
- **Fontes com data.** A norma da otite é de 2014, o programa-tipo de cessação tabágica de 2007, e o PNV foi alterado em outubro de 2025.
