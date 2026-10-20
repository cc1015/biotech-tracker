# Biological silos

A "silo" is a scientific area that companies keep coming out of. Each one has its own enabling discovery, its own pool of founders and labs, and its own regulatory and financing path. New companies tend to appear in waves right after an enabling discovery shows a path to the clinic or to a product.

Use the `id` in the `silo` column of the data files.

## Therapeutic modalities

| id | Silo | Enabling discovery / trigger | Typical origin | Notes |
|---|---|---|---|---|
| `small-molecule` | Small molecules | Structural biology, chemistry automation, AI | founder-led, pharma-spinout | Oldest silo; AI is reviving it |
| `antibody` | Antibodies & biologics | Hybridoma → phage display → humanized/human mAbs | academic, pharma-spinout | Bispecifics and multispecifics are a sub-wave |
| `adc` | Antibody–drug conjugates | Linker/payload chemistry | pharma-spinout, China licensing | Heavy in-licensing from Chinese biotechs |
| `radiopharma` | Radiopharmaceuticals | Targeted radioligands (e.g. PSMA) | founder-led | M&A-driven wave |
| `cell-therapy` | Cell therapy (CAR-T, NK, TIL, in vivo CAR) | CAR-T approvals | academic-spinout | Moving into autoimmune disease; in vivo CAR is the newest sub-wave |
| `gene-therapy` | Gene therapy (AAV, lentiviral) | AAV vectors | academic-spinout | Capsid engineering is a separate sub-silo |
| `gene-editing` | Gene editing (CRISPR, base, prime, epigenetic) | CRISPR-Cas9 (2012), base editing (2016), prime editing (2019) | academic-spinout (Broad, UC Berkeley) | A clear case of one lab → many companies |
| `rna` | RNA (mRNA, siRNA, ASO, RNA editing) | mRNA/LNP delivery, GalNAc conjugates | academic-spinout, studio-built | Delivery is the bottleneck, so delivery startups appear |
| `protein-degradation` | Targeted protein degradation | PROTACs, molecular glues | academic-spinout (Yale) | |
| `microbiome` | Microbiome therapeutics | Sequencing-based microbiome science | studio-built | Wave cooled after setbacks |

## Platforms and enabling technologies

| id | Silo | Trigger | Notes |
|---|---|---|---|
| `ai-discovery` | AI drug discovery & protein design | AlphaFold 2 (2020), protein language models, diffusion design | Where tech entrants most often land; see `tech_entrants.csv` |
| `foundation-models` | Biology foundation models / "virtual cell" | Large single-cell, genomic and protein datasets | Often nonprofit or big-tech-adjacent |
| `lab-automation` | Autonomous labs / self-driving labs | Robotics + AI agents | Close to tech companies' strategies |
| `synbio` | Synthetic biology / biomanufacturing | DNA synthesis cost curve | Cooled after the 2021 SPAC era |
| `tools-omics` | Sequencing, single-cell, spatial, proteomics tools | NGS cost curve | Tools companies supply every other silo |
| `diagnostics` | Diagnostics (liquid biopsy, MCED) | cfDNA sequencing | |
| `precision-data` | Clinical / real-world data platforms | EHR + genomic data | |
| `longevity` | Aging / rejuvenation | Partial reprogramming (Yamanaka factors) | Heavy funding from tech billionaires |

## How a silo turns into companies

Things to record for each company in `companies.csv`:

1. **Enabling discovery.** Which paper or technique made the company possible?
2. **Lab of origin.** Which PI or institution? (Broad/Harvard/MIT, Stanford, UCSF, UC Berkeley, and so on)
3. **Builder.** Studio-built (Flagship, ARCH, Third Rock, Atlas) or a founder-led raise?
4. **Model.** Platform or asset? Platforms raise large rounds but need partnerships to make money. Asset companies are simpler M&A targets.
5. **Exit path.** Partnering, M&A, or IPO. This tells you which silos pharma currently wants.
6. **Geography.** Boston/Cambridge, SF Bay Area, San Diego, London/Oxford/Cambridge, Shanghai/Suzhou.
