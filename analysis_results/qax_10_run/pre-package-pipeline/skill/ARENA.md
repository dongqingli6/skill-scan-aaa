# Arena — pre-package-pipeline
# Human edits this. The organism runs experiments against it overnight.
# Analogous to program.md in Karpathy's autoresearch.

## Fitness metric
primary: composite_score
formula: "correctness×0.25 + reasoning_depth×0.20 + completeness×0.25 + hallucination_risk×0.20 + coherence×0.10"
improvement_threshold: 0.05
regression_threshold: 0.10

## Experiment budget
eval_budget_seconds: 30
eval_dataset: "datasets/synthetic/pre-package-pipeline/shard_000.json"
eval_n_items: 50
max_experiments_per_generation: 12

## Mutation strategies
allowed_mutations:
  - instruction_clarity
  - example_replacement
  - output_schema_tightening
  - edge_case_handling
  - reasoning_scaffolding

## Transfer test (Karpathy's depth-N insight applied to skill complexity)
transfer_dataset: "datasets/synthetic/pre-package-pipeline/shard_001.json"
transfer_n_items: 30
transfer_pass_threshold: -0.15

## Browser arena config
browser_demo_enabled: true
demo_eval_dimensions: [correctness, reasoning_depth, completeness, hallucination_risk, coherence]

## Trilogy integration
mindspider_feed_enabled: false
bettafish_engine_type: null
mirofish_simulation_enabled: false

## What "better" means
improvement_requires:
  - composite_score increases by >= 0.05
  - hallucination_risk does NOT decrease
  - transfer_test passes
notes: "Standard skill improvement via instruction clarity and example quality."
