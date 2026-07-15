# Technical report source

`main.tex` is an Overleaf-ready draft. It deliberately separates analytic evidence,
paired simulator validation, and the real StarWAM action-only experiment.

Compile locally with:

```bash
cd paper
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

Before submission, replace corporate `et al.` bibliography placeholders with complete
author metadata from the pinned records, add publication-quality figures, expand the
real-model candidate-future experiment, and obtain an independent reproduction. Generated
PDF and LaTeX auxiliary files are not committed.
