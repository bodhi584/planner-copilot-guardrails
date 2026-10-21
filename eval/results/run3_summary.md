# Run 3: same as run 2 plus the two changes in rule_changes.md (2026-10-17)

Kaggle GPU notebook, version 4 (45 min, GPU T4 x2). qwen2.5:7b-instruct, 80 questions x A/B/C, repeat 1.

| | A correct / cautious / wrong | B | C |
|---|---|---|---|
| run 2 | 42 / 9 / 29 | 62 / 7 / 11 | 75 / 2 / 3 |
| **run 3** | **43 / 9 / 28** | **63 / 7 / 10** | **76 / 2 / 2** |

Per case, run 3 (correct / cautious / wrong): A1 A 12/3/6, B 18/2/1, C 20/1/0; A2 A 9/5/5, B 15/3/1, C 19/0/0;
A3 A 13/0/7, B 15/1/4, C 17/1/2; A5 A 9/1/10, B 15/1/4, C 20/0/0.

What changed: only A2-14 (now a scope item; A and B also gain because their refusal is now correct). A3-12 now reaches
`compare` (routing works) and the model states the right winner in text (NEAREST) but leaves `choice` empty: still
cautious. 239 of 240 answers are identical to run 2 (the model is effectively deterministic at the default temperature),
so repeated runs would not estimate variance; use different models or prompt paraphrases instead.

Remaining C errors: A3-13 (model did not compare 12 vs 9 trucks), A3-20 (layout question passed the scope check).
