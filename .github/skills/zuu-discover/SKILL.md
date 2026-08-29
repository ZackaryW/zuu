---
name: zuu-discover
description: Explore a repository, URL, package, or other source read-only to identify small generic utilities that could become independent zuu cases. Use for case discovery and candidate evaluation; do not use to implement cases or port whole packages.
---

# Zuu Discover

Investigate one supplied source and return an evidence-backed shortlist of reusable
utility responsibilities. The goal is to discover ideas worth expressing as zuu
cases, not to reproduce the source package.

## Establish the target

Require a concrete source such as a local repository path, repository URL, package,
documentation set, or code sample. If the target is already supplied, inspect it
without asking redundant questions. Clarify only when access, source boundaries, or
the desired area of investigation would materially change the result.

Keep the exploration read-only. Do not modify the source, zuu, or external systems;
do not create cases, planning artifacts, or commits. A temporary read-only checkout
is acceptable when a remote repository cannot be inspected directly, but it must not
become part of either repository.

## Inspect for reusable mechanisms

Read enough source evidence to understand behavior rather than inferring candidates
from filenames. Inspect the relevant public APIs, implementations, tests, examples,
and documentation. Look for bounded mechanisms such as deterministic transforms,
state transitions, filesystem operations, matching rules, serialization boundaries,
or replaceable protocols that remain useful outside the original product.

Compare candidates against the current zuu index, each case's `__purpose__` and
`__depends__`, and the relevant public APIs. Identify overlap explicitly. A nearby
topic does not mean a candidate extends an existing case.

## Apply the genericity filter

A strong candidate:

- has one concise purpose understandable without the source package;
- is useful in at least two plausible contexts beyond the source;
- can expose a small composable API using ordinary Python values or protocols;
- can shed product names, orchestration, configuration formats, and domain policy;
- can be tested independently through observable behavior;
- does not duplicate an existing zuu case; and
- can reasonably preserve zuu's standard-library-only runtime.

Reject or downgrade a candidate when its value depends on copying the package's
architecture, coordinating most of its subsystems, preserving source-specific data
models, or importing substantial third-party behavior. Extract concepts and
contracts, never source code or a disguised port.

## Separate responsibilities and dependencies

Propose distinct cases when responsibilities remain independently useful. Combine
them only when separating them would destroy the public lifecycle or force callers
to coordinate private details.

Declare a proposed dependency only when one candidate would directly consume
another case's public API. Do not use dependency language to mean thematic relation,
shared origin, or implementation order. Treat case0 as reserved foundational
utilities, not a destination for ordinary discovered capabilities.

Do not assign final case numbers during discovery. The owner selects candidates and
their order before case development begins.

## Report candidates

Lead with the strongest candidates. For each one, provide:

- a provisional utility name and one-sentence purpose;
- exact source evidence, including relevant paths, symbols, or documentation;
- the generic behavior retained and source-specific behavior discarded;
- a small public API sketch, without implementation;
- possible direct zuu dependencies or overlap with existing cases;
- two or more example contexts demonstrating generic value;
- important non-goals or risks; and
- a recommendation: strong, conditional, or reject.

Include notable rejected ideas when they might otherwise look attractive, explaining
why they fail the genericity filter. End with a short recommended selection for the
owner. Stop there and ask which candidates, if any, should move into the separate
case-development process.
