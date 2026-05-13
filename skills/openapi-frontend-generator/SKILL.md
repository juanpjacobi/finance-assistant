---
name: openapi-frontend-generator
description: Generate TypeScript types, API client functions, and Next.js pages from an OpenAPI 3.x spec. Use this skill when asked to generate frontend code from a spec. Always run openapi-spec-reader first. Triggers include: "generate frontend", "create the UI", "generate types from spec", "write the frontend".
---

This skill generates a complete typed frontend for a Next.js (App Router) project from an OpenAPI spec. It produces TypeScript types, an API client, and basic page components — all derived from the spec's schemas and operationIds.

## Prerequisites

openapi-spec-reader must have been run first.

## Inputs

```
SPEC_PATH:       spec/openapi.yaml           (required)
FRONTEND_PATH:   ../finance-assistant-frontend  (required — path to Next.js project)
API_BASE_URL:    http://localhost:8000        (required — backend URL)
```

## Step 1 — Read the frontend project structure

```bash
ls $FRONTEND_PATH/src/
ls $FRONTEND_PATH/src/app/
```

Understand what already exists before generating anything.

## Step 2 — Generate TypeScript types

Create `$FRONTEND_PATH/src/lib/types.ts` from `components/schemas` in the spec.

Rules:
- One TypeScript interface per schema
- Use `number` for `integer` and `float`
- Use `string` for `date`, `date-time`, `uri`
- Nullable fields become `field: type | null`
- Optional fields become `field?: type`
- Enum values become TypeScript string literal unions
- Never use `any`

Example output:
```typescript
export interface Category {
  id: number
  name: string
  description: string | null
}

export type TransactionType = 'income' | 'expense'

export interface Transaction {
  id: number
  amount: number
  type: TransactionType
  date: string
  description: string | null
  category_id: number
  created_at: string
}
```

## Step 3 — Generate API client

Create `$FRONTEND_PATH/src/lib/api.ts`.

Rules:
- One function per operationId
- Function name = operationId (camelCase, matches spec exactly)
- Each function is async, typed with the correct response type from the spec
- Uses native `fetch` — no axios or other libraries
- Base URL comes from `process.env.NEXT_PUBLIC_API_URL`
- For list endpoints: return `Promise<Type[]>`
- For single resource endpoints: return `Promise<Type>`
- For DELETE (204): return `Promise<void>`
- For POST/PUT: accept a typed body parameter

Example output:
```typescript
const BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export async function listCategories(): Promise<Category[]> {
  const res = await fetch(`${BASE}/categories`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function createCategory(body: { name: string; description?: string | null }): Promise<Category> {
  const res = await fetch(`${BASE}/categories`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function deleteCategory(id: number): Promise<void> {
  const res = await fetch(`${BASE}/categories/${id}`, { method: 'DELETE' })
  if (!res.ok) throw new Error(await res.text())
}
```

## Step 4 — Generate .env.local

Create `$FRONTEND_PATH/.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Step 5 — Generate pages

For each tag in the spec, create a route in `$FRONTEND_PATH/src/app/{tag}/page.tsx`.

Each page must:
- Be a Server Component (no `'use client'`) — fetch data server-side
- Call the relevant `list*` function from `api.ts`
- Render a simple table or list of the resources
- Link to individual resource pages where relevant
- Use Tailwind classes for basic styling

Example structure:
```tsx
import { listCategories } from '@/lib/api'
import { Category } from '@/lib/types'

export default async function CategoriesPage() {
  const categories = await listCategories()

  return (
    <main className="p-8">
      <h1 className="text-2xl font-bold mb-4">Categories</h1>
      <table className="w-full border-collapse">
        <thead>
          <tr className="border-b">
            <th className="text-left p-2">ID</th>
            <th className="text-left p-2">Name</th>
            <th className="text-left p-2">Description</th>
          </tr>
        </thead>
        <tbody>
          {categories.map((c) => (
            <tr key={c.id} className="border-b hover:bg-gray-50">
              <td className="p-2">{c.id}</td>
              <td className="p-2">{c.name}</td>
              <td className="p-2">{c.description ?? '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  )
}
```

## Step 6 — Update root layout

Update `$FRONTEND_PATH/src/app/layout.tsx` to add a navigation bar with links to each tag's page.

## Step 7 — Verify types only

```bash
cd $FRONTEND_PATH && npx tsc --noEmit 2>&1
```

Fix any TypeScript errors before reporting done. Do NOT run `npm run build` — it is too slow for this step.

## Rules

- Never use `any` — every variable must be typed
- Function names must match operationIds exactly — this is the contract between spec and frontend
- Server Components by default — only add `'use client'` when strictly necessary (forms, interactivity)
- Keep pages minimal — this skill generates the skeleton, not the final UI
- If the spec changes, regenerate `types.ts` and `api.ts` completely — do not patch

## React 19 rules

- Do NOT use `React.FormEvent<HTMLFormElement>` — deprecated in React 19
- For form submit handlers, type the event as `{ preventDefault(): void }` — minimal and correct
- Example: `async function handleSubmit(e: { preventDefault(): void }) { e.preventDefault() ... }`

## Server / Client Component boundary

- Server Components CANNOT pass functions as props to Client Components — functions are not serializable
- For delete buttons and similar interactive components, pass only serializable data: `id: number`, `apiPath: string`
- The Client Component calls `fetch` directly using that data instead of receiving a callback
- Example: `<DeleteButton id={item.id} apiPath="/categories" />` — not `onDelete={() => deleteCategory(id)}`

## Error handling in Client Components

- Use `sweetalert2` for confirmations (replaces `window.confirm`) and error/success notifications
- Parse API errors properly — FastAPI wraps HTTPException in `{"detail": {...}}`:
  ```ts
  const body = await res.json()
  const detail = body?.detail
  const message = typeof detail === 'object' ? detail?.detail ?? detail?.title : detail
  ```
- Never use `window.alert` or `window.confirm` — always use sweetalert2

## Backend requirements

- FastAPI needs `CORSMiddleware` configured before the frontend can call it:
  ```python
  from fastapi.middleware.cors import CORSMiddleware
  app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"], allow_methods=["*"], allow_headers=["*"])
  ```
- Remind the user to add this if it's not already in `api/main.py`

## Mobile-first rules

- All layouts must work on mobile first, then scale up with `sm:` / `md:` prefixes
- Never use fixed widths without a `sm:` breakpoint fallback
- Tables must always be wrapped in `<div className="overflow-x-auto">` with a `min-w-*` on the table
- Grids start as `grid-cols-1` and scale to `sm:grid-cols-2` or more
- Padding/spacing: use `px-4 sm:px-8`, `py-6 sm:py-8` patterns
- Navigation must wrap gracefully on small screens — use `flex-col sm:flex-row` and `flex-wrap`
- Never use arbitrary values like `min-w-[600px]` — prefer Tailwind canonical classes (`min-w-150`)

## Dark mode rules

- Do NOT use CSS variables for colors in `globals.css` — they conflict with Tailwind's explicit color classes
- Do NOT add `@media (prefers-color-scheme: dark)` unless the design explicitly supports dark mode
- Keep `globals.css` minimal: only `@import "tailwindcss"` and `font-family` on body
- Use explicit Tailwind color classes (`text-slate-900`, `bg-white`) — never `text-foreground` or `bg-background`
