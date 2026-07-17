# Phase 4.4.3 — Continuous Learning

## Purpose

Phase 4.4.3 closes the forecasting feedback loop by converting historical
performance scorecards into persistent model reputation and adaptive ensemble
weights.

## Components

- `ContinuousLearningProfile`
- `ModelLearningStatus`
- `ModelLearningSignal`
- `ModelLearningSnapshot`
- `LearningState`
- `ContinuousLearningResult`
- `ContinuousLearningEngine`
- `ContinuousLearningService`
- Learning-state serialization helpers

## Reputation model

Each model receives a reputation update based on:

- Historical performance score
- Recency of evaluated outcomes
- Stability of bias and interval coverage
- Sample-size support
- Prior reputation

## Model lifecycle

Models may be classified as:

- Promoted
- Stable
- Watch
- Demoted
- Ineligible

## Adaptive weights

Recommended ensemble weights:

- Begin from the current model weights
- Move toward stronger-reputation models
- Respect maximum per-update weight changes
- Respect minimum and maximum weight constraints
- Are normalized to sum to one

## Persistent state

The learning state stores:

- Model reputation
- Adaptive weight
- Lifecycle status
- Sample size
- Update count
- Timestamp
- Supporting metadata

State can be serialized deterministically to JSON and saved atomically.

## Continuous-learning loop

1. Forecast outcomes are archived.
2. Performance scorecards are generated.
3. Reputation and weights are updated.
4. Learning state is persisted.
5. The next forecasting cycle consumes the new adaptive weights.

## Next phase

Phase 4.4.4 will add forecast drift detection and regime-aware performance
memory.
