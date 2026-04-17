# Code Enhancer — Prompt Strategy

This document covers how prompts are structured, how the prompt router works,
and how to add or tune prompts without touching any service logic.

---

## Two-Layer Prompt Design

Every prompt sent to the AI is assembled from two layers:

```
┌─────────────────────────────────────────────────────────────────┐
│                        LAYER 1: SYSTEM PROMPT                   │
│                                                                 │
│  Generic, task-level instructions that apply to ALL requests    │
│  regardless of language or technology.                          │
│                                                                 │
│  Sets the AI's role, output format, quality standards,          │
│  and the ALREADY_OPTIMAL signal contract.                       │
└─────────────────────────────────────────────────────────────────┘
                              +
┌─────────────────────────────────────────────────────────────────┐
│                        LAYER 2: USER MESSAGE                    │
│                                                                 │
│  The actual request: code + language + context                  │
│  + technology-specific instructions (if technology provided)    │
└─────────────────────────────────────────────────────────────────┘
```

The assembled result is an OpenAI-format messages list:
```json
[
  { "role": "system", "content": "<SYSTEM_PROMPT>" },
  { "role": "user",   "content": "<USER_MESSAGE>" }
]
```

---

## Prompt Router

**File:** `api/ai/prompts/__init__.py`

The `PromptRouter` class selects the correct prompt file based on `task_type`
and assembles the final messages list.

```
task = "enhance"  →  enhance_prompt.py
task = "complete" →  complete_prompt.py
task = "generate" →  generate_prompt.py
```

Technology hints are injected into the user message when `technology` is provided:

```
User message = base_user_message
             + "\n\nTechnology context: " + TECHNOLOGY_HINTS[technology]
```

If `technology` is not in `TECHNOLOGY_HINTS`, the base message is used as-is —
no error, no crash.

---

## Task 1: Enhancement Prompt

**File:** `api/ai/prompts/enhance_prompt.py`

### Goal
Analyze the submitted code and return an improved version. If the code is already
optimal, return the `ALREADY_OPTIMAL` signal instead of fabricating changes.

### System Prompt Design

```
Role:
  You are an expert code reviewer and enhancer. Your job is to improve code quality,
  correctness, readability, and adherence to best practices.

Output rules:
  - Return ONLY valid JSON — no markdown, no explanation outside the JSON
  - If enhancements are needed, return the variants array
  - If code is already optimal, return the already_optimal signal
  - Every code block must be properly formatted and commented
  - Comments must explain WHY, not WHAT

Quality checklist applied to every enhancement:
  - Correct and complete logic
  - Proper naming (variables, functions, classes)
  - Type hints / type annotations where applicable
  - Docstrings / JSDoc / GoDoc on all public functions
  - Inline comments on non-obvious logic only
  - No dead code, no unused imports
  - Error handling where appropriate
  - No magic numbers — use named constants

ALREADY_OPTIMAL signal:
  When the submitted code already meets all quality standards, respond with:
  { "already_optimal": true, "notes": ["reason 1", "reason 2"] }
  Do NOT fabricate enhancements just to have something to return.

Output format (when enhancements exist):
  {
    "already_optimal": false,
    "variants": [
      {
        "title": "short descriptive title",
        "description": "what changed and why",
        "code": "the complete enhanced code"
      }
    ]
  }
```

### User Message Template

```
Language: {language}
{technology_hint}

Code to enhance:
{code}

{context_section}

Return {variants} variant(s).
```

---

## Task 2: Completion Prompt

**File:** `api/ai/prompts/complete_prompt.py`

### Goal
Complete partial or stub code. The user provides incomplete code (empty functions,
`pass` bodies, `TODO` comments) and optionally the full file as context. The AI
returns the best complete implementation.

### System Prompt Design

```
Role:
  You are an expert software engineer. Your job is to complete partial or stub code
  with the best possible implementation based on the function signature, docstring,
  surrounding context, and the technology being used.

Completion rules:
  - Infer intent from the function name, parameters, and any docstring or comments
  - Use the provided file context to understand data models, patterns, and conventions
    already in use — match them exactly
  - Do not change function signatures unless they are clearly wrong
  - Complete ALL stubs in the submitted code, not just the first one
  - Return the complete file/function, not just the filled-in parts

Quality standards: (same as enhancement — formatting, comments, type hints, etc.)

Output format:
  {
    "already_optimal": false,
    "variants": [
      {
        "title": "short descriptive title",
        "description": "implementation approach and key decisions",
        "code": "the complete implemented code"
      }
    ]
  }
```

### User Message Template

```
Language: {language}
{technology_hint}

Incomplete code to implement:
{code}

{context_section}

Return {variants} variant(s).
```

---

## Task 3: Generation Prompt

**File:** `api/ai/prompts/generate_prompt.py`

### Goal
Generate code from a natural language prompt. Returns code in one or more languages,
each as a separate JSON key. Every language entry has a title, description, and the code.

### System Prompt Design

```
Role:
  You are an expert polyglot software engineer. Your job is to generate production-ready
  code from a natural language description, in one or more programming languages.

Generation rules:
  - Generate complete, runnable code — not pseudocode or skeletons
  - Follow the idioms and conventions of each language strictly
  - Apply technology-specific patterns when a technology is specified
  - Every generated file must include necessary imports/dependencies
  - Add a file-level comment block explaining what the code does

Output format:
  Return a single JSON object where each key is a language name (lowercase).
  Each value is an object with title, description, and code.

  {
    "python": {
      "title": "descriptive title for this implementation",
      "description": "what this code does and any notable implementation decisions",
      "code": "the complete generated code"
    },
    "javascript": {
      "title": "...",
      "description": "...",
      "code": "..."
    }
  }

  Return ONLY the JSON object. No markdown. No explanation outside the JSON.
```

### User Message Template

```
Generate code for the following:

{prompt}

Languages: {languages_list}
{technology_hints_per_language}

Ensure each implementation follows the conventions and best practices of its language
and specified technology.
```

---

## Technology Hints

Technology hints are short, targeted instruction strings injected into the user message
when `technology` is provided. They tell the AI which ecosystem conventions to follow.

### Current Hints

```python
TECHNOLOGY_HINTS = {
    # Python ecosystem
    "fastapi":     "Use Pydantic v2 models, FastAPI dependency injection, proper HTTP status codes, and async functions.",
    "django":      "Follow Django ORM patterns, use class-based views where appropriate, respect Django's app structure.",
    "flask":       "Use Flask blueprints, proper error handlers, and Flask-SQLAlchemy patterns if DB is involved.",

    # JavaScript / TypeScript ecosystem
    "express":     "Use async/await throughout, proper Express error middleware (4-arg), no callback hell.",
    "nextjs":      "Use App Router conventions, server components by default, client components only when needed.",
    "react":       "Functional components only, proper hook usage, no prop drilling — use context or state management.",
    "nestjs":      "Use NestJS decorators, dependency injection, proper module structure, DTOs with class-validator.",

    # Go ecosystem
    "gin":         "Idiomatic Go error handling (return error, don't panic), context propagation, Gin middleware patterns.",
    "stdlib":      "Standard library Go patterns, proper error wrapping with fmt.Errorf, table-driven tests.",

    # Java ecosystem
    "spring-boot": "Use @Service/@Repository separation, constructor injection (not field injection), proper exception handling.",
    "quarkus":     "Use Quarkus CDI, reactive patterns where appropriate, MicroProfile annotations.",

    # Other
    "sqlalchemy":  "Use SQLAlchemy 2.0 style (select() statements), proper session management, avoid N+1 queries.",
    "prisma":      "Use Prisma client patterns, proper transaction handling, type-safe queries.",
}
```

### Adding a New Technology

Add one line to `TECHNOLOGY_HINTS` in the relevant prompt file (or in a shared
`technology_hints.py` if hints are shared across tasks):

```python
"your-technology": "Key conventions and patterns to follow for this technology.",
```

Zero impact on any other layer.

---

## ALREADY_OPTIMAL Contract

The `ALREADY_OPTIMAL` signal is a first-class part of the prompt contract, not an
afterthought. The system prompt explicitly instructs the AI:

1. Apply the quality checklist to the submitted code
2. If ALL checks pass → return `{ "already_optimal": true, "notes": [...] }`
3. If ANY check fails → return the variants array with fixes

The `ResponseParser` looks for `already_optimal: true` in the parsed JSON and sets
the response field accordingly. The route returns this to the client as-is.

This prevents the AI from fabricating unnecessary changes just to have something to
return — a common failure mode when this isn't explicitly instructed.

---

## Output Format Contract

All three tasks instruct the AI to return **only valid JSON** with no surrounding
markdown or explanation. The `ResponseParser` still strips code fences as a safety net
in case the AI wraps the JSON in backticks despite instructions.

The JSON structure is task-specific but all share:
- `already_optimal` boolean (enhance and complete tasks)
- `variants` array with `title`, `description`, `code` (enhance and complete)
- Language-keyed object with `title`, `description`, `code` (generate)

---

## Prompt Tuning Guidelines

When tuning prompts:

- Change the **system prompt** to adjust overall behavior, quality standards, or output format
- Change the **user message template** to adjust how the request is framed
- Change **TECHNOLOGY_HINTS** to adjust technology-specific behavior
- Never put business logic in prompts — keep routing logic in `PromptRouter`
- Test prompt changes with `TESTING=false` locally against the real API before committing
- The `MockAIProvider` in tests returns hardcoded responses — prompt changes don't affect test results
