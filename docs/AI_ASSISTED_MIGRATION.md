# AI-Assisted Migration Layer

## Principle

```
Source extract → AI-assisted layer (suggests) → Deterministic transform/validate → Kraken
                      ↑
              LangChain / LangGraph
              (never in write path)
```

**AI proposes; the deterministic engine disposes.** Every AI output is a draft suggestion requiring human approval through existing workflow states (`draft` → `in_review` → `approved` → `signed_off`).

## Capabilities

| Feature | Provider | API |
|---------|----------|-----|
| Semantic field mapping | LangChain structured output (or heuristic fallback) | `POST .../ai/suggest-mappings/{entity}` |
| Lookup table generation | LangChain / heuristic enum gap analysis | `POST .../ai/suggest-lookups/{entity}` |
| Transform-rule inference from sample values | Deterministic profiler + enum/boolean/date inference | `POST .../ai/suggest-transform-rules/{entity}` |
| Error batch triage | LangGraph loop (or heuristic clustering) | `POST .../ai/triage-errors` |
| Mapping assistant chat | LangChain / heuristic Q&A | `POST .../ai/assistant` |

## Configuration

```env
AI_ENABLED=true
AI_MOCK_MODE=true          # heuristic fallback when no API key (default for CI)
OPENAI_API_KEY=sk-...      # enables LangChain provider
AI_MODEL=gpt-4o-mini
AI_FORCE_HEURISTIC=false   # force rule-based even with key
```

Install optional deps: `pip install -e ".[ai]"`

## Audit trail

Applied field mappings store:

- `ai_suggested` — true when mapping came from AI layer
- `ai_reasoning` — why the model/heuristic suggested the link
- `ai_confidence` — 0–1 score
- `uncovered_source_values` (draft response field) — values observed in source samples with no confident destination mapping

## What we do not do

- No AI in Kraken mutation/write path
- No autonomous migration loops
- No fine-tuning required initially

See also: [STW_TRANSFORM_RULES.md](STW_TRANSFORM_RULES.md) for deterministic utility transforms.

## Quick QA path (non-zero suggestions)

1. Open project page and keep **plugin schema** active (do not use a plain custom target CSV without enum constraints).
2. Upload source file: `samples/severn_trent/target_cmp_ai_gap_sample.csv`.
3. Click **AI suggest**.
4. Click **AI lookup gaps** -> should report enum gaps (e.g. `X`, `Z`, `STD`, `AUDIOBOOK`).
5. Click **AI transform rules** -> should infer conditional/lookup transforms and populate review-first flags for uncovered values.

If either action returns zero:
- confirm source upload is a data extract CSV (not only a field-name list),
- confirm `source_fields[*].sample_values` are present in catalog,
- confirm target schema includes enum/boolean constraints.
