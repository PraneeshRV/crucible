# Crucible

A falsification gate for AI agents.

Crucible does not investigate. It intercepts the moment an agent is about to commit to a
conclusion that is expensive to get wrong, and forces it to construct a rival explanation,
predeclare what each possible outcome would mean, run the check most likely to change the
decision, update every rival rather than the favoured one, and resolve into an explicit
terminal state.

It records what is *known* separately from what is *permitted*. An authority can authorize
acting under acknowledged uncertainty; it can never turn an unsupported conclusion into a
justified one.

## Install

```bash
git clone https://github.com/PraneeshRV/crucible ~/Praneesh/crucible
ln -s ~/Praneesh/crucible/skill/crucible ~/.claude/skills/crucible
ln -s ~/Praneesh/crucible/skill/crucible ~/.agents/skills/crucible
```

## Status

Pre-release. Gate 1 (pilot) evidence only — see `evals/results/`. Not yet validated at the
Gate 2 threshold required for release.

## Design

Full specification: `docs/superpowers/specs/2026-07-29-crucible-skill-design.md` in the
author's vault.
