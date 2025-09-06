You will receive: {slug}, {rating}, optional {statement_file}.
If {statement_file} exists, ground your reasoning to it (do not hallucinate constraints).
Suggest 2–3 strictly easier bridge problems pulled from ratings.json within DELTA=150 of {rating}; if none exist, widen window gradually (up to 300). Prefer similar keywords in the slug.
Then generate a language starter (default: Python) with a minimal test scaffold from examples/input_output.md if provided.