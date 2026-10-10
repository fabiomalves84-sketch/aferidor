"""The stylesheet of the HTML report, kept apart from the code that builds the page.

Colour tokens are written once per theme and placed three times in the CSS:
the system preference, the header switch, and print (always light).
"""

from __future__ import annotations

LIGHT_TOKENS = """
  --page: #f3f7f7; --surface: #ffffff; --surface-2: #e3eeee; --highlight: #d6ecee;
  --ink: #0c1f24; --ink-2: #435a60; --muted: #506b70;
  --grid: #cfe0e1; --border: rgba(12,31,36,0.10);
  --accent: #0e6b78;
  --good: #0ca30c; --warning: #fab219; --serious: #ec835a; --critical: #d03b3b; --neutral: #a9a79f;
  --good-bg: rgba(12,163,12,0.12); --warning-bg: rgba(250,178,25,0.18);
  --critical-bg: rgba(208,59,59,0.12); --neutral-bg: rgba(137,135,129,0.14);
  --success-text: #006300; --critical-text: #b42a2a;
  --tooltip-shadow: rgba(0,0,0,0.18); --scroll-shadow: rgba(0,0,0,0.3);
"""
DARK_TOKENS = """
  --page: #0e191b; --surface: #152225; --surface-2: #1c2e32; --highlight: #1d3b41;
  --ink: #e9f2f2; --ink-2: #b7cacc; --muted: #93a9ac;
  --grid: #2a4045; --border: rgba(233,242,242,0.12);
  --accent: #5cc1d0;
  --good: #0ca30c; --warning: #fab219; --serious: #ec835a; --critical: #d03b3b; --neutral: #6c6a64;
  --good-bg: rgba(12,163,12,0.20); --warning-bg: rgba(250,178,25,0.16);
  --critical-bg: rgba(208,59,59,0.24); --neutral-bg: rgba(137,135,129,0.18);
  --success-text: #5fd35f; --critical-text: #ff8f86;
  --tooltip-shadow: rgba(0,0,0,0.55); --scroll-shadow: rgba(0,0,0,0.7);
"""
# Only CSS decides the theme: no radio is checked, so the page follows the
# system until the reader picks one; `:has()` lets the choice reach :root.
THEME_CSS = (
    ":root { color-scheme: light;" + LIGHT_TOKENS + "}\n"
    "@media (prefers-color-scheme: dark) {\n"
    "  :root:not(:has(#tema-claro:checked)) { color-scheme: dark;" + DARK_TOKENS + "}\n}\n"
    ":root:has(#tema-escuro:checked) { color-scheme: dark;" + DARK_TOKENS + "}\n"
    "@media print {\n"
    "  :root, :root:has(#tema-escuro:checked) { color-scheme: light;" + LIGHT_TOKENS + "}\n}\n"
)
PANEL_IDS = ("inicio", "sobre", "fontes", "resultados", "areas", "casos", "conclusoes", "metodo")
# Height of the fixed bar. It is declared, not measured: `.topo` has exactly this height and the
# page's scroll padding leaves exactly this much free, so a page or an anchor opens just below the
# bar in every language and at every width. What it holds has to fit: the pages never wrap (they
# scroll sideways), and the notice sentence takes one line from 600 px up, two below, and three
# in German under 24rem. Four values, one per width; checked in a browser at fourteen widths in the
# five languages (see METODO.md).
BAR_HEIGHT = (
    "html { --barra: 4.8rem; }\n"
    "@media (max-width: 62rem) { html { --barra: 7rem; } }\n"
    "@media (max-width: 46rem) { html { --barra: 8.6rem; } }\n"
    "@media (max-width: 24rem) { html { --barra: 9.4rem; } }\n"
)
CURRENT_PAGE = "".join(
    f'body:has(main #{ident}:target) nav.indice a[href="#{ident}"], '
    f'body:has(main #{ident} :target) nav.indice a[href="#{ident}"], '
    for ident in PANEL_IDS[1:]
) + 'body:not(:has(main :target)) nav.indice a[href="#inicio"], body:has(main #inicio:target) nav.indice a[href="#inicio"], body:has(main #inicio :target) nav.indice a[href="#inicio"]'
STYLE = THEME_CSS + BAR_HEIGHT + """
* { box-sizing: border-box; }
html { background: var(--page); scroll-behavior: smooth; scroll-padding-top: var(--barra); }
body {
  margin: 0 auto; max-width: 72rem; padding: 0 1rem 3rem;
  background: var(--page); color: var(--ink);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  line-height: 1.55; font-size: 16px;
}
h1, h2, h3, h4 { line-height: 1.25; margin: 0; }
h2 { font-size: 1.35rem; margin-bottom: 0.75rem; }
h3 { font-size: 1.05rem; }
p { margin: 0 0 0.75rem; }
code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.88em;
  background: var(--surface-2); padding: 0.1rem 0.3rem; border-radius: 4px; }
section { margin-top: 2.5rem; }
/* The fixed bar: brand and controls, the pages, and the notice every page carries. Its height
   is --barra, which the scroll padding uses so a page opens just below it. */
.topo { position: sticky; top: 0; z-index: 5; box-sizing: border-box; height: var(--barra); background: var(--page);
  border-bottom: 1px solid var(--grid); padding-top: 0.4rem; }
.topo-linha { display: flex; justify-content: space-between; align-items: center; gap: 0.5rem 1rem; }
.controlos { display: flex; gap: 0.5rem; align-items: flex-start; }
.linguas { position: relative; }
.linguas > summary { list-style: none; cursor: pointer; padding: 0.35rem 0.75rem; border-radius: 999px; font-size: 0.85rem;
  color: var(--ink-2); background: var(--surface-2); border: 1px solid var(--border); user-select: none; }
.linguas > summary::-webkit-details-marker { display: none; }
.linguas > summary:hover { color: var(--ink); }
.linguas > summary:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }
.linguas ul { position: absolute; right: 0; top: calc(100% + 6px); z-index: 30; list-style: none; margin: 0; padding: 0.35rem;
  background: var(--surface); border: 1px solid var(--border); border-radius: 10px; box-shadow: 0 4px 14px var(--tooltip-shadow); min-width: 9rem; }
.linguas a { display: block; padding: 0.35rem 0.6rem; border-radius: 6px; color: var(--ink); text-decoration: none; font-size: 0.9rem; }
.linguas a:hover, .linguas a:focus-visible { background: var(--surface-2); }
.linguas a[aria-current="page"] { font-weight: 650; }
.linguas a[aria-current="page"]::after { content: " ✓"; color: var(--success-text); }
.tema { display: inline-flex; padding: 3px; gap: 2px;
  background: var(--surface-2); border: 1px solid var(--border); border-radius: 999px; }
.tema input { position: absolute; opacity: 0; width: 1px; height: 1px; margin: 0; }
.tema label { cursor: pointer; padding: 0.3rem 0.8rem; border-radius: 999px; font-size: 0.85rem;
  color: var(--ink-2); user-select: none; }
.tema label:hover { color: var(--ink); }
.tema input:focus-visible + label { outline: 2px solid var(--accent); outline-offset: 1px; }
/* The highlighted half is the theme in force: the one picked, or the system's. */
.tema label[for="tema-claro"], :root:has(#tema-claro:checked) .tema label[for="tema-claro"],
:root:has(#tema-escuro:checked) .tema label[for="tema-escuro"] {
  background: var(--surface); color: var(--ink); box-shadow: 0 1px 2px var(--border); }
:root:has(#tema-escuro:checked) .tema label[for="tema-claro"] { background: none; color: var(--ink-2); box-shadow: none; }
@media (prefers-color-scheme: dark) {
  :root:not(:has(#tema-claro:checked)) .tema label[for="tema-escuro"] {
    background: var(--surface); color: var(--ink); box-shadow: 0 1px 2px var(--border); }
  :root:not(:has(#tema-claro:checked)) .tema label[for="tema-claro"] { background: none; color: var(--ink-2); box-shadow: none; }
}
.marca { font-size: 0.8rem; letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted); font-weight: 600; }
.titulo-inicio { padding: 0.5rem 0 0; margin-bottom: 1.25rem; }
.titulo-inicio h1 { font-size: 2rem; margin: 0 0 0.4rem; color: var(--accent); }
.subtitulo { color: var(--ink-2); margin: 0; }
.data { color: var(--muted); font-size: 0.9rem; margin: 0.35rem 0 0; }
nav.indice { min-width: 0; flex: 1 1 auto; }
/* The pages never wrap: they scroll sideways where they do not fit, with a shadow at the edge that
   still has more, so the bar keeps its declared height. Four backgrounds: two cover the edge when
   there is nothing more that way, two draw the shadow. */
nav.indice ul { list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: nowrap; gap: 0.25rem 1.1rem;
  overflow-x: auto; scrollbar-width: none;
  background:
    linear-gradient(to right, var(--page) 35%, transparent) left center / 1.6rem 100% no-repeat local,
    linear-gradient(to left, var(--page) 35%, transparent) right center / 1.6rem 100% no-repeat local,
    radial-gradient(farthest-side at 0 50%, var(--scroll-shadow), transparent) left center / 0.7rem 100% no-repeat scroll,
    radial-gradient(farthest-side at 100% 50%, var(--scroll-shadow), transparent) right center / 0.7rem 100% no-repeat scroll; }
nav.indice ul::-webkit-scrollbar { display: none; }
nav.indice a { display: inline-block; white-space: nowrap; padding: 0.15rem 0; color: var(--ink-2); text-decoration: none; font-size: 0.95rem;
  border-bottom: 2px solid transparent; }
nav.indice a:hover, nav.indice a:focus-visible { color: var(--accent); }
.faixa { margin: 0; padding: 0.25rem 0 0.4rem; font-size: 0.8rem; line-height: 1.35; color: var(--ink-2); }
.faixa a { color: var(--accent); }
@supports selector(:has(*)) {
  """ + CURRENT_PAGE + """ { color: var(--ink); font-weight: 650; border-bottom-color: var(--accent); }
}
/* One page at a time, by CSS alone: the page named in the address, or the first one when the
   address names none. Where :has() is not understood every page stays visible, in order. */
@supports selector(:has(*)) {
  main > .painel { display: none; }
  main:not(:has(:target)) > #inicio, main > .painel:target, main > .painel:has(:target) { display: block; }
}
.painel h3 + ul.conclusoes, ul.conclusoes { max-width: 46rem; margin: 0 0 1.25rem; padding-left: 1.25rem; }
ul.conclusoes li { margin: 0 0 0.45rem; }
.painel a { color: var(--accent); }
.painel h3:has(+ ul.conclusoes) { font-size: 1.1rem; margin: 1.1rem 0 0.5rem; }
.fecho { max-width: 46rem; margin: 1rem 0 0; padding-top: 0.9rem; border-top: 1px solid var(--grid); color: var(--ink-2); }
.inicio-texto, .inicio-lateral, .sobre { max-width: 38rem; }
/* From 80rem the numbers and the result sit beside the text; below, they stack under it. */
@media (min-width: 80rem) {
  .inicio-corpo { display: grid; grid-template-columns: 38rem 18rem; column-gap: 1.5rem; align-items: start; }
}
.saber-mais { margin: 0 0 1.1rem; font-weight: 600; }
.definicao { margin: 0.7rem 0 0; font-size: 0.92rem; color: var(--ink-2); }
.sobre .exemplo { margin: 1.1rem 0 1.25rem; padding: 0.9rem 1.1rem; background: var(--surface-2); border-radius: 10px; }
.sobre .exemplo h3 { margin-top: 0; }
.sobre .exemplo p:last-child, .sobre .exemplo details { margin-bottom: 0; }
.sobre pre { background: var(--surface-2); border-radius: 8px; padding: 0.75rem 0.9rem; overflow-x: auto; margin: 0 0 1rem; }
.sobre pre code { background: none; padding: 0; font-size: 0.85rem; }
.sobre h3 { margin: 1.4rem 0 0.5rem; font-size: 1.1rem; }
/* The link of the About page lands inside a closed block that opens on arrival; Firefox settles 4 px short. */
#como-se-verifica-o-corretor { scroll-margin-top: 0.5rem; }
.sobre ul.objetivos { margin: 0 0 0.9rem; padding-left: 1.25rem; color: var(--ink-2); }
.porque { font-size: 1.12rem; margin-bottom: 1.1rem; }
.objetivos-titulo { margin: 0 0 0.25rem; color: var(--accent); }
.inicio-corpo .factos { margin: 0 0 1.25rem; }
.resultado { margin: 0 0 0.6rem; padding: 1rem 1.25rem; font-size: 1.3rem; line-height: 1.4; background: var(--highlight);
  border: 1px solid var(--border); border-left: 4px solid var(--accent); border-radius: 12px; }
.resultado strong { font-weight: 650; }
.remate { margin: 0 0 0.6rem; font-size: 0.95rem; color: var(--ink-2); }
.inicio-corpo .triagem { margin: 0.9rem 0 0; font-size: 0.95rem; color: var(--ink-2); }
footer.rodape .data, footer.rodape .marca { margin: 0.2rem 0 0; font-size: 0.82rem; color: var(--muted); }
footer.rodape .marca { text-transform: uppercase; letter-spacing: 0.08em; font-weight: 600; }
.traducao { margin: 0 0 0.9rem; padding: 0.4rem 0.7rem; font-size: 0.82rem; color: var(--ink-2); background: var(--warning-bg);
  border-left: 3px solid var(--warning); border-radius: 6px; }
footer.rodape .traducao { margin-top: 0.9rem; }
.painel { margin-top: 0; padding-top: 1rem; }
.painel > h2 { font-size: 1.6rem; margin: 0 0 1rem; }
.painel > section:first-of-type, .painel > .cartoes:first-child { margin-top: 0; }
.painel section > h3 { font-size: 1.2rem; margin-bottom: 0.6rem; }
.triagem { color: var(--ink-2); font-size: 0.9rem; margin-top: -0.25rem; }
.factos { list-style: none; padding: 0; margin: 0.5rem 0 0; display: flex; flex-wrap: wrap; gap: 0.5rem; }
.factos li { background: var(--highlight); border-radius: 999px; padding: 0.2rem 0.75rem; font-size: 0.88rem; color: var(--ink-2); }
.como-ler { margin: 0; padding-left: 1.3rem; color: var(--ink-2); font-size: 0.95rem; }
.como-ler li { margin-bottom: 0.6rem; }
.como-ler strong { color: var(--ink); }
.aviso { display: flex; gap: 0.75rem; align-items: flex-start; margin: 0.75rem 0;
  background: var(--warning-bg); border: 1px solid var(--border); border-radius: 10px; padding: 0.8rem 1rem; }
.aviso-icone { flex: none; width: 1.5rem; height: 1.5rem; border-radius: 50%; background: var(--warning);
  color: #0b0b0b; font-weight: 700; display: inline-flex; align-items: center; justify-content: center; }
.seccao-intro { color: var(--ink-2); max-width: 48rem; }
.cartoes { display: grid; grid-template-columns: repeat(auto-fit, minmax(20rem, 1fr)); gap: 1rem; }
.cartao-modelo { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 1.25rem; }
.cartao-modelo header { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: flex-start; gap: 0.5rem; min-height: 3.5rem; }
.modelo-nome { font-size: 1.15rem; font-weight: 650; display: block; }
.modelo-desc { display: block; color: var(--ink-2); font-size: 0.85rem; margin-top: 0.1rem; }
.modelo-id { display: inline-block; margin-top: 0.3rem; font-size: 0.72rem; color: var(--muted); background: none; padding: 0; }
.selo { font-size: 0.8rem; font-weight: 600; border-radius: 999px; padding: 0.15rem 0.6rem; }
.selo.aprovado { background: var(--good-bg); color: var(--success-text); }
.selo.reprovado { background: var(--critical-bg); color: var(--ink); }
.numero-principal { display: flex; align-items: baseline; gap: 0.6rem; margin: 0.9rem 0 1rem; flex-wrap: wrap; }
.destaque { font-size: 3.2rem; font-weight: 650; line-height: 1; font-variant-numeric: lining-nums; }
.numero-principal .legenda { color: var(--ink-2); font-size: 0.92rem; max-width: 16rem; }
.barra { display: flex; gap: 2px; height: 16px; border-radius: 4px; overflow: hidden; }
.seg { display: block; height: 100%; flex-basis: 0; }
.seg.ok, .swatch.ok { background: var(--good); }
.seg.instavel, .swatch.instavel { background: var(--warning); }
.seg.erro, .swatch.erro { background: var(--critical); }
.swatch.sem-resposta { background: var(--neutral); }
.legenda-estados, .legenda-riscos { list-style: none; padding: 0; margin: 0.6rem 0 0.75rem; display: flex; flex-wrap: wrap; gap: 0.3rem 1rem;
  font-size: 0.85rem; color: var(--ink-2); }
.legenda-estados strong { color: var(--ink); }
.swatch { display: inline-block; width: 0.7rem; height: 0.7rem; border-radius: 3px; margin-right: 0.35rem; vertical-align: -0.05rem; }
.pontos { display: inline-flex; gap: 2px; margin-left: 0.4rem; font-size: 0.72rem; letter-spacing: 0; vertical-align: 0.05rem; }
.pt.certa { color: var(--success-text); }
.pt { display: inline-block; width: 0.85em; text-align: center; }
.pt.errada { color: var(--critical-text); font-weight: 800; font-size: 1.2em; line-height: 1; }
.pt.falta { color: var(--muted); }
.como-se-conta { background: var(--surface-2); border-radius: 10px; padding: 0.9rem 1.1rem; margin: 1.25rem 0 0.5rem; }
.como-se-conta h3 { margin: 0 0 0.4rem; font-size: 1rem; }
.como-se-conta p { margin: 0.4rem 0; }
.como-se-conta ul { list-style: none; padding: 0; margin: 0.5rem 0; }
.como-se-conta li { margin: 0.25rem 0; }
.como-se-conta li .pontos { display: inline-flex; min-width: 5.5rem; margin: 0 0.6rem 0 0; }
.protocolo .cartao { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 1.25rem; }
.protocolo ul { padding-left: 1.2rem; margin-bottom: 0; }
.comparacao { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 1.25rem; margin-bottom: 1rem; }
.comp-frase { font-size: 1.05rem; }
.comp-lista, .comp-eixo { list-style: none; margin: 0; padding: 0; }
.comp-lista li, .comp-eixo { display: grid; grid-template-columns: 9rem 1fr 8.5rem; align-items: center; gap: 0.75rem; padding: 0.45rem 0; }
.comp-nome { font-weight: 600; }
.comp-pista { position: relative; height: 22px; border-left: 1px solid var(--grid); border-right: 1px solid var(--grid);
  background: linear-gradient(var(--grid), var(--grid)) center / 100% 1px no-repeat; }
.comp-ic { position: absolute; top: 9px; height: 4px; border-radius: 2px; background: var(--critical); opacity: 0.45; }
.comp-ponto { position: absolute; top: 3px; width: 16px; height: 16px; margin-left: -8px; border-radius: 50%;
  background: var(--critical); box-shadow: 0 0 0 2px var(--surface); }
.comp-valor { font-variant-numeric: tabular-nums; font-size: 0.9rem; color: var(--ink-2); }
.comp-eixo { padding-top: 0; }
.comp-ticks { position: relative; height: 1.1rem; font-size: 0.72rem; color: var(--muted); }
.comp-ticks span { position: absolute; transform: translateX(-50%); }
.comp-ticks span:first-child { transform: none; } .comp-ticks span:last-child { transform: translateX(-100%); }
.comp-nota { font-size: 0.82rem; color: var(--muted); margin: 0.4rem 0 0; }
.erros { display: grid; grid-template-columns: repeat(auto-fit, minmax(30rem, 1fr)); gap: 1rem; }
.erro-cartao { background: var(--surface); border: 1px solid var(--border); border-left: 4px solid var(--critical); border-radius: 12px; padding: 1.1rem 1.25rem; }
.erro-topo { display: flex; justify-content: space-between; gap: 0.5rem; margin-bottom: 0.3rem; }
.erro-modelo { font-size: 0.85rem; color: var(--ink-2); font-weight: 600; }
.erro-pergunta { font-weight: 600; }
.erro-par { display: grid; grid-template-columns: 1fr 1fr; gap: 0.9rem; }
.erro-rotulo { font-size: 0.74rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted); margin: 0 0 0.25rem; font-weight: 600; }
.erro-par blockquote { max-height: 12rem; font-size: 0.84rem; }
.erro-ref { background: var(--good-bg); border-radius: 6px; padding: 0.6rem 0.8rem; font-size: 0.88rem; margin-bottom: 0.4rem; }
.erro-chips { margin: 0.6rem 0 0.3rem; }
.erro-cartao a, .rodape a { color: var(--accent); }
.repo { font-size: 0.92rem; margin: 0 0 0.75rem; }
.veredicto { font-size: 1.05rem; max-width: 48rem; margin: 0 0 0.5rem; }
table.areas { border-collapse: collapse; width: 100%; font-size: 0.92rem; }
table.areas th, table.areas td { border-bottom: 1px solid var(--grid); padding: 0.5rem 0.75rem; text-align: left; }
table.areas thead th { font-size: 0.85rem; }
table.areas tbody th { font-weight: 500; }
.area-cel { background: rgba(208, 59, 59, var(--a)); font-variant-numeric: tabular-nums; min-width: 7rem; }
.area-cel.vazio { background: var(--neutral-bg); color: var(--ink-2); }
.falhas-grelha { display: grid; grid-template-columns: repeat(auto-fit, minmax(22rem, 1fr)); gap: 1rem; }
.falhas-modelo { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 1.25rem; }
.falhas-modelo .modelo { margin-bottom: 0.9rem; }
.barras-falhas { list-style: none; margin: 0; padding: 0; }
.barras-falhas li { display: grid; grid-template-columns: 14rem 1fr 2.5rem; align-items: center; gap: 0.6rem; padding: 0.3rem 0; }
.rotulo { font-size: 0.88rem; line-height: 1.25; }
.rotulo .sub { display: block; color: var(--muted); font-size: 0.74rem; }
.pista { height: 14px; border-left: 1px solid var(--grid); display: flex; }
.fill { display: block; height: 14px; border-radius: 0 4px 4px 0; min-width: 3px; }
.valor { font-variant-numeric: tabular-nums; font-weight: 600; font-size: 0.9rem; text-align: right; }
.r-critico { --c: var(--critical); } .r-alto { --c: var(--serious); } .r-medio { --c: var(--warning); } .r-baixo { --c: var(--neutral); }
.fill, .swatch.r-critico, .swatch.r-alto, .swatch.r-medio, .swatch.r-baixo { background: var(--c); }
.grade-wrap { overflow-x: auto; background: var(--surface); border: 1px solid var(--border); border-radius: 12px; }
table.grade { border-collapse: collapse; width: 100%; font-size: 0.9rem; }
table.grade th, table.grade td { border-bottom: 1px solid var(--grid); padding: 0.55rem 0.75rem; text-align: left; vertical-align: top; }
table.grade thead th { font-size: 0.82rem; color: var(--ink); background: var(--surface); min-width: 12rem; }
table.grade tbody th { font-weight: 400; min-width: 16rem; max-width: 30rem; }
.caso-id { display: block; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.82rem; font-weight: 600; }
.caso-pergunta { display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; color: var(--ink-2); font-size: 0.82rem; line-height: 1.35; margin-top: 0.15rem; }
tr.categoria td { background: var(--surface-2); font-weight: 600; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--ink-2); }
td.cel { white-space: nowrap; }
td.cel.ok { background: var(--good-bg); }
td.cel.erro { background: var(--critical-bg); }
td.cel.instavel { background: var(--warning-bg); }
td.cel.sem-resposta { background: var(--neutral-bg); color: var(--ink-2); }
.cel-falha { font-size: 0.8rem; color: var(--ink-2); }
.ic { font-weight: 700; }
td.cel.ok .ic { color: var(--success-text); }
td.cel.erro .ic { color: var(--critical-text); }
.detalhe details { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; margin: 0.5rem 0; }
.detalhe summary { cursor: pointer; padding: 0.75rem 1rem; display: grid; grid-template-columns: 9rem 1fr auto; gap: 0.75rem; align-items: center; }
.detalhe summary:hover { background: var(--surface-2); border-radius: 10px; }
.resumo-pergunta { color: var(--ink-2); font-size: 0.9rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.minis { display: inline-flex; gap: 0.25rem; }
.mini { display: inline-flex; align-items: center; justify-content: center; width: 1.35rem; height: 1.35rem; border-radius: 50%;
  font-size: 0.75rem; font-weight: 700; color: #0b0b0b; flex: none; }
.mini.ok { background: var(--good); } .mini.instavel { background: var(--warning); } .mini.erro { background: var(--critical); color: #ffffff; }
.detalhe-corpo { padding: 0.9rem 1rem 1rem; border-top: 1px solid var(--grid); scroll-margin-top: 3.5rem; }
.referencia { background: var(--surface-2); border-radius: 8px; padding: 0.75rem 0.9rem; margin: 0.5rem 0 1rem; }
.referencia p { margin: 0 0 0.35rem; } .fonte { color: var(--ink-2); font-size: 0.88rem; }
.detalhe h4 { margin: 1.1rem 0 0.4rem; font-size: 0.98rem; display: flex; align-items: center; gap: 0.4rem; flex-wrap: wrap; }
.h4-sub { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; font-weight: 400; color: var(--muted); font-size: 0.85rem; }
.amostra { border-left: 3px solid var(--grid); padding-left: 0.9rem; margin: 0.75rem 0; }
.amostra-numero, .passou { font-size: 0.85rem; color: var(--ink-2); margin: 0 0 0.3rem; font-weight: 600; }
.passou { color: var(--success-text); }
blockquote { margin: 0 0 0.5rem; padding: 0.6rem 0.8rem; background: var(--surface-2); border-radius: 6px;
  white-space: pre-wrap; font-size: 0.88rem; max-height: 22rem; overflow: auto; }
.criterios-falhados { list-style: none; padding: 0; margin: 0; }
.criterios-falhados li { margin: 0.35rem 0; }
.chip { display: inline-flex; align-items: center; gap: 0.35rem; font-size: 0.8rem; font-weight: 600;
  background: var(--surface-2); border-radius: 999px; padding: 0.1rem 0.6rem; margin-right: 0.4rem; }
.chip .dot { width: 0.55rem; height: 0.55rem; border-radius: 50%; background: var(--c); }
.chip-risco { font-weight: 400; color: var(--muted); }
.evidencia { font-size: 0.84rem; color: var(--ink-2); }
.lingua ul { padding-left: 1.2rem; }
.condicoes dl { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 1rem 1.25rem; margin: 0; }
.condicoes dt { font-weight: 600; font-size: 0.9rem; word-break: break-word; }
.condicoes dd { margin: 0.1rem 0 0.8rem; color: var(--ink-2); font-size: 0.9rem; }
abbr.termo { text-decoration: none; border-bottom: 1px dotted var(--muted); cursor: help; position: relative; }
abbr.termo:focus { outline: 2px solid var(--accent); outline-offset: 2px; border-radius: 2px; }
abbr.termo:hover::after, abbr.termo:focus::after {
  content: attr(data-def); position: absolute; left: 0; top: calc(100% + 6px); z-index: 20;
  width: max-content; max-width: min(20rem, 80vw); padding: 0.5rem 0.65rem; border-radius: 6px;
  background: var(--ink); color: var(--page); font-size: 0.8rem; line-height: 1.4; font-weight: 400;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  text-transform: none; letter-spacing: normal; white-space: normal; text-align: left;
  box-shadow: 0 4px 14px var(--tooltip-shadow); pointer-events: none; }
abbr.termo.lado:hover::after, abbr.termo.lado:focus::after { left: calc(100% + 8px); top: -0.3rem; }
.vh { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
details.recolhe { margin-top: 1rem; background: var(--surface); border: 1px solid var(--border); border-radius: 12px; }
details.recolhe > summary { cursor: pointer; padding: 0.8rem 1.25rem; font-weight: 650; }
details.recolhe[open] > summary { border-bottom: 1px solid var(--grid); }
details.recolhe > :not(summary) { margin-left: 1.25rem; margin-right: 1.25rem; }
details.recolhe > :last-child { margin-bottom: 1rem; }
details.mais, details.tecnico { margin-top: 2.5rem; }
details.recolhe h3 { margin-top: 1.25rem; }
.card-linha { font-size: 0.9rem; color: var(--ink-2); margin: 0.75rem 0 0; }
.card-linha strong { color: var(--ink); }
.lista-certos { list-style: none; padding: 0; margin: 0.75rem 1.25rem 1rem; font-size: 0.88rem; color: var(--ink-2); }
.lista-certos li { margin: 0.3rem 0; }
.glossario dl { margin: 0; display: grid; grid-template-columns: repeat(auto-fit, minmax(18rem, 1fr)); gap: 0.4rem 1.5rem; }
.glossario dt { font-weight: 650; font-size: 0.9rem; }
.glossario dd { margin: 0 0 0.5rem; color: var(--ink-2); font-size: 0.86rem; }
footer.rodape { margin-top: 3rem; padding-top: 1.25rem; border-top: 1px solid var(--grid); color: var(--ink-2); font-size: 0.88rem; }
footer.rodape h2 { font-size: 1rem; color: var(--ink); }
@media (max-width: 62rem) {
  .topo-linha { flex-wrap: wrap; justify-content: flex-start; }
  .controlos { order: -1; }
  nav.indice { flex: 1 1 100%; }
}
@media (max-width: 46rem) {
  nav.indice ul { gap: 0.25rem 0.9rem; }
  .detalhe summary { grid-template-columns: 1fr auto; }
  .resumo-pergunta { display: none; }
  .barras-falhas li { grid-template-columns: 8.5rem 1fr 2rem; }
  .destaque { font-size: 2.6rem; }
  .titulo-inicio h1 { font-size: 1.6rem; }
  .erros { grid-template-columns: 1fr; }
  .erro-par { grid-template-columns: 1fr; }
  .comp-lista li, .comp-eixo { grid-template-columns: 6rem 1fr 6.5rem; }
}
@media print {
  .topo { position: static; }
  .controlos { display: none; }
  main > .painel { display: block !important; break-before: page; }
  main > .painel:first-child { break-before: auto; }
  details { break-inside: avoid; }
}
"""


__all__ = ["LIGHT_TOKENS", "DARK_TOKENS", "THEME_CSS", "STYLE"]
