# BeanTech Profit Project Report

An Italian, single-column technical report using the LaTeX `article` class.
Authors: **Gabriele G. Pintus** and **Marta Lucas**, both affiliated with the
**University of Trieste**.

## Structure

- `main.tex`: entry point, title metadata and ordered section inputs.
- `beantechreport.sty`: visual style, shared packages and evidence-label commands.
- `references.bib`: bibliography, initially empty apart from usage comments.
- `sections/`: one file per section, numbered in reading order.
- `appendices/`: supplementary analyses and technical details.
- `figures/`: plots and diagrams, preferably vector PDFs.
- `tables/`: reusable LaTeX table fragments.

Add sections with `\input{sections/file-name}` rather than `\include`, so sections
continue naturally without forced page breaks. Keep the numeric filename prefix
aligned with the section's position in `main.tex`. The introduction currently
contains its heading and an outline; the following three sections contain text.

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

A4, 11 pt, Palatino-style text and mathematics, restrained blue headings/links,
compact title block, running header and page numbers. Change the appearance in
`beantechreport.sty`; edit authors, affiliation, date and version in `main.tex`.

Reading order and filenames (sections 5–9 are planned and their inputs remain commented):

1. Introduzione — `sections/01-introduction.tex`.
2. Modus operandi — `sections/02-modus-operandi.tex`.
3. Conoscenza di dominio — `sections/03-domain-knowledge.tex`.
4. Dati e trattamento — `sections/04-data-and-treatment.tex`.
5. Pulizia statistica e imputazione — `sections/05-statistical-cleaning-and-imputation.tex`.
6. Modelli ed esperimenti — `sections/06-modelling-framework-and-experiments.tex`.
7. Scheduling — `sections/07-scheduling.tex`.
8. Implementazione dell'applicazione web e deployment — `sections/08-web-app-implementation-and-deployment.tex`.
9. Conclusioni — `sections/09-conclusions.tex`.

Use `\cref{label}` for cross-references, `\textcite{key}` / `\parencite{key}` for
citations, and `booktabs` rules for tables without vertical borders. Put table
captions below tables and figures. Optional inline labels
`\domainknowledge`, `\datafinding`, and `\workingassumption` distinguish the
source/interpretation of a statement; they do not substitute for citations.


## Consistent example boxes

Use the `examplebox` environment for every example. Its layout is defined once
in `beantechreport.sty`: soft blue background, a subtle rounded frame, blue left
accent, title band, uniform padding and automatic numbering within each section.
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
