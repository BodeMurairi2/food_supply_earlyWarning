"""System instruction for repairing an answer that did not match the output schema."""

REPAIR_INSTRUCTION = """You receive a DRAFT answer from a food security analyst, which is incomplete or badly formatted, and the ORIGINAL REQUEST
with its numbers. Rewrite the draft in the required structured format, filling every field.

Keep the draft's meaning. Do not add facts, statistics, URLs or source ids that are not in the draft or the request. Keep only source
ids (S1, S2, ...) that appear in the draft; if a section has no evidence, leave its list empty. If the draft was cut off, complete the
remaining fields using only the request's numbers, and say in the limitations that outside evidence could not be fully reviewed."""
