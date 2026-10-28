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

Reading order and filenames (chapter 5 has been started; chapters 6–7 are planned and their inputs remain commented):

1. Introduzione, including Approccio metodologico — `sections/01-introduction.tex`.
2. Conoscenza di dominio — `sections/02-domain-knowledge.tex`.
3. Dati e trattamento — `sections/03-data-and-treatment.tex`.
4. Pulizia statistica e imputazione — `sections/04-statistical-cleaning-and-imputation.tex`.
5. Modellazione e generazione degli scenari produttivi — `sections/05-modelling-framework-and-experiments.tex`.
6. Scheduling — `sections/06-scheduling.tex`.
7. Conclusioni — `sections/07-conclusions.tex`.

Use `\cref{label}` for cross-references, `\textcite{key}` / `\parencite{key}` for
citations, and `booktabs` rules for tables without vertical borders. Put table
captions below tables and figures. Optional inline labels
`\domainknowledge`, `\datafinding`, and `\workingassumption` distinguish the
source/interpretation of a statement; they do not substitute for citations.


## Figure sizes

Ordinary figures are capped at 60% of the paper width (126 mm on A4), and never
exceed the local text width. Change `\reportfiguremaxwidth` in
`beantechreport.sty` to adjust this shared limit.
Use `\reportgraphic{filename.pdf}` for images, optionally adding a height limit
such as `\reportgraphic[height=0.50\textheight]{filename.pdf}`.
Wrap TikZ diagrams in `\reportfigurecontent{\input{figures/diagram}}`.
Smaller diagrams are not enlarged. Captions retain the text width.
Full-page diagrams, including the production graph and treatment pipeline,
are explicit exceptions and keep their dedicated sizing.

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

Use plain, natural Italian: direct sentences, familiar words and technical terms
explained when needed. Avoid formal-sounding phrasing that makes the text harder
to read. Precision should come from explicit definitions, not elaborate wording.

Define quantities, symbols, acronyms and technical methods before using them in
arguments, equations, tables or figures. Keep chapter introductions and general
principles free of implementation details that will only be explained later.

Use *macrofase* for a type of process step and *occorrenza di macrofase*
for an individual recorded instance within an ODP. In cycle reconstruction,
each node represents an occurrence; avoid using *operazione* as a synonym.
Refer explicitly to sales positions (*posizioni ODV*) and their associated
production orders (*ODP*). Avoid *famiglia*/*famiglie* as shorthand for these
entities, including in headings, tables and diagrams.
Use *scarto relativo alla quantità lavorata* for the ratio of scrap to processed
input quantity, rather than *frazione di scarto*.

Describe the final methodology, modelling choices and results rather than the
chronology of development. References to data always mean the latest supplied
dataset; delivery dates and earlier versions need not be repeated in the prose.
Retain dated source paths and provenance in LaTeX comments for traceability. When giving
renaming examples, state both the original name or abbreviation and its normalized
form, so the transformation is explicit.

## Production graph

Production-cycle diagrams mark their first phase with a short incoming arrow
from outside the graph. For TikZ, use `\productionstart{node-name}` (or pass
local link styling as its optional argument). The full-page Graphviz diagram
uses an invisible anchor for the same convention, not an additional phase.

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
Use `\bm{v}` for vectors and uppercase `\bm{M}` for matrices throughout the
report, including figures. Scalar components and indices remain unbolded.
Use `\cdot` for explicit multiplication in mathematical expressions.
Use numbered `equation` or `align` environments for displayed equations, with
stable labels for cross-references. Do not use `\[ ... \]` or `$$ ... $$`.

## Statistical mass figures

The plots in section 4.2 are vector PDFs generated from the aggregated evidence
in `figures/data/statistical-mass-*.csv`. Rebuild them with a Python environment
containing NumPy and Matplotlib:

```sh
python scripts/plot_statistical_mass.py
```

`figures/data/statistical-mass-comparison.csv` contains exact medians and 5th/25th/75th/95th
percentiles for the 101 treated ODP before/after and the 4759 untreated ODP.
These groups are defined by the union of yield and local-scrap flags.

`tables/data/statistical-mass-summary.json` records sample sizes, candidate counts,
model verification metrics, correction totals and SHA-256 hashes of the source
Parquets. Pre-imputation values were restored in memory from the correction
audits before computing the descriptive comparisons. The plotting script does
not train models or modify the source datasets.

## Positive-duration treatment figures

Section 4.3 uses saved positive-duration correction audits and the verification
results of the exact duration-correction models loaded by the pipeline. Refresh
its evidence from the adjacent code repository with:

```sh
python scripts/collect_duration_evidence.py --project-dir ../StrategicPlannerBeanTech
python scripts/plot_statistical_duration.py
```

The collector requires pandas and NumPy; the plotter also requires Matplotlib.
Neither command trains models or changes source data. Paired before/after values,
reference quantiles and model verification metrics are in `figures/data/`.
`tables/data/statistical-duration-summary.json` records source hashes, counts,
the real TRATT_LFC example and the overlap between applied temporal corrections
and the saved model-training ODV split. The LaTeX tables contain rounded values
from these evidence files and must be updated if the evidence changes.

## Zero-duration evidence (section 4.4)

Recreate the aggregate data and figure using the project Python environment:

```sh
../StrategicPlannerBeanTech/.venv/bin/python scripts/collect_zero_duration_evidence.py --project-dir ../StrategicPlannerBeanTech
MPLCONFIGDIR=/tmp/report-mpl ../StrategicPlannerBeanTech/.venv/bin/python scripts/plot_zero_duration.py
```

The collector regenerates the imputations from the frozen models and saved time
windows, and checks every value against the audit and final parquet. It does not
change the source data or refit models. Source hashes and counts are saved in
`tables/data/zero-duration-summary.json`. If the source data change, also update
the rounded values in `tables/zero-duration-results.tex` and the section text.

## Demand-feature generation evidence (section 5.2)

```sh
OMP_NUM_THREADS=2 MPLCONFIGDIR=/tmp/report-mpl ../StrategicPlannerBeanTech/.venv/bin/python scripts/collect_feature_generation_evidence.py --project-dir ../StrategicPlannerBeanTech
MPLCONFIGDIR=/tmp/report-mpl ../StrategicPlannerBeanTech/.venv/bin/python scripts/plot_feature_generation.py
```

The collector checks that the selected network weights match the evaluated
checkpoint, that the physical feature data match the evaluation cohort, and that
the training and validation ODV groups are disjoint. It also computes the independent
marginal baseline accuracy using the same hidden categorical targets and the most
frequent training category for each variable. It generates a reproducible
example from the selected frozen model, with three inputs from a validation row.
It does not retrain or modify project data. Counts, source hashes and the sampling
configuration are in `tables/data/feature-generation-summary.json`. If evidence
changes, update the rounded LaTeX table and prose too.

## ODP generation evidence (section 5.3)

```sh
OMP_NUM_THREADS=2 MPLCONFIGDIR=/tmp/report-mpl ../StrategicPlannerBeanTech/.venv/bin/python scripts/collect_odp_generation_evidence.py --project-dir ../StrategicPlannerBeanTech
MPLCONFIGDIR=/tmp/report-mpl ../StrategicPlannerBeanTech/.venv/bin/python scripts/plot_odp_generation.py
```

The collector checks the selected count and allocation components embedded in the
cascade, recomputes validation results from current Parquets and the frozen ODV
splits, and generates an allocation example from a real validation request.
It does not fit models or evaluate the held-out test set. Source hashes, exact
values and the example seed are in `tables/data/odp-generation-summary.json`.
The split table uses the mean for point predictions, matching deterministic
cascade generation. The plotted band is a prediction interval for the allocation
share, not a confidence interval for its mean. Update rounded LaTeX values when
the evidence changes.

## Cycle and material generation evidence (section 5.4)

```sh
OMP_NUM_THREADS=2 MPLCONFIGDIR=/tmp/report-mpl ../StrategicPlannerBeanTech/.venv/bin/python scripts/collect_graph_generation_evidence.py --project-dir ../StrategicPlannerBeanTech
MPLCONFIGDIR=/tmp/report-mpl ../StrategicPlannerBeanTech/.venv/bin/python scripts/plot_graph_generation.py
```

The collector uses the selected frozen graph model and catalog. It checks every
cached observed phase, input quantity and scrap value against the current Parquets,
and verifies cached transfers against current flow bounds or completion links.
Snapshot byte hashes differ from the frozen training metadata, so both provenance
and these physical consistency checks are recorded. Saved validation predictions
and normalized reference masses are reproduced before the reported comparison.

The reported evaluation omits `codice_motivo_ordine`, matching its absence in the
cascade, while supplying other observed upstream characteristics and observed
allocation shares. It is an isolated component evaluation. Structural accuracy
is unchanged by this omission; mass errors are recomputed. Ten sampled cycles per
validation ODP supply the phase-frequency comparison. The test set is not scored.
No model is fitted and no project data are changed. Exact metrics, sampling seed,
example values and source hashes are in `tables/data/graph-generation-summary.json`.
Reference masses are normalized to the same assigned final quantity as predictions.

## Duration generation evidence

Section 5.5 uses the duration component selected by `configs/production_cascade_selected.json`
in the code repository. `scripts/collect_duration_generation_evidence.py` checks that its
state equals the component embedded in the production cascade, recomputes predictions on
the current canonical parquet and reproduces all 1,314 eligible saved validation targets
and point predictions. It never refits models or evaluates test orders. Source hashes,
cohort counts and the example are saved in `tables/data/duration-generation-summary.json`.

Run with the code repository's Python environment and `--project-dir /path/to/code`.
The mean baseline consistently uses positive training durations without the two statistical
imputation flags. This changes the TRATT_LFC baseline slightly relative to its saved analysis.
The frozen imputers use a different ODV split, so this is a component diagnostic on treated
data, not an independent evaluation of the full preparation pipeline.

`scripts/plot_duration_generation.py` renders the conditional intervals and one seeded
duration draw for the same generated cycle used in Section 5.4. The plot has a logarithmic
minute axis and transparent background to preserve the shared example-box styling.

## Readiness deadline evidence

Section 5.6 describes the Gamma readiness-margin component embedded in the selected
production cascade. `scripts/collect_readiness_generation_evidence.py --project-dir /path/to/code`
verifies the current source hashes, reconstructs every observed margin and filtering
decision, and checks equality between the selected standalone and embedded models.
The Gamma fitting cohort contains 3,658 positive margins. Results are descriptive
on that cohort, not held-out Gamma validation metrics. The stale component-config
flag `integrated_in_cascade=false` is superseded by the verified runtime archive.

The collector writes the cohort, histogram probabilities and provenance to
`tables/data/readiness-generation-*`. `scripts/plot_readiness_generation.py` renders
the histogram using exact Gamma probabilities after upward rounding to calendar days.
The example reuses the two generated ODP of Example 5.2 and explicitly assumes a
scenario reference date; one seeded draw supplies their shared deadline.

## Complete cascade evaluation

Section 5.7 uses `scripts/collect_cascade_generation_evidence.py --project-dir /path/to/code`,
run with the code repository's Python environment. It reuses the graph collector's
validation of cached quantities and current flow bounds, checks every selected embedded
component, and evaluates 675 graph-validation positions in two modes: deterministic
generation from observed commercial specifications, and one sampled scenario per position
from requested quantity alone. Count decoding remains deterministic in both modes.
The direct mapper is extracted from its source package and its field names are converted
exactly as in the cascade build.

Reference material balances use the same normalization as Section 5.4. Duration references
come from the current parquet, not the older graph cache, and exclude entire positions
with statistically replaced, nonpositive or unsupported material durations. The duration
metric sums operation minutes; it is not elapsed production time or makespan.

Results, failures (none in the recorded run), component hashes, matching rules and three
complete sample outputs are retained in `tables/data/cascade-generation-*`. The 193-position
subset excludes ODV in the count/allocation training split; it is not a universal held-out
set for every component. The full procedure is a diagnostic integration evaluation, not
an independent final test. `scripts/plot_cascade_generation.py` compares phase presence
in observed ODP and scenarios generated from quantity only. No production model or
source data is changed by these scripts.
