# Run 4: other models (Kaggle version 6, 17/18 Oct 2026)

Same bundle and patches as run 3 (compare routing, A2-14 scope). Numbers below are read from the Kaggle log tables
(the version was cancelled while Mistral was stuck, so per-answer files were not saved; rerun Llama for those).

## llama3.1:8b (32 min)

| Case | A correct / cautious / wrong | B | C |
|---|---|---|---|
| A1 | 11 / 2 / 8 | 15 / 5 / 1 | 18 / 3 / 0 |
| A2 | 5 / 9 / 5 | 11 / 6 / 2 | 10 / 6 / 3 |
| A3 | 4 / 2 / 14 | 5 / 10 / 5 | 17 / 1 / 2 |
| A5 | 7 / 0 / 13 | 11 / 3 / 6 | 18 / 0 / 2 |
| **Total (80)** | **27 / 13 / 40** | **42 / 24 / 14** | **63 / 10 / 7** |

Compared with qwen2.5:7b (run 3): A 43/9/28, B 63/7/10, C 76/2/2.
Same ordering for both models: C > B > A in correct answers, and C has the fewest confidently wrong answers.
Llama is weaker overall; its C errors concentrate in A2 (3 wrong, 6 cautious).

## mistral:7b-instruct

Pulled and smoke-tested, then produced no answer for A1 in > 5 h (no log output after the smoke test); cancelled at
02:00 UTC to save GPU quota. Likely cause: the model does not end its turn / repeats, so every call runs into the
180 s timeout (x retries). To do: rerun alone with a lower max_tokens and timeout, or replace with another model.
