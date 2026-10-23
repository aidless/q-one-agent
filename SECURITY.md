# Security and privacy

The agent can be connected to hosted models, so callers must treat prompts, retrieved documents, and outputs as sensitive.

- Do not put credentials in source or run artifacts.
- Make provider routing explicit before sending personal context over a network.
- Redact or hash private inputs in run records.
- Restrict tools and retrieval sources to the minimum needed for a decision.
- Record provider failures and abstentions rather than hiding them behind a fallback.
