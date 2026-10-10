# Qualidade: requisitos, rastreabilidade e riscos

O Aferidor não é um dispositivo médico, mas mede sistemas que respondem a
médicos. Este documento aplica ao próprio instrumento duas práticas da ISO
13485 e da ISO 14971: a ligação de cada requisito ao teste que o verifica, e o
registo dos riscos do instrumento com a respetiva mitigação e o risco residual.

Os nomes de testes citados abaixo existem na bateria (`tests/`); um teste
(`tests/test_qualidade.py`) falha se algum deixar de existir, para este
documento não descrever verificações que já não se fazem.

## Requisitos e verificação

| ID | Requisito | Verificação |
|---|---|---|
| R01 | O modelo nunca recebe a resposta de referência nem os critérios. | `test_the_prompt_never_carries_the_reference_answer` |
| R02 | A resposta de referência de cada caso cumpre os seus próprios critérios. | `test_every_reference_passes_its_own_criteria`; `test_self_check_reports_an_alternative_whose_own_reference_fails` |
| R03 | Cada critério deteta uma resposta errada construída a partir da referência. | `test_every_criterion_catches_its_negative_control` |
| R04 | Todos os tipos de falha da taxonomia são medidos por algum caso; os críticos, por mais de um (com exceção declarada). | `test_every_failure_type_in_the_taxonomy_is_measured_by_some_case`; `test_every_critical_failure_is_measured_by_more_than_one_case` |
| R05 | Um critério que a própria pergunta cumpre é assinalado. | `test_a_required_term_the_question_already_contains_is_reported` |
| R06 | Um marcador de recusa não oculta uma prescrição proibida. | `test_a_refusal_followed_by_a_forbidden_drug_carries_the_critical_failure` |
| R07 | Negar uma contraindicação conta como prescrição; explicar uma exclusão não. | `test_denying_the_contraindication_is_a_prescription`; `test_a_later_mention_with_a_dose_or_advice_to_give_is_a_prescription` |
| R08 | Cada caso tem fonte identificada, com documento e local. | `test_every_case_cites_a_document_and_a_place_in_it`; `test_every_case_records_a_source_a_type_and_a_verification_date` |
| R09 | Uma retoma recusa condições diferentes (temperatura, limite de tokens, texto enviado). | `test_another_temperature_is_refused_before_anything_is_asked`; `test_another_token_limit_is_refused`; `test_a_changed_prompt_for_the_same_case_is_refused`; `test_an_answer_without_the_hash_of_the_text_sent_is_not_resumed_onto` |
| R10 | A mesma amostra duas vezes no ficheiro é recusada. | `test_a_file_with_the_same_sample_twice_is_refused` |
| R11 | Nenhuma contagem mistura modelos. | `test_mixing_two_models_in_one_tally_is_refused` |
| R12 | O resultado principal é o número de casos com falha crítica, com intervalo de confiança. | `test_the_headline_carries_its_interval`; `test_the_html_headline_carries_the_interval_too`; `test_the_critical_case_count_is_shown_per_model` |
| R13 | A comparação entre modelos é emparelhada por caso. | `test_values_match_the_exact_binomial`; `test_two_models_are_compared_with_a_paired_test` |
| R14 | O critério de aprovação é prévio, e o relatório assinala o contrário. | `test_a_protocol_dated_after_the_first_answer_is_not_a_prior_criterion` |
| R15 | Só é aprovado um modelo com todos os casos e amostras; o protocolo é lido antes do primeiro pedido. | `test_a_model_that_answered_part_of_the_bank_is_not_approved`; `test_a_missing_protocol_stops_before_asking_anything`; `test_a_protocol_with_limite_is_refused` |
| R16 | Casos defeituosos impedem a execução antes de qualquer pedido. | `test_broken_cases_stop_the_run_before_anything_is_asked` |
| R17 | O texto dos modelos é escapado; o relatório não tem script nem recursos externos. | `test_a_scripted_answer_is_escaped_not_executed`; `test_it_loads_nothing_from_the_network`; `test_the_only_addresses_in_attributes_are_the_project_link_and_the_preview_image`; `test_still_no_script_in_any_language` |
| R18 | O relatório diz que os veredictos são triagem, a validar por um especialista. | `test_the_first_screen_says_the_verdicts_are_triage_for_a_specialist` |
| R19 | A folha de revisão é cega e não executa fórmulas. | `test_the_sheet_is_blind_to_the_verdict_and_the_model`; `test_an_answer_that_looks_like_a_formula_is_written_as_text` |
| R20 | Cada ensaio registado corresponde ao seu manifesto SHA-256. | `test_every_trial_folder_is_intact` |
| R21 | Cada alteração ao corretor pode ser medida nos ensaios registados. | `test_a_verdict_that_flipped_is_named_with_its_sample`; `test_a_verdicts_file_of_other_answers_is_refused` |
| R22 | As chaves de API vêm apenas do ambiente. | `test_a_missing_key_names_the_variable`; `test_a_real_provider_without_a_key_raises_rather_than_asking` |
| R23 | A interface traduzida não altera os casos nem as respostas. | `test_every_interface_string_is_translated_into_every_language`; `test_the_answers_and_the_cases_stay_in_portuguese` |
| R24 | O texto tem contraste legível nos dois temas. | `test_every_text_colour_reads_on_the_page_and_on_cards_in_both_themes` |
| R25 | Um protocolo pode fixar a versão do corretor; o relatório assinala respostas ou correções feitas com outra. | `test_a_grader_changed_after_the_protocol_is_named`; `test_answers_asked_with_another_build_are_named` |
| R26 | O relatório são sete páginas só com CSS: o Início aparece sem endereço, a página do endereço (ou que contém o alvo) é a que se mostra, ocultar páginas só acontece onde `:has()` existe, e a impressão mostra todas. | `test_the_first_page_comes_first_and_is_shown_when_the_address_names_none`; `test_a_page_is_shown_when_it_is_the_target_or_holds_the_target`; `test_pages_are_hidden_only_where_has_is_understood`; `test_printing_shows_every_page`; `test_the_navigation_is_a_list_of_links_and_does_not_claim_a_current_page` |
| R27 | Em todas as páginas a barra fixa diz que os veredictos são triagem sem validação clínica e, enquanto houver fontes por confirmar, liga à página das fontes; a barra tem a altura que declara, em qualquer língua e largura; todas as línguas exceto o português dizem, no cimo de cada página e no rodapé, que a tradução é automática e não foi revista. | `test_the_bar_says_the_verdicts_are_triage_and_links_the_sources_page`; `test_the_bar_sits_outside_main_so_it_is_on_every_page`; `test_the_bar_has_the_height_it_declares_and_no_language_has_its_own`; `test_the_pages_never_wrap_so_the_bar_keeps_its_height`; `test_every_other_language_says_so_at_the_top_of_every_page_and_in_the_footer`; `test_the_bar_never_carries_the_translation_notice_in_any_language` |
| R28 | A primeira página tem um orçamento de palavras (120 sem protocolo, 115 com a revisão feita, 130 com protocolo), a moldura em português tem 60, e o aviso de tradução é uma só frase de no máximo 20 palavras. | `test_the_reference_version_fits_its_budget`; `test_the_version_with_the_review_done_fits_its_budget`; `test_the_versions_with_a_protocol_fit_theirs_with_and_without_the_warnings_pointer`; `test_the_frame_in_portuguese_fits_its_budget`; `test_the_translation_notice_is_one_short_sentence_in_every_language_that_shows_it` |
| R29 | A primeira página só diz que não há revisor enquanto `CLINICAL_REVIEW_DONE` for falso, sem afirmar mais nada sobre a revisão quando passa a verdadeiro; com protocolo nomeia as quatro condições que aplicou; o README e o caderno dizem o mesmo que a constante. | `test_the_review_sentence_is_true_while_there_is_no_reviewer`; `test_once_the_review_is_done_the_sentence_stops_saying_there_is_no_reviewer_and_claims_nothing_else`; `test_with_a_protocol_the_result_names_all_four_conditions_it_applied`; `test_the_readme_says_there_is_no_reviewer_exactly_while_the_constant_is_false`; `test_the_notebook_records_the_constant` |

## Registo de riscos do instrumento

Gravidade: **alta** quando o erro pode levar a considerar seguro um modelo que
não é; **média** quando distorce a comparação; **baixa** quando afeta a leitura
sem mudar conclusões.

| ID | Perigo | Efeito | Gravidade | Mitigação | Verificação | Risco residual |
|---|---|---|---|---|---|---|
| P01 | O corretor aprova uma resposta perigosa. | Modelo inseguro parece seguro. | Alta | Controlos negativos por critério; verificações críticas nos critérios comuns; recusa não oculta prescrição; revisão cega por um clínico. | R03, R06, R07, R19 | `contem` não lê negações; `valor_numerico` aceita qualquer número com a unidade; `nao_prescreve` é heurístico (limites em `METODO.md`). A revisão clínica ainda não foi feita. |
| P02 | O corretor reprova uma resposta certa. | Modelo penalizado; comparação distorcida. | Média | Referência passa nos próprios critérios; afinação documentada com razão e efeito medido; alternativas para esquemas defensáveis. | R02, R21 | Dois falsos positivos conservadores conhecidos no `nao_prescreve` (`METODO.md`); o ensaio congelado de 01/10 encontrou mais quatro casos (flexões não previstas, exclusões em título de lista ou como falta de evidência), descritos e não corrigidos durante o ensaio. |
| P03 | A referência está errada ou desatualizada. | O instrumento mede contra um erro. | Alta | Prioridade às normas da DGS e ao Infarmed; fonte com local em cada caso; aviso no relatório enquanto houver fontes por confirmar. | R08 | 24 fontes por confirmar por uma pessoa (`casos/VERIFICACAO.md`). |
| P04 | Critérios ou limites decididos depois de ver os resultados. | Validação enviesada a favor do modelo. | Alta | Protocolo commitado antes do ensaio; cada alteração a um critério com a razão no commit; o relatório assinala protocolos posteriores. | R14, R15, R21, R25 | O `nao_prescreve` foi afinado a 29/09 depois de ver respostas; está documentado no ensaio e no commit, com o efeito medido. Desde 01/10, um protocolo pode congelar o corretor. |
| P05 | Condições ou versões misturadas numa medição. | Resultado que não descreve nenhuma medição. | Média | A retoma recusa condições diferentes; cada resposta regista versão e hash do texto; amostras repetidas recusadas; manifesto por ensaio. | R09, R10, R20 | Incidente de 28/09 (dois processos no mesmo ficheiro), resolvido e documentado no ensaio. |
| P06 | A referência chega ao modelo. | O ensaio mede o prompt, não o modelo. | Alta | O texto enviado é construído só com a pergunta. | R01 | Nenhum conhecido. |
| P07 | Leitura errada do relatório. | Uma média esconde falhas críticas; triagem lida como validação. | Média | Casos com falha crítica primeiro; estados definidos no glossário; aviso de triagem no topo. | R12, R18 | Depende da leitura; o relatório não substitui a revisão clínica. |
| P08 | Conclusões tiradas de amostras pequenas. | Diferenças por acaso tomadas por reais. | Média | Intervalos de Wilson; teste de McNemar emparelhado; texto que diz quando a diferença pode ser acaso. | R12, R13 | 27 e 31 casos por banco: intervalos largos. |
| P09 | Texto malicioso de um modelo executado no relatório. | Código a correr no computador de quem lê. | Alta | Escape de todo o texto externo; relatório sem script nem recursos de rede. | R17 | Nenhum conhecido. |
| P10 | Fuga de chaves de API. | Uso indevido da conta. | Média | Chaves só no ambiente; nunca no repositório. | R22 | Depende de quem corre. |
| P11 | Uso clínico da ferramenta. | Decisão terapêutica tomada com base no instrumento. | Alta | Âmbito declarado no README, na apresentação e em cada relatório: mede, não aconselha; não é dispositivo médico. | R18 | Depende de quem usa. |
| P12 | Revisão clínica enviesada ou comprometida. | Concordância que não mede o corretor. | Média | Folha cega, chave separada, amostra reprodutível; fórmulas neutralizadas; aviso de amostra estratificada. | R19 | Sem revisor disponível à data; decisão registada. |
| P13 | Quem usa leitor de ecrã não sabe em que página do relatório está, ou lê uma tradução automática como se fosse revista. | Leitura errada do relatório sem que o relatório o mostre. | Baixa | Cada página tem o seu título; a barra de todas as páginas diz que os veredictos são triagem; cada página e o rodapé das línguas em `UNREVIEWED` dizem que a tradução é automática e não foi revista. | R26, R27 | Sem `aria-current` (sem script não se mantém); o inglês, o espanhol, o francês e o alemão continuam por rever, e só o português é a versão de referência; só visto em navegadores, sem leitor de ecrã. |
