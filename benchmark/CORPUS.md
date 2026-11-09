# Corpus and licenses

The public corpus is four openly licensed textbooks, **1,882 PDF pages** in total. The PDFs are committed in
`corpus/pdfs/` so anyone who clones the repo searches exactly the same pages the benchmark labels point
at. `corpus/books.json` records each file's SHA-256, and the index builder refuses to run if a file does
not match, because a different edition would silently shift every page label.

Licenses were checked on each book's own copyright page on 2026-11-09.

## Public corpus

| ID | Book | Pages | License | Source |
| --- | --- | --- | --- | --- |
| `judson-abstract-algebra` | Thomas W. Judson (with Robert A. Beezer), *Abstract Algebra: Theory and Applications*, Annual Edition 2025 | 503 | GNU FDL 1.2 or later, no invariant sections | [judsonbooks.org](https://judsonbooks.org/aata-files/aata-20250801.pdf) |
| `levin-discrete-math` | Oscar Levin, *Discrete Mathematics: An Open Introduction*, 4th ed. | 549 | CC BY-NC-SA 4.0 | [discrete.openmathbooks.org](https://discrete.openmathbooks.org/pdfs/dmoi4.pdf) |
| `lebl-basic-analysis` | Jiří Lebl, *Basic Analysis I: Introduction to Real Analysis*, v6.3 | 312 | CC BY-SA 4.0 or CC BY-NC-SA 4.0 (author's choice of either) | [jirka.org/ra](https://www.jirka.org/ra/realanal.pdf) |
| `grinstead-snell-probability` | Charles M. Grinstead and J. Laurie Snell, *Introduction to Probability* (CHANCE version by Peter G. Doyle, 4 July 2006) | 518 | GNU FDL | [math.dartmouth.edu](https://math.dartmouth.edu/~prob/prob/prob.pdf) |

**What the licenses require of this project:**
- **Attribution.** Every search result shows the book title, and this file credits the authors.
- **ShareAlike (Levin, Lebl).** The derived index and the excerpts shown in the demo are shared under the same terms, never under a more restrictive license.
- **NonCommercial (Levin).** The demo must stay free and non-commercial.
- **GFDL (Judson, Grinstead & Snell).** Verbatim copies must keep the license, and each PDF includes it in an appendix.

I am not a lawyer. These are the plain-language terms of each license, not legal advice.

## Books from the original index

| File | Book | License found | Decision |
| --- | --- | --- | --- |
| `final.pdf` | Bruce E. Sagan, *Combinatorics: The Art of Counting* (AMS, GSM 210) | All rights reserved. Every page is stamped *"Prepublication copy… Not for print or electronic distribution. This file may not be posted electronically."* | **Removed.** Kept only in the git-ignored `private_corpus/`. It is still in the git history of the public repo (commit `04f00bb`); see the note below. |
| `book of proof.pdf` | Richard Hammack, *Book of Proof*, 3rd ed. (3.4) | CC BY-NC-ND 4.0 | **Removed.** "No derivatives": a search index plus excerpts may count as an adaptation. Kept privately. |
| `ntic2023.pdf` | Karl-Dieter Crisman, *Number Theory: In Context and Interactive* (2023) | Text CC BY-ND 4.0; some images non-commercial only | **Removed** for the same no-derivatives reason. Kept privately. |
| `mit18_100af20_basic_analysis.pdf` | Jiří Lebl, *Basic Analysis* (2021 MIT edition) | CC BY-SA 4.0 / CC BY-NC-SA 4.0 | **Replaced** by the author's current version (v6.3) from his site. |
| `prob.pdf` | Grinstead & Snell, *Introduction to Probability* | GNU FDL | **Kept.** Byte-identical to the file on the official site. |

Considered but not used: Robert A. Beezer, *A First Course in Linear Algebra* v3.50 (GFDL, 646 pages). It would
bring the corpus to 2,528 pages. I left it out to keep labeling manageable: every extra book is another
place where a relevant passage can go unlabeled, which unfairly penalises every system.

### Removing `final.pdf` from git history

Deleting a file in a new commit does not remove it from history. To remove it fully, rewrite history and
force-push. This cannot be undone and changes every commit hash, so the repo owner should do it deliberately:

```bash
pip install git-filter-repo
git filter-repo --invert-paths --path "Project Search/pdfs/final.pdf" \
  --path "Project Search/pdfs/book of proof.pdf" --path "Project Search/pdfs/ntic2023.pdf"
git remote add origin https://github.com/QuinnTravis/Math_Search_Engine   # filter-repo removes remotes
git push --force --all
```
