*Teymour Davoudi*

*DSCI 305*

*Dr. Abramson*

*April 24, 2026*

## 1. Problem

It is well-known that large language models, by design, are forced to give users an output. This fundamental property of LLMs often leads to "hallucinations," confident-sounding responses that are either incorrect or fabricated altogether. One such area in which hallucinations are particularly common (and dangerous) is citations. Walters and Wilder (2023) studied ChatGPT-generated bibliographies and found that roughly 47% of references in their sample were fully fabricated, containing nonexistent papers with plausible authors, titles, and DOIs. Bhattacharyya et al. (2023) reported similar rates in medical prompts. Chelli et al. (2024) documented hallucinated references in submitted and even a handful of published manuscripts. Though models have significantly improved since these studies took place, hallucinated citations remain a major issue today.

It is plain to see why hallucinated citations are so dangerous. Beyond wasting reviewer time, in clinical, legal, and policy contexts, decisions made on the basis of citations that do not exist carry material consequences. And in the past several years, it is likely that much false information has been taken as fact and applied in consequential, real-world contexts because nobody cared to check the legitimacy of the apparent source of this information.

`Hallucitation` is a direct response to this issue. It accepts a research PDF, extracts the references section, parses each entry, and verifies it against **Crossref** and **OpenAlex**, two independent, free, and public scholarly metadata services. References with no match in either are flagged as **hallucinated**.

## 2. Audience

The intended users are:

- **Researchers** sanity-checking LLM-assisted literature reviews before submission.
- **Journal editors and peer reviewers** spot-checking bibliographies without a commercial citation manager.
- **Journalists** fact-checking AI-assisted articles.
- **Instructors** auditing student work in a world where bibliographies are now routinely pasted out of LLMs.
- **The open-science community**, who benefit when integrity checks are free, scriptable, and transparent.

## 3. Ethical framework: NIST AI Risk Management Framework (2023)

`Hallucitation` is designed in accordance with the four core functions of the NIST AI Risk Management Framework (GOVERN / MAP / MEASURE / MANAGE). NIST is an apt choice for this project because the tool is itself an AI **countermeasure**; its intent is to mitigate common errors produced by AI systems, making NIST's AI risk-management vocabulary and focus an excellent fit. The tool strives to adhere to the framework as follows:

- **GOVERN.** MIT licensed, with a documented scope, explicit limitations, and a reproducible CI workflow. PDFs are processed in-memory; no telemetry, no logging beyond an opt-in `--verbose` flag. Most importantly, the tool ships with **zero AI/LLM dependencies** by design. Every verdict is produced by deterministic code. This eliminates the meta-risk of an AI auditor that itself hallucinates.

- **MAP.** The README documents what the tool can and cannot do. It detects references with no presence in Crossref or OpenAlex. It cannot detect citations to real-but-retracted papers, citations to obscure venues not indexed by either service, plausible citations that point to the wrong real paper, or non-English papers with poor metadata coverage. These limits are made expressly clear.

- **MEASURE.** Every hallucination verdict comes from a transparent and well-defined scoring rubric that combines title fuzzy similarity, first-author surname match, year proximity, and DOI exact match. Further, cross-checking against **two independent sources** bolsters confidence and robustness. Absence from both sources is the only path to a `hallucinated` verdict. A labeled test bibliography (real + hallucinated + mixed references) is provided within the repository. The evaluation run on this bibliography reports Precision = Recall = F1 = 1.000, with caveats noted.

- **MANAGE.** This tool is human-in-the-loop by design. The tool flags suspects for hallucinated citations. However, it never edits or deletes; this is the job of the reviewer. Every report includes per-citation notes explaining why a verdict was reached and links back to the underlying Crossref / OpenAlex record, giving the reviewer the ability to disagree and override.

## 4. Social impact

The concrete impact of `Hallucitation` is lowering the cost of citation auditing from hours of manual lookup to seconds of running code. This matters most for under-resourced authors and reviewers who cannot afford commercial tools to perform these tasks. Further, it pushes the burden of integrity off the individual scholar/reviewer and onto reproducible infrastructure, mitigating the risk of human error in citation auditing.

## 5. Limitations and risks

**False positives** (flagging a real reference): the dominant failure vector is obscure venues with poor Crossref/OpenAlex coverage. The dual-source threshold minimizes this risk but does not eliminate it. While this tool is powerful and makes verifying most sources much faster and more robust, reviewers are encouraged to manually ensure that all flags are correct.

**False negatives**: the tool cannot detect citations to retracted papers or citations where an LLM produced a real paper's metadata for the wrong claim. Both are outside the scope of the basic reference verification that `Hallucitation` performs.

**Meta-risk**: using AI to check AI-generated content (which many people often do) is itself a risk. `Hallucitation` deliberately avoids that trap. The tool has no LLM dependency or calls.

## 6. Compliance

Released under the MIT License. All processing is local. Crossref and OpenAlex are free public APIs with permissive terms; the tool sends a polite-pool User-Agent header on every request. No PII is collected. No data ever leaves the user's machine except to Crossref and OpenAlex, which only ever see public bibliographic metadata.

## References

Bhattacharyya, M., Miller, V., Bhattacharyya, D., & Miller, L. (2023). High Rates of Fabricated and Inaccurate References in ChatGPT-Generated Medical Content. *Cureus*, 15(5), e39238.

Chelli, M., Descamps, J., Lavoué, V., et al. (2024). Hallucination Rates and Reference Accuracy of ChatGPT and Bard for Systematic Reviews. *JMIR Medical Informatics*, 12, e53164.

National Institute of Standards and Technology. (2023). *AI Risk Management Framework (AI RMF 1.0)*. NIST AI 100-1. https://www.nist.gov/itl/ai-risk-management-framework

Walters, W. H., & Wilder, E. I. (2023). Fabrication and errors in the bibliographic citations generated by ChatGPT. *Scientific Reports*, 13, 14045.
