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

## What we do not do

- No AI in Kraken mutation/write path
- No autonomous migration loops
- No fine-tuning required initially

See also: [STW_TRANSFORM_RULES.md](STW_TRANSFORM_RULES.md) for deterministic utility transforms.
