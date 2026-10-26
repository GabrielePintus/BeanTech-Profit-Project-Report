# BeanTech Profit Project Report

An Italian, single-column technical report using the LaTeX `report` class.
Authors: **Gabriele G. Pintus** and **Marta Lucas**, both affiliated with the
**University of Trieste**.

## Structure

- `main.tex`: entry point, title metadata and ordered chapter inputs.
- `beantechreport.sty`: visual style, shared packages and evidence-label commands.
- `references.bib`: bibliography, initially empty apart from usage comments.
- `sections/`: one file per chapter, numbered in reading order.
- `appendices/`: supplementary analyses and technical details.
- `figures/`: plots and diagrams, preferably vector PDFs.
- `tables/`: reusable LaTeX table fragments.

Add chapters with `\input{sections/file-name}` rather than `\include`, so chapter files can be managed independently; each chapter starts on a new page. Keep the numeric filename prefix
aligned with the chapter's position in `main.tex`. The introduction currently
contains an outline and the methodological approach section; domain knowledge
and data descriptions follow as separate chapters.

## Overleaf

Set **Main document** to `main.tex` and **Compiler** to **pdfLaTeX**. Use a recent
TeX Live release. No custom fonts, shell escape or external assets are required.
Bibliography processing uses **BibLaTeX + Biber**; Overleaf/latexmk handles it
automatically after citations are added. Uncomment `\printbibliography` when
there are references to print.

## Local build

```sh
latexmk -pdf -outdir=build main.tex
```

The PDF is written to `build/main.pdf`. To clean local build products:

```sh
latexmk -C -outdir=build main.tex
```

## Style and conventions

A4, 11 pt, Palatino-style text and mathematics, vivid blue headings/links and teal accents,
dedicated title page and chapter headings, running header and page numbers. Change the appearance in
`beantechreport.sty`; edit authors, affiliation, date and version in `main.tex`.

Reading order and filenames (chapters 4–8 are planned and their inputs remain commented):

1. Introduzione, including Approccio metodologico — `sections/01-introduction.tex`.
2. Conoscenza di dominio — `sections/02-domain-knowledge.tex`.
3. Dati e trattamento — `sections/03-data-and-treatment.tex`.
4. Pulizia statistica e imputazione — `sections/04-statistical-cleaning-and-imputation.tex`.
5. Modelli ed esperimenti — `sections/05-modelling-framework-and-experiments.tex`.
6. Scheduling — `sections/06-scheduling.tex`.
7. Implementazione dell'applicazione web e deployment — `sections/07-web-app-implementation-and-deployment.tex`.
8. Conclusioni — `sections/08-conclusions.tex`.

Use `\cref{label}` for cross-references, `\textcite{key}` / `\parencite{key}` for
citations, and `booktabs` rules for tables without vertical borders. Put table
captions below tables and figures. Optional inline labels
`\domainknowledge`, `\datafinding`, and `\workingassumption` distinguish the
source/interpretation of a statement; they do not substitute for citations.


## Numbering

Examples, tables and figures use independent counters in `chapter.number` format.
Each counter restarts at 1 in each chapter: for example, Figure 2.1 and Example 2.1
can coexist. Plots use the figure counter. Numbering is automatic; never write
numbers manually in titles or cross-references.

## Consistent example boxes

Use the `examplebox` environment for every example. Its layout is defined once
in `beantechreport.sty`: soft yellow background, a subtle rounded frame, golden left
accent, title band, uniform padding and automatic numbering within each chapter.
Long examples can continue on the next page, with a repeated continuation title.

```tex
% Keep the verified dataset/source reference here, as a LaTeX comment.
\begin{examplebox}[ex:descriptive-identifier]{A descriptive title}
Example text, with equations or a table when useful.
\end{examplebox}
```

The optional argument is a reference identifier, not a set of style overrides.
Reference examples with `\cref{ex:descriptive-identifier}`. Do not introduce local
`\colorbox`/`minipage` wrappers or override colours and spacing in section files.
The current report uses the labels “Esempio” and “continua”; these can be changed
centrally via `\reportexamplename` and `\reportexamplecontinued` if the report's
language changes. Sources remain in comments; no selection rationale is added
to an example's body.

## VS Code

Install the recommended **LaTeX Workshop** extension and open this repository as
the workspace folder. Saving a LaTeX source file (`Ctrl+S`) runs `latexmk` and
writes the PDF and auxiliary files to `build/`. The recipe uses the report root
`main.tex`; LaTeX Workshop finds it through its section inputs.

A local TeX installation with Italian language support, `latexmk` and Biber is
required. Run **LaTeX Workshop: View LaTeX PDF file** to open the PDF in VS Code.

## Editorial scope

Use *macrofase* for a type of process step and *occorrenza di macrofase*
for an individual recorded instance within an ODP. In cycle reconstruction,
each node represents an occurrence; avoid using *operazione* as a synonym.

Describe the final methodology, modelling choices and results rather than the
chronology of development. References to data always mean the latest supplied
dataset; delivery dates and earlier versions need not be repeated in the prose.
Retain dated source paths and provenance in LaTeX comments for traceability. When giving
renaming examples, state both the original name or abbreviation and its normalized
form, so the transformation is explicit.

## Production graph

The full production graph is stored in `figures/documented-production-graph.dot`.
Each edge connects two visible phase nodes. Shared final trunks merge connections
that lead to the same phase. Regenerate the vector PDF after
editing the graph with:

```sh
python3 scripts/render_production_graph.py
```

Then compile the report normally. The generated figure PDF is versioned, so
Overleaf does not need Graphviz or shell escape.

## Numeric formatting

Use `\num{12345.67}` for quantities and statistics. The shared style displays
a thin space for thousands and a point for decimals: `12 345.67`.
Identifiers remain literal text and retain leading zeros.
Use `\cdot` for explicit multiplication in mathematical expressions.
Use numbered `equation` or `align` environments for displayed equations, with
stable labels for cross-references. Do not use `\[ ... \]` or `$$ ... $$`.
