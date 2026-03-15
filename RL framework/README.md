# Agentic Research Framework for QDP / QDEP Programs

**Status:** Working internal reference  
**Date:** 2026-03-06  
**Scope:** Project architecture, governance, artifacts, workflows, and implementation sequencing  
**Reference basis:** The maturity model follows the nested-ring progression in the reference image: **AI & Machine Learning -> Deep Neural Networks -> Generative AI -> AI Agents -> Agentic AI**.

---

## 1. Executive Summary

This project should not be framed as an attempt to build an autonomous quantum company. That framing is structurally wrong and leads directly to brittle architectures, incoherent delegation, and uncontrolled risk.

The correct framing is narrower and more operational:

> Build an **agentic research-operations layer** that shortens the path from **hypothesis -> model/run specification -> simulation/evidence -> claim adjudication -> decision memo -> downstream QDEP transfer**, while keeping consequential judgment, theory selection, and irreversible actions under explicit human control.

In this framework:

- **Generative AI** handles drafting, summarisation, extraction, and code/text generation.
- **AI Agents** add planning, tool use, memory, task decomposition, and bounded coordination.
- **Agentic AI** is the outer control layer: governance, safety, memory policy, observability, risk controls, evaluation, and limited long-horizon autonomy.

The practical objective is not to maximize autonomy. The objective is to maximize **reliable, traceable, decision-useful delegation**.

The system is successful when it can:
1. reduce duplicate work,
2. improve evidence traceability,
3. lower time-to-decision for bounded research questions,
4. preserve provenance and contradiction awareness,
5. remain inspectable when it fails.

---

## 2. Working Assumptions and Glossary

This document preserves the working assumptions used in prior discussion. If project terminology changes, rename entities, but keep the control structure.

### 2.1 Working terminology

- **OCH / TCF**  
  Upstream theoretical priors, framing assumptions, mechanism hypotheses, or model families.

- **QDP**  
  The mechanism-discrimination and evidence-synthesis layer that sits between upstream theory and downstream deployment / transfer.  
  Primary function: translate ambiguous research questions into testable artifact chains.

- **QDEP**  
  The downstream transfer layer where validated QDP outputs are converted into actionable design rules, experiment proposals, or applied program decisions.

- **QSIP**  
  The execution substrate for simulation, compute jobs, and bounded analysis pipelines. QSIP is a runtime / platform, not an autonomous decision-maker.

### 2.2 Key principle

QDP is the **control surface** between upstream theory and downstream program action.  
That means QDP must be built as a governed orchestration system, not as an unconstrained chat stack.

---

## 3. Reference Model: What the Image Actually Implies

The reference image is not a branding diagram. It is an architecture maturity ladder.

### 3.1 Lower rings: capability substrate

- **AI & Machine Learning**: optimisation, representation learning, reinforcement learning, reasoning components, attention, supervised/unsupervised learning.
- **Deep Neural Networks**: CNNs, RNNs/LSTMs, transfer learning, pretraining/fine-tuning, large language models.
- **Generative AI**: text, code, images, audio, multimodal generation, retrieval-augmented generation, function calling, summarisation, prompt engineering.

These layers are necessary but not sufficient.

### 3.2 Middle ring: AI Agents

AI Agents introduce:
- planning,
- context management,
- memory systems,
- tool orchestration,
- task decomposition,
- scheduling,
- coordination,
- bounded autonomy.

This is where most teams stop. That is why most systems remain brittle.

### 3.3 Outer ring: Agentic AI

Agentic AI is not “smarter chat”. It is a control regime around agents. The image’s outer ring implies:

- long-term autonomy and goal chaining,
- governance, safety, and guardrails,
- memory governance and retention policy,
- observability and tracing,
- feedback loops and evaluators,
- risk management and hard constraints,
- self-healing / self-improving mechanisms,
- explicit protocols for coordination.

A system should not be called agentic unless those controls exist.

---

## 4. Design Principles

1. **Typed artifacts over free-form chat**  
   Canonical project memory must be typed, versioned, attributable, and queryable.

2. **Proposal is not approval**  
   No agent can certify its own proposal as accepted truth.

3. **Evidence before claim**  
   Every consequential claim must point to evidence objects, not just prose.

4. **Bounded tools only**  
   Tools must have explicit contracts, cost models, side-effect classes, and retry policies.

5. **Human judgment remains at the theory / strategy layer**  
   Agents support theory testing and evidence synthesis; they do not own theory selection or strategic commitment.

6. **Child agents must be shallow and scoped**  
   Default maximum delegation depth is 1. Recursive spawning is disabled until explicitly proven necessary.

7. **Observability is mandatory**  
   If the system cannot be inspected, it cannot be trusted.

8. **Memory must be governed**  
   Raw conversational residue is not canonical memory. Summaries and typed records are.

9. **Reversible actions by default**  
   Drafts are preferred over commits. Sandboxes are preferred over live systems.

10. **The goal is operational reliability, not theatrical autonomy**  
    “Looks autonomous” is not a metric.

---

## 5. System Objectives

### 5.1 Primary objectives

- Compress the cycle time from research question to decision memo.
- Reduce duplicate simulations, redundant literature review, and lost context.
- Preserve a versioned evidence graph linking assumptions, models, runs, and claims.
- Make contradictions explicit rather than burying them in narrative summaries.
- Improve transfer from QDP outputs into QDEP-ready design material.

### 5.2 Non-objectives

This system is **not** intended to:
- autonomously choose the program’s scientific direction,
- autonomously allocate meaningful capital,
- autonomously publish or communicate externally,
- autonomously modify physical lab procedures,
- autonomously manage unrestricted long-horizon business execution.

---

## 6. System Architecture

### 6.1 Layered architecture

```text
Researchers / Decision Owners
        │
        ▼
Research UI / Notebook / API / CLI
        │
        ▼
QDP Supervisor  ───── Approval Router ───── Human Reviewer
        │
        ├── Theory Interface Agent
        ├── Literature Scout Agent
        ├── Solver Router Agent
        ├── Run Auditor / Identifiability Agent
        ├── Skeptic / Contradiction Checker
        └── QDEP Transfer Drafting Agent
        │
        ▼
Artifact Ledger (typed, versioned, cited)
        │
        ├── HypothesisCards
        ├── ModelSpecs / NoiseSpecs
        ├── RunSpecs / ResultRecords
        ├── ClaimLedgerEntries
        ├── ContradictionIssues
        └── DecisionMemos
        │
        ▼
Retrieval / Code / Repo / Search / Simulation Tool Layer
        │
        ▼
QSIP / Compute Runtime / Storage / Internal Services
        │
        ▼
Trace Store / Eval Store / Audit Logs / Budget Controls
```

### 6.2 Separation of planes

The architecture has three planes:

#### A. Work plane
Where agents perform bounded research operations:
- reading,
- extracting,
- planning,
- generating specs,
- launching approved jobs,
- synthesizing findings.

#### B. Control plane
Where the system enforces:
- access policy,
- tool permissions,
- risk tiering,
- cost ceilings,
- approval gates,
- state transitions,
- stop conditions.

#### C. Evaluation plane
Where the system measures:
- schema compliance,
- tool reliability,
- provenance coverage,
- contradiction detection,
- decision usefulness,
- cost / latency / rework,
- failure modes.

If these planes are not separated, the system will drift into operational ambiguity.

---

## 7. Core Agent Topology

### 7.1 QDP Supervisor

**Role**  
Primary orchestrator for intake, task decomposition, delegation, synthesis, and handoff to review.

**Inputs**
- researcher question,
- current artifact context,
- prior claims,
- active contradictions,
- budget / risk constraints.

**Outputs**
- task plan,
- delegation contracts,
- synthesis packet,
- decision memo draft,
- approval requests.

**Allowed actions**
- create bounded sub-tasks,
- request information,
- invoke read-only tools,
- draft run specifications,
- route for approval.

**Disallowed actions**
- approving its own claims,
- modifying canonical ontology unilaterally,
- committing expensive runs above threshold,
- performing external communication,
- writing unstructured memory as canonical truth.

**Success criteria**
- valid decomposition,
- low redundancy,
- bounded cost,
- high citation/provenance coverage,
- coherent final synthesis.

### 7.2 Theory Interface Agent

**Role**  
Translate upstream OCH/TCF framing into testable mechanism statements and observable implications.

**Inputs**
- theory notes,
- prior models,
- mechanism families,
- unresolved questions.

**Outputs**
- HypothesisCard,
- assumptions list,
- observable mappings,
- candidate discriminators.

**Failure mode to watch**
- converting ambiguity into fake certainty.

### 7.3 Literature Scout Agent

**Role**  
Gather, rank, and compress external and internal literature relevant to current mechanism testing.

**Outputs**
- literature summaries,
- claim-evidence packets,
- unresolved inconsistencies,
- confidence modifiers for hypotheses.

**Failure mode**
- verbosity without discriminative value.

### 7.4 Solver Router Agent

**Role**  
Map hypothesis and model requirements to the correct simulation or analysis path.

**Outputs**
- ModelSpec,
- NoiseSpec,
- RunSpec,
- estimated cost and confidence in the chosen path.

**Failure mode**
- sending a problem to the wrong solver family,
- underestimating compute burden,
- hiding modelling assumptions.

### 7.5 Run Auditor / Identifiability Agent

**Role**  
Check convergence, sensitivity, identifiability, and methodological sufficiency before a result is promoted to evidence.

**Outputs**
- audit result,
- warnings,
- rejection reasons,
- remediation suggestions.

**Failure mode**
- superficial pass / fail checks without mechanistic scrutiny.

### 7.6 Skeptic / Contradiction Checker

**Role**  
Red-team claims, compare against prior evidence, and force explicit contradiction handling.

**Outputs**
- ContradictionIssue,
- challenge note,
- confidence downgrade,
- escalation flag.

**Failure mode**
- cosmetic skepticism instead of meaningful challenge.

### 7.7 QDEP Transfer Drafting Agent

**Role**  
Convert validated QDP outputs into downstream-ready design rules, experiment drafts, or transfer memos.

**Outputs**
- DecisionMemo,
- QDEP transfer packet,
- residual uncertainty register.

**Failure mode**
- overstating certainty during transfer.

### 7.8 Portfolio Governor (V3 only)

**Role**  
Maintain a view of the program-level queue, hypothesis portfolio, and scheduled review cadence.

**Outputs**
- prioritization proposals,
- portfolio health summaries,
- reranking recommendations.

**Disallowed actions**
- strategy commitment without human review.

---

## 8. Canonical Artifact Ledger

The artifact ledger is the backbone of the entire system.  
Without it, agents become eloquent but non-recoverable.

### 8.1 Canonical chain

```text
HypothesisCard
    -> ModelSpec
    -> NoiseSpec
    -> RunSpec
    -> ResultRecord
    -> ClaimLedgerEntry
    -> DecisionMemo
```

### 8.2 Required properties across all artifacts

Every canonical artifact must have:

- stable `id`,
- `version`,
- `created_at`,
- `created_by`,
- `status`,
- provenance or source references,
- links to parent / child artifacts,
- confidence or uncertainty field where applicable,
- explicit assumptions where applicable.

### 8.3 Artifact lifecycle state model

Suggested common states:

- `proposed`
- `triaged`
- `approved_for_test`
- `running`
- `completed`
- `challenged`
- `accepted`
- `parked`
- `rejected`
- `archived`

### 8.4 Why this matters

Typed artifacts enable:
- retrieval that does not depend on brittle chat history,
- exact lineage from question to result,
- duplicate detection,
- contradiction tracking,
- auditability,
- stable evaluation.

---

## 9. Memory Model

### 9.1 Memory classes

#### A. Ephemeral working memory
Session-only context used during a single run.

Examples:
- current task plan,
- scratch summaries,
- temporary execution notes.

#### B. Canonical long-term memory
Versioned artifact ledger and curated research memory.

Examples:
- accepted hypotheses,
- validated model specs,
- audited result records,
- resolved contradictions,
- decision memos.

#### C. Derived retrieval memory
Indexes, embeddings, tag graphs, and summary caches generated from canonical artifacts.

### 9.2 Memory write policy

Agents may write:
- draft summaries,
- structured proposed artifacts,
- links between existing objects.

Agents may not write:
- unreviewed free-form narratives as truth,
- private or hidden internal reasoning as canonical memory,
- speculative conclusions without provenance.

### 9.3 Retention discipline

Memory is an asset and a liability. Retention policy must define:
- what is stored,
- what expires,
- what can be revised,
- what requires immutable audit retention,
- what must be redacted.

---

## 10. Tooling and Tool Contracts

Every tool exposed to any agent must declare:

- `name`
- `description`
- `input_schema`
- `output_schema`
- `side_effect_class`
- `cost_estimator`
- `timeout_s`
- `retry_policy`
- `idempotency_key_strategy`
- `approval_policy`
- `allowed_roles`
- `logging_policy`

### 10.1 Side-effect classes

- `none` — read-only or purely analytical
- `draft` — writes a reversible draft object
- `internal_mutation` — changes an internal project object
- `external_action` — communicates or commits outside the sandbox
- `irreversible` — should be blocked by policy unless separately approved

### 10.2 Default policy

Only `none` and `draft` tools are enabled by default.

### 10.3 Tool categories

- literature search
- internal file search
- schema validation
- code execution
- simulation job submission
- result retrieval
- citation/provenance resolution
- contradiction graph query
- budget inspection
- approval request submission

---

## 11. Governance, Safety, and Risk Controls

### 11.1 Risk tiers

#### Tier 0 — Advisory
Purely informational. No state change.  
Example: summarise papers.

#### Tier 1 — Drafting
Creates draft artifacts only.  
Example: draft a HypothesisCard or DecisionMemo.

#### Tier 2 — Bounded internal action
Internal mutations with low impact and explicit traceability.  
Example: attach references, tag artifacts, queue low-cost runs below threshold.

#### Tier 3 — Expensive or consequential internal action
Requires approval.  
Example: high-cost simulation sweep, ontology change, registry update, status promotion.

#### Tier 4 — External or irreversible action
Disabled by default.  
Example: external messaging, procurement, publication submission, physical system control.

### 11.2 Approval gates

Approval is required before:
- any run above cost threshold,
- any run above time threshold,
- any ontology or registry modification,
- promoting a challenged claim to accepted,
- external communication,
- irreversible internal mutation.

### 11.3 Separation of duties

At minimum:
- one component proposes,
- another validates,
- a human or designated controller approves.

No single agent should both:
- create a hypothesis,
- validate it,
- mark it accepted,
- and write it into canonical memory as settled truth.

### 11.4 Hard limits

Defaults:
- max agent depth: 1
- max parallel workers: 4
- max retries per tool: 2
- max unanswered contradiction count before escalation: 3
- max automatic run cost per request: configurable
- max continuous autonomous runtime before checkpoint/review: configurable

---

## 12. Workflow Specifications

### 12.1 Primary research loop

```text
1. Intake question
2. Parse constraints and desired outputs
3. Retrieve relevant artifacts and prior claims
4. Generate / update HypothesisCard
5. Produce ModelSpec and NoiseSpec
6. Produce RunSpec and estimated cost/risk
7. Route to approval if threshold exceeded
8. Execute or queue bounded run
9. Ingest ResultRecord
10. Run audit and identifiability checks
11. Run contradiction / skeptic pass
12. Update ClaimLedgerEntry
13. Draft DecisionMemo
14. Human review
15. Write approved artifacts to canonical memory
16. Generate QDEP transfer packet if applicable
```

### 12.2 Contradiction loop

```text
1. New claim enters ledger
2. Compare against active and historical claims
3. Open ContradictionIssue if conflict threshold met
4. Route to skeptic
5. Require explicit disposition:
   - resolved
   - tolerated with caveat
   - re-test required
   - reject claim
```

### 12.3 Literature watch loop

```text
1. Scheduled trigger
2. Search for new relevant sources
3. Extract claims and methods
4. Compare against active hypotheses
5. Flag impact:
   - no effect
   - confidence modifier
   - contradiction
   - new mechanism branch
6. Queue review memo
```

### 12.4 Failure recovery loop

```text
1. Tool fails or returns invalid schema
2. Retry if policy permits
3. If still failing, degrade gracefully:
   - fallback tool
   - partial result
   - explicit uncertainty marker
4. Log failure class
5. Preserve trace and state
6. Route unresolved blockage to human review
```

---

## 13. Evaluation Framework

### 13.1 Evaluation philosophy

Evaluate the workflow, not just the prose.

A final answer can sound competent while the workflow underneath is unsafe, duplicated, uncited, or irreproducible.

### 13.2 Core metric families

#### A. Reliability
- schema validation rate,
- tool success rate,
- idempotent retry success,
- workflow completion rate.

#### B. Traceability
- percentage of claims with provenance,
- percentage of accepted claims linked to ResultRecord,
- contradiction capture rate.

#### C. Scientific usefulness
- researcher usefulness score,
- decision memo adoption rate,
- duplicate-run reduction,
- time-to-decision reduction.

#### D. Risk / control
- unauthorized action count,
- approval bypass attempts,
- uncited-claim count,
- stale-memory incidents,
- ontology drift incidents.

#### E. Efficiency
- median cost per resolved question,
- median latency per workflow class,
- token / compute budget adherence,
- unnecessary parallel branch rate.

### 13.3 Mandatory eval types

- unit evals for schemas and tool adapters,
- integration evals for workflows,
- adversarial evals for contradiction detection,
- regression evals after prompt / policy changes,
- human review calibration for decision usefulness.

---

## 14. Maturity Model

## 14.1 V1 — Instrumented Copilot

**Shape**  
One supervisor, one skeptic pass, minimal tools, typed artifacts, no recursive delegation.

**Purpose**  
Stabilize the artifact chain and tool reliability.

**What it can do**
- literature triage,
- draft hypotheses,
- propose model/run specs,
- execute only low-cost bounded runs,
- draft decision memos.

**What it cannot do**
- self-approve,
- mutate ontology,
- run expensive sweeps autonomously,
- manage portfolio-level autonomy.

**Exit criteria**
- schema compliance > 90%
- tool success > 85%
- accepted memos mostly citation-complete
- researchers prefer it over ad hoc manual assembly

## 14.2 V2 — Bounded Workflow Graph

**Shape**  
Supervisor plus scoped workers with explicit contracts, persistent traces, approval interrupts, and durable state.

**Purpose**  
Handle parallelizable research operations without losing control.

**Additions**
- explicit workflow graph,
- resumable execution,
- contradiction service,
- budget-aware run scheduling,
- stronger audit layer.

**Exit criteria**
- low duplicate branch generation,
- consistent synthesis across repeated runs,
- recovery from tool failure without silent corruption,
- visible contradiction management.

## 14.3 V3 — Portfolio-Level Research Ops

**Shape**  
Controlled long-horizon automation for literature watch, queue management, reranking, and program-level summaries.

**Purpose**  
Provide bounded program support without pretending to be an autonomous laboratory or business.

**Capabilities**
- scheduled literature monitoring,
- portfolio reranking suggestions,
- recurring decision memo generation,
- queue shaping under cost caps.

**Still prohibited**
- autonomous strategy commitment,
- uncontrolled external actions,
- uncontrolled spawning,
- unrestricted memory mutation.

---

## 15. Implementation Roadmap

### Phase 0 — Foundations

Deliver:
- artifact schemas,
- tool contracts,
- trace store,
- policy file,
- basic workflow definitions.

Do not:
- add multiple agents yet,
- add persistent autonomy yet.

### Phase 1 — Single-agent stable loop

Deliver:
- QDP Supervisor,
- literature and retrieval tools,
- schema validator,
- low-cost run submission,
- skeptic pass,
- decision memo drafting.

Exit when:
- the artifact chain is stable and auditable.

### Phase 2 — Governed parallelism

Deliver:
- worker contracts,
- approval router,
- contradiction graph,
- durable execution / checkpoints,
- budget controller,
- evaluator dashboards.

Exit when:
- the system can branch without losing coherence.

### Phase 3 — Program-level bounded autonomy

Deliver:
- portfolio governor,
- scheduled watch loops,
- queue optimisation,
- review cadence automation,
- stronger retention and governance policy.

Exit when:
- long-horizon runs remain controllable, auditable, and useful.

---

## 16. Failure Taxonomy and Mitigations

### 16.1 Common failure classes

1. **Context pollution**  
   Irrelevant history contaminates current judgment.

2. **Spec drift**  
   ModelSpec, RunSpec, and DecisionMemo stop referring to the same actual problem.

3. **False convergence**  
   Results appear stable but are methodologically weak.

4. **Uncited claims**  
   Narrative outruns evidence.

5. **Recursive spawning**  
   Supervisor creates work faster than it closes work.

6. **Permission leakage**  
   Child agents inherit tools they should not have.

7. **Ontology drift**  
   Canonical terms mutate silently.

8. **Duplicate execution**  
   Similar runs are launched because state lookup is weak.

9. **Synthesis mismatch**  
   Final memo misrepresents branch outputs.

10. **Theatrical certainty**  
    The model speaks as though a contested claim is settled.

### 16.2 Standard mitigations

- shallow delegation,
- typed contracts,
- schema validation,
- contradiction service,
- mandatory provenance,
- approval checkpoints,
- budget ceilings,
- trace review,
- replayable workflows,
- human final acceptance on consequential outputs.

---

## 17. Repo Integration Guidance

Recommended insertion paths:

```text
docs/
  agentic_research_framework.md
  roadmap.md

schemas/
  hypothesis_card.schema.json
  model_spec.schema.json
  noise_spec.schema.json
  run_spec.schema.json
  result_record.schema.json
  claim_ledger_entry.schema.json
  contradiction_issue.schema.json
  decision_memo.schema.json

policies/
  agent_governance.yaml

workflows/
  qdp_workflow_spec.yaml

contracts/
  tool_contract_template.yaml

prompts/
  supervisor_system_prompt.md
  skeptic_system_prompt.md

evals/
  acceptance_matrix.yaml
```

### 17.1 Insertion order

1. Insert schemas first.
2. Insert governance policy second.
3. Insert workflow specification third.
4. Insert prompts fourth.
5. Wire tool adapters and validators.
6. Run in shadow mode before live internal use.

---

## 18. Operating Rules That Should Not Be Relaxed Early

- No unrestricted agent spawning.
- No direct write access to canonical memory without validation.
- No external actions by default.
- No acceptance of claims without evidence links.
- No expensive compute without cost-aware approval.
- No merging of proposal, validation, and approval into one role.
- No reliance on raw chat logs as ground truth.
- No portfolio-level autonomy before single-loop reliability.

---

## 19. Minimal Definition of “Good Enough”

The system is good enough for internal reliance when:

- a researcher can inspect how a conclusion was reached,
- duplicate work is measurably reduced,
- contradictions surface earlier,
- the system’s uncertainty is legible,
- reruns are recoverable,
- failures are easier to debug than the manual process they replace.

If those conditions are not true, the system is still a demo.

---

## 20. Final Position

This project should be built as a **governed agentic research stack**, not as a speculative autonomy narrative.

The central product is not “an intelligent agent.”  
The central product is a **reliable delegation architecture** composed of:

- bounded agents,
- typed artifacts,
- explicit memory policy,
- approval routing,
- contradiction handling,
- traceability,
- workflow-level evaluation.

That is the framework worth putting into the project files.

---

## Appendix A — Recommended first live loop

Use this as the first production-grade loop:

```text
Question intake
    -> literature retrieval
    -> hypothesis drafting
    -> model/run spec drafting
    -> low-cost run submission
    -> result ingestion
    -> audit pass
    -> skeptic pass
    -> decision memo draft
    -> human review
    -> canonical write
```

This loop is narrow enough to debug and broad enough to prove value.

---

## Appendix B — Required review owners

At minimum assign named owners for:
- scientific review,
- ontology / vocabulary control,
- workflow operations,
- tool / runtime maintenance,
- evaluation and regression review,
- security / access policy.

If ownership is vague, the system will silently rot.
