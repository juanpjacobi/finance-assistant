---
name: openapi-spec-reader
description: Read, parse and deeply understand an OpenAPI 3.x spec file before any code generation, test writing, or API integration task. Use this skill whenever a task involves an OpenAPI/Swagger YAML or JSON file. Triggers include: "read the spec", "understand the API", "parse the openapi", "analyze the contract", or when another skill (like openapi-test-writer or openapi-code-generator) requires spec context as input.
---

This skill parses an OpenAPI 3.x specification file and produces a structured understanding of the API contract. Its output is used as input by other skills (test writer, code generator, documentation generator).

The user provides a path to an OpenAPI YAML or JSON file. Parse it completely before producing any output.

## Input

```
SPEC_PATH: path/to/openapi.yaml
```

## Parsing Strategy

### 1. Read the file

```bash
cat $SPEC_PATH
```

If the file is large (>500 lines), read it in sections:
```bash
head -100 $SPEC_PATH        # info, servers, tags
grep -n "operationId" $SPEC_PATH  # list all operations
```

### 2. Extract global metadata

From the `info` block:
- `title` — API name
- `version` — API version
- `description` — purpose

From `servers`:
- base URLs per environment

From `tags`:
- logical groupings of endpoints

### 3. Extract components

From `components/schemas`:
- For each schema: name, required fields, field types, enums, nullable fields, nested refs
- Note: `$ref` values point to reusable schemas

From `components/responses`:
- Reusable response definitions (e.g. NotFound, UnprocessableEntity)
- Content type (e.g. `application/problem+json` signals RFC 9457 error format)

### 4. Extract operations

For each path and method in `paths`:

```
operationId   → unique name (used as function/test name)
method        → GET POST PUT DELETE PATCH
path          → URL pattern (note {param} variables)
tags          → which group this belongs to
summary       → short description
description   → detailed description
parameters    → path, query, header params with types and required flag
requestBody   → schema ref or inline schema, required flag
responses     → status codes with schema refs
```

### 5. Identify design patterns

Look for:
- **Error format**: if responses use `application/problem+json` → RFC 9457
- **Auth**: if `securitySchemes` defined → note type (bearer, apiKey, oauth2)
- **Pagination**: if list endpoints have `page`/`limit`/`offset` params
- **Soft delete**: if schemas have `deleted_at` or `is_deleted` fields
- **Versioning**: if paths start with `/v1/`, `/v2/` etc.

### 6. Detect constraints and edge cases

For each operation, note:
- Required vs optional parameters
- Enum values that restrict inputs
- Nullable fields
- Default values mentioned in descriptions
- Business rules mentioned in descriptions (e.g. "fails if transactions assigned")

## Output Format

Produce a structured summary in this exact format:

```
## API: {title} v{version}
{description}

Base URL: {server url}

## Schemas
{for each schema}
### {SchemaName}
Required: {field list}
Optional: {field list}
Enums: {field}: [{values}]
Notes: {any constraints from descriptions}

## Operations
{for each operation grouped by tag}
### {tag}

**{operationId}** {METHOD} {path}
- Summary: {summary}
- Params: {param name} ({type}, {required|optional}) — {description}
- Body: {schema name or inline description}
- Returns: {status}: {schema} | {status}: {error schema}
- Notes: {business rules, edge cases, defaults}

## Design Patterns
- Error format: {RFC 9457 | generic JSON | none detected}
- Auth: {type | none}
- Pagination: {yes | no}
- Versioning: {yes | no}

## Edge Cases & Business Rules
{numbered list of all constraints found in descriptions}
```

## Rules

- Never assume field types — read them from the spec
- Never skip `$ref` resolution — follow refs to their definitions
- If a description mentions a business rule (e.g. "defaults to today", "fails if assigned"), include it in Edge Cases
- If the spec is incomplete or ambiguous, flag it explicitly
- This skill produces no code — only structured understanding