# Axel Coiffard-Donaty — ML reliability & evaluation engineer

I find the bugs that don't crash but falsify results: data leakage, biased samplers, GPU races, numerical drift, CI that stays green on failure. Every fix below is public, tested, and was merged by the project's maintainers. I keep the public **[Silent Failures Registry](https://github.com/AxelNoun/silent-failures)**: twenty classes of such bugs, each with a real specimen, the test that would have caught it, and — for thirteen of them — a static detector.

> [!NOTE]
> **Open to contracts** (remote, English or French): evaluation & test engineering for ML teams, evaluation-integrity reviews, targeted correctness fixes, scientific-stack migrations. Contact: [axel.cffrd.dnty@icloud.com](mailto:axel.cffrd.dnty@icloud.com) · [LinkedIn](https://www.linkedin.com/in/axel-coiffard-donaty-208a9a183/)

[Merged upstream](#merged-upstream) · [Diagnoses](#diagnoses-maintainers-agreed-with) · [Silent Failures Registry](#silent-failures-registry) · [Own projects](#own-projects) · [How I work](#how-i-work)

## Merged upstream

<!-- merged:start -->
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/merged-dark.png">
  <img alt="Timeline of the merge dates of the pull requests listed below, one row per project, June to October 2026." src="assets/merged-light.png" width="100%">
</picture>

| Project | What I fixed or built | Maintainer's words |
|---|---|---|
| [pytorch/executorch #20685](https://github.com/pytorch/executorch/pull/20685) | Runtime MoE expert-sort for the MLX backend: two custom ops, a wire-compatible FlatBuffer field, C++ interpreter changes, a serialization fix, and a stride bug traced into Apple's MLX `matmul.cpp` | "Tested locally. Improves Qwen3.5 perf from 73 tok/sec to 80 tok/sec. Great job!" |
| [pytorch/executorch #22372](https://github.com/pytorch/executorch/pull/22372) | Vulkan quantizer lifted integer scalars as float32 and broke integer indexing; fix + test + Buck target | merged, no changes requested |
| [pytorch/executorch #22373](https://github.com/pytorch/executorch/pull/22373) | Four error guards that could never fire (unraised exceptions, always-true `assert`) made to actually raise; tests | merged |
| [sunlabuiuc/PyHealth #1179](https://github.com/sunlabuiuc/PyHealth/pull/1179) | MEDS (Medical Event Data Standard) dataset support: typed Parquet scan path, schema guard, tests, docs, MIMIC-IV demo (+1,526 lines) | "lgtm" |
| [sunlabuiuc/PyHealth #1203](https://github.com/sunlabuiuc/PyHealth/pull/1203) | External review of an OMOP drug-recommendation task: found a self-leakage bug and a fixture that could not detect the regression it targeted; two hardening commits integrated | author merged my commits |
| [lnccbrown/HSSM #1371](https://github.com/lnccbrown/HSSM/pull/1371) | Parameter order permuted between HSSM and ssm-simulators: fits were fine, predictive draws silently wrong; fix + test over 21 model/likelihood pairs | "Looks good, and thanks for catching the issue." |
| [lnccbrown/HSSM #1411](https://github.com/lnccbrown/HSSM/pull/1411) | The balanced-panel error message suggested `sort_values('participant_id')`, an unstable sort that scrambles each participant's trial order (which the RL likelihood reads) and still passes validation; stable sort suggested, docstrings, tests | "…this is a real bug and a clean fix." |
| [lnccbrown/HSSM #1415](https://github.com/lnccbrown/HSSM/pull/1415) | Follow-up to #1411 from the maintainer's review: the test of the balanced-panel check sorted with the default (unstable) sort that #1410 warns against; it now uses `kind="stable"` | "lgtm! thanks @AxelNoun" |
| [DeepLabCut #3445](https://github.com/DeepLabCut/DeepLabCut/pull/3445) | pandas 3 Copy-on-Write: ten in-place mutations on read-only arrays made safe across eight modules | "definitely correct and very helpful!" |
| [brian-team/brian2 #1861](https://github.com/brian-team/brian2/pull/1861) | ~80 ms `gc.collect()` per `Network.run()` skipped when the warning it served is disabled; regression test | "This makes perfect sense to me, and everything looks good." |
| [brian-team/brian2 #1885](https://github.com/brian-team/brian2/pull/1885) | Developer guidelines refresh (scope I proposed in #1827/#1829) | "Thanks, LGTM!" |
| [brian-team/brian2 #1896](https://github.com/brian-team/brian2/pull/1896) | Dangling pointer diagnosed in #1893: the random state now stores the Cython random-number buffers by value instead of the address of a buffer freed on refill, so `restore()` no longer reads freed memory; older stored states handled with a warning; test | "Thanks, LGTM!" |
| [NeuralEnsemble/python-neo #1891](https://github.com/NeuralEnsemble/python-neo/pull/1891) | `CedRawIO` broken by sonpy ≥ 1.9.12 (three import layouts by version and platform); CED tests re-enabled; test extra fixed | "Looks great. Thanks." — added to the neo 0.14.6 author list |
| [NeuralEnsemble/python-neo #1912](https://github.com/NeuralEnsemble/python-neo/pull/1912) | CI step stayed green when `git ls-remote` failed (exit status of `echo`); `pipefail`, emptiness check, error annotation; backed by log counts | approved by two maintainers |
| [NeuralEnsemble/python-neo #1911](https://github.com/NeuralEnsemble/python-neo/pull/1911) | Python 3.9 dropped from a matrix that had failed weekly since February | approved |
| [catalystneuro/neuroconv #1855](https://github.com/catalystneuro/neuroconv/pull/1855) | `spike2` extra had a PEP 508 marker that could never be satisfied; platform-aware test | "This is ready to go" |
| [fangwei123456/spikingjelly #692](https://github.com/fangwei123456/spikingjelly/pull/692) | Dead assertion on an attribute never defined in the repository's history | merged |
<!-- merged:end -->

<!-- open:start -->
Open and under review: [brian2 #1891](https://github.com/brian-team/brian2/pull/1891) (Cython Binomial sampler wrong for p > 0.5 and non-terminating on underflow), [ComputationalPsychiatry/pyhgf #448](https://github.com/ComputationalPsychiatry/pyhgf/pull/448), [executorch #23798](https://github.com/pytorch/executorch/pull/23798) (bf16 positional-embedding interpolation, approved), [HSSM #1414](https://github.com/lnccbrown/HSSM/pull/1414), [huggingface/course #1328](https://github.com/huggingface/course/pull/1328), [PyHealth #1187](https://github.com/sunlabuiuc/PyHealth/pull/1187) (PTB-XL ECG dataset), [PyHealth #1202](https://github.com/sunlabuiuc/PyHealth/pull/1202) (knowledge-graph embeddings on the 2.0 pipeline, negatives drawn from training triples only), [PyHealth #1207](https://github.com/sunlabuiuc/PyHealth/pull/1207) (deterministic, collision-free task cache keys), [python-neo #1913](https://github.com/NeuralEnsemble/python-neo/pull/1913).
<!-- open:end -->

## Diagnoses maintainers agreed with

- [pytorch/pytorch #200949](https://github.com/pytorch/pytorch/issues/200949) — `grid_sample` on CPU returns wrong values for fp16/bf16 when a gather offset exceeds 32,767 (int16 offset overflow in the vectorized kernel). Labelled "module: correctness (silent)".
- [brian2 #1893](https://github.com/brian-team/brian2/issues/1893) — `restore(restore_random_state=True)` uses a dangling pointer after a RNG buffer refill (Cython target). Maintainer: "I agree with the analysis and the proposed solution." Fixed in [#1896](https://github.com/brian-team/brian2/pull/1896), merged.
- [ml-explore/mlx-lm #1700](https://github.com/ml-explore/mlx-lm/issues/1700) — fused Metal KL/JS kernels reused one threadgroup buffer for max and sum exchanges without a barrier; my fix ([#1719](https://github.com/ml-explore/mlx-lm/pull/1719)) was reproduced independently on an M5 Max (26/50 → 0/50 mismatches). Closed by the maintainers for review capacity, not on technical grounds.
- [PCNtoolkit #600](https://github.com/predictive-clinical-neuroscience/PCNtoolkit/issues/600) — MLL/MSLL used the posterior mean of log p instead of log p(y | D, x) (Jensen bias). Collaborator: "To me it makes sense… I would change it."

## Silent Failures Registry

The fixes above belong to a small number of recurring classes. I wrote them down.

- **[The Registry](https://github.com/AxelNoun/silent-failures)** (EN/FR) — twenty classes of bugs that pass the tests and falsify the results: how each one looks in code, the public pull request where it was found and fixed, the test that would have caught it, how to prevent it. Examples: *the assertion that cannot fail* (executorch #22373), *the parameter order permuted between two libraries* (HSSM #1371), *the CI step that stays green on failure* (python-neo #1912), *the write into a DataFrame view* (DeepLabCut #3445), *the threadgroup barrier that guards nothing* (mlx-lm #1719).
- **[sfradar](https://github.com/AxelNoun/silent-failures/tree/main/sfradar)** — a dependency-free static radar for the thirteen classes that have a reliable pattern (AST + regex, with taint tracking for pandas views). Validated against the seven bug sites above at the commit before each fix (7/7 found, 6/6 cleared on the fixed version) and against a 344-test control repository (0 findings). On a first pass over six live scientific repositories it surfaced seven error guards that cannot fire in a widely used neuroscience library — being reproduced before I report them upstream.

It is a radar, not a judge: it ranks where a reviewer should look first. The registry is how I audit a codebase; the radar makes the first look take minutes.

## Own projects

<!-- projects:start -->
- [discoursekit](https://github.com/AxelNoun/discoursekit) — linguistic measures for discourse research; UAX #29 tokenizer that passes the official conformance test, MATTR, embedding-based coherence, permutation-test segmentation. 344 tests, `ruff` and `mypy` clean, doctests run as tests.
- [kinoscope](https://github.com/AxelNoun/kinoscope) — kinase–inhibitor affinity prediction under a leakage-free, four-regime evaluation protocol (random, cold-drug, cold-target, temporal) with an automated leakage audit in CI and Hypothesis property tests. No model trained yet; the README says so.
- [tpl-lab](https://github.com/AxelNoun/tpl-lab) — a pre-registered falsification test of a geometric conjecture on Allen Neuropixels recordings; decision rule frozen before the data; 12/12 refuted. Latest release: [v0.1.0](https://github.com/AxelNoun/tpl-lab/releases/tag/v0.1.0).
- [neurovis3d](https://github.com/AxelNoun/neurovis3d) — diagnostics for spiking neural networks (snnTorch): dead-neuron ratio, sparsity, temporal gradient signature. Work in progress; indicators not yet validated against analytical ground truth.
<!-- projects:end -->

## How I work

- Test plans say what they did **not** exercise, with negative controls (see executorch #22372 and #22373).
- I work in unfamiliar codebases and follow their conventions (Buck targets, FlatBuffer wire compatibility, review requests).
- I use AI coding assistants and say so in every commit; what I'm paid for is the diagnosis, the direction and the verification.
- Windows machine, no Apple or NVIDIA hardware: Metal/MLX work is validated through upstream CI and third-party reproduction.
