# Unresolved pin -> question -> prompt -> proposed experiment

Implemented 2026-09-07 in `pin_questions.py`, with additive hooks in
`diagonal.py` and `play.py`. This first version builds a local prompt outbox.
It does not contact a language model, spend API credits, or choose game actions.

The connection to the earlier void-line idea is operational: a gap in evidence
becomes a request for information. No sedenion zero product is needed to
generate a question, and an algebraic cancellation is not treated as a game
outcome.

## What it asks

| Evidence | Question | Completion rule |
| --- | --- | --- |
| No trials with the condition | What happens with it present? | At least one observed with-condition trial. |
| No trials without the condition | Would the effect happen without it? | At least one observed without-condition trial. |
| Only one or two trials on either side | Can we reproduce that observation? | Reach the configured sampling quota, default three. |
| Fires without it, or stays silent with it | What additional context explains the contradiction? | Not closed automatically by more counts; replace/refine the hypothesis. |

Three trials is a small exploration quota, not a statistical confidence
threshold. Here positive/negative mean condition present/absent, not
success/failure. Observational counts cannot establish causality.

For example, `fired_with=1, fired_without=0, silent_with=0,
silent_without=0` creates a missing-negative question and a repetition question.
If the next observation fires without the condition, the missing-negative
question is answered by that counterexample, while a contradiction question
opens. A model's reply cannot answer either question by itself.

## What travels with the prompt

Each record includes a scope and stable ID, the pin and condition, all four
counts, sample sizes, conditional rates, the specific question, a proposed test,
and explicit blockers. The prompt requests a structured proposal containing
prerequisites, candidate controls, predicted observations under competing
hypotheses, and stop conditions. It forbids inventing observations or missing
controls/patterns/routes.

New diagonal dumps now retain the pattern or relation matcher specification,
including floor context when provided. They also describe which existing eye
events were counted: relations currently use level events for firing;
nonrelations use level/state/pass proxies, and refusal supplies silence.
Those proxies still need target-specific verification before causal testing.
The counter implementation itself has not been changed.

Older saved reports omit the condition pattern. Their prompts explicitly flag
that omission instead of reconstructing a pattern from a bounding box. An empty
front-control list is an unknown binding, not permission to try every button.
An always-true ring predicate cannot support an absent-condition experiment;
the question asks for a meaningful observable predicate first.

## Integration and lifecycle

- Each game/level gets its own `QuestionQueue`.
- At diagonal rebuilds, `play.py` refreshes the queue from cumulative counts and
  includes it under `question_queue` in the normal diagonal log/report.
- The final level observation refreshes the queue before saving the level report.
- Repeated snapshots do not increment evidence or duplicate questions.
- Decreasing counts retire open questions as an evidence reset. Changed
  hypotheses and disappearing pins retire their old questions too.
- Answered sampling questions retain their closing counts. More repetition may
  remain pending; no status means the causal rule has been proven.
- Questions and prompts persist in the normal report files, but queue history
  is not restored across process restarts in this version.

All records have `execution_ready=false` and `transport=local_outbox_only`.
Missing blockers do not imply that route, budget, or action safety has been
checked. The next stage is a proposal consumer with validation against the
current frame, known controls, reachable states, and remaining game budget.
No remote model transport or response consumer has been added yet.

## Offline pilot

Five existing reports produced 16 questions: LS20 L1/L2/current yielded 2/4/4;
SP80 L1/current yielded 5/1. All five old reports lacked condition specifications,
so none provides a fully specified executable experiment. The current SP80
report had one firing with the condition and eleven silent trials without it;
its useful request is to repeat the positive case, not collect another first
negative case.

The latest generated prompt examples are in
[the local outbox](D:/planet/eye/pin_question_outbox_20260907_codex_v2.json).
The first pilot outbox is retained separately. Input recordings were unchanged.
Files are treated independently in the CLI because they may represent different
levels, not a chronological stream from one hypothesis.

Validation: 15 new question tests plus the 10 algebra/cube tests pass. Checks
cover lifecycle, contradictory outcomes, scope isolation, reset/disappearance,
deduplication, missing information, prompt contents, and diagonal serialization.
The modified play script passes syntax parsing; no live game or external-model
end-to-end run has been performed. Its existing Windows-path docstring escape
warning is unrelated to these changes.

```powershell
Set-Location -LiteralPath 'C:\Users\GamerTech\Desktop\Vesica AI\AI Detector\planet'
python -X utf8 -B -W error::ResourceWarning -m unittest test_pin_questions test_algebra_memory -v
python -X utf8 -B pin_questions.py D:\planet\eye\diagonal_sp80.json
```

An optional `--output NEW_PATH.json` creates a new outbox and refuses to
overwrite an existing file. Direct Python use is `QuestionQueue(scope).update`
with a list from `diag.dump(floor=known_floor)`; retain the same queue instance
for successive cumulative snapshots of one level.
