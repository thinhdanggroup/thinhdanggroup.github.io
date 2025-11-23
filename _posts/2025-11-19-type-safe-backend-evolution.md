---
author:
    name: "Thinh Dang"
    avatar: "/assets/images/avatar.png"
    bio: "Experienced Fintech Software Engineer Driving High-Performance Solutions"
    location: "Viet Nam"
    email: "thinhdang206@gmail.com"
    links:
        - label: "Linkedin"
          icon: "fab fa-fw fa-linkedin"
          url: "https://www.linkedin.com/in/thinh-dang/"
toc: true
toc_sticky: true
header:
    overlay_image: /assets/images/type-safe-backend-evolution/banner.png
    overlay_filter: 0.5
    teaser: /assets/images/type-safe-backend-evolution/banner.png
title: "Untitled Blog Post"
tags:
    - typescript
    - zod
    - tRPC
---

You’re on call. It’s 2:13 AM.

A partner team pings you: “Your user API just started returning 500s when we deploy. We didn’t change anything.”

You did, though. Yesterday you refactored a handler, renamed a field, tweaked a type. TypeScript built fine. Unit tests passed. Your frontend monorepo is happy.

But someone else’s Go client, generated months ago from an old OpenAPI spec, is not happy at all.

That’s a **silent API break**: the backend evolved, the contract didn’t, and nothing screamed until production traffic did.

This post is about building a stack where:

* TypeScript catches mistakes **across the client/server boundary**.
* Your API contract is **generated from the same source of truth** as your runtime validation.
* Every change to that contract is **diffed and checked for breakage in CI**, ideally in a way that plays nicely with the upcoming **OpenAPI 4 “Moonwalk”** effort. ([OpenAPI Initiative][1])

We’ll get there with three tools:

* **tRPC** – end-to-end TypeScript RPC framework. ([trpc.io][2])
* **Zod** – TypeScript-first runtime schema validation & type inference. ([Zod][3])
* **OpenAPI 3.x now, 4 later** – the ubiquitous API contract format, currently at 3.2.0, with v4 “Moonwalk” under active design. ([OpenAPI Initiative Publications][4])

---

## 1. The Real Enemy: Silent API Breaks

APIs *want* to drift.

You start with:

```http
GET /users/{id}
{
  "id": "123",
  "name": "Ada Lovelace",
  "age": 29
}
```

A month later someone “just”:

* Renames `name` → `fullName`
* Makes `age` optional
* Adds `email` as required

TypeScript keeps compiling, because your backend code still type-checks. Your own frontend, which imports shared types from the backend, gets compile errors and you fix them. But:

* A Python client that deserializes `name` breaks at runtime.
* A mobile app compiled with an old model silently drops `email`.
* A partner’s codegen client still thinks `age` is required.

The core problem:

> Your **runtime contract** (what the API actually returns) and your **static types** (what your code thinks exists) drift apart over time.

And if you don’t have **automated contract diffing**, you only learn that after an outage.

We want a pipeline that makes it *hard* to accidentally change the contract without knowing:

1. Types break → TypeScript yells.
2. Payload shape breaks → Zod yells.
3. Contract changes → OpenAPI diff tools yell.

Let’s build that.

---

## 2. tRPC + Zod: End-to-End Type Safety Inside Your World

First, we fix type safety for **your own** TypeScript clients.

### 2.1 What tRPC brings to the table

tRPC is basically:

> “Call backend functions directly from the frontend, but with real HTTP under the hood and **no codegen** – just TypeScript inference.” ([trpc.io][2])

You define a router on the server:

```ts
// src/trpc/router.ts
import { initTRPC } from '@trpc/server';
import { z } from 'zod';

const t = initTRPC.create();

export const appRouter = t.router({
  getUser: t.procedure
    .input(
      z.object({
        id: z.string().uuid(),
      }),
    )
    .output(
      z.object({
        id: z.string().uuid(),
        name: z.string(),
        age: z.number().int().nonnegative(),
      }),
    )
    .query(async ({ input }) => {
      const user = await db.user.findById(input.id);
      // Zod will enforce this at runtime
      return user;
    }),
});

// Export type for client
export type AppRouter = typeof appRouter;
```

On the client:

```ts
// src/trpc/client.ts
import { createTRPCClient, httpBatchLink } from '@trpc/client';
import type { AppRouter } from '../trpc/router';

export const trpc = createTRPCClient<AppRouter>({
  links: [
    httpBatchLink({
      url: 'https://api.example.com/trpc',
    }),
  ],
});

// Usage
const user = await trpc.getUser.query({ id: 'uuid-string' });
// user has type: { id: string; name: string; age: number }
```

If you change the server’s `output()` schema, the client’s inferred type **changes automatically**. Any mismatched usage (`user.age.toFixed()` when you made `age` optional) fails at compile time.

### 2.2 Zod closes the runtime gap

Zod is a TypeScript-first validation library:

* You define schemas (`z.object({ ... })`).
* It validates data **at runtime**.
* It also infers the **TypeScript type** from the schema. ([Zod][3])

In tRPC, those `.input()` and `.output()` Zod schemas are used both for:

* **Runtime validation** of HTTP payloads.
* **Static typing** of client/server code.

So if your database returns `age: "29"` as a string by mistake, `.output()` validation fails before that bad shape leaks over the wire.

Inside a TypeScript monorepo, **tRPC + Zod virtually eliminate silent breaks**.

But that only helps if all your consumers are TypeScript and speak tRPC.

The real world… is not that kind.

---

## 3. Beyond the Monorepo: Why We Still Need OpenAPI

Once you have:

* Mobile apps
* Backend-to-backend integrations
* External partners
* Polyglot microservices

you need a **language-neutral** description of your API.

That’s what the **OpenAPI Specification (OAS)** gives you: a standard way to describe HTTP APIs – endpoints, parameters, schemas – so tools and humans can understand them without reading source code. ([OpenAPI Initiative Publications][4])

OpenAPI specs power:

* Documentation (Swagger UI, Redoc, etc.)
* Code generation (clients in Go, Java, Swift…)
* Contract testing & breaking change detection
* Governance & API catalogs

Currently, the spec is at **3.2.0** with widespread tooling support. ([OpenAPI Initiative Publications][4])

### 3.1 What about OpenAPI 4 “Moonwalk”?

OpenAPI 4 (code name **Moonwalk**) is the **next major revision** under active work by a dedicated SIG. The goals include: ([OpenAPI Initiative][1])

* Better **semantics** – making the meaning of operations clearer for humans *and* LLMs.
* More explicit **signatures** – ways to identify API operations from HTTP details.
* Cleaner **modularity & foundational interfaces** – easier for tooling authors.
* A focus on **mechanical upgrade** from 3.x → 4.0.

Crucially, the OpenAPI Initiative has emphasized that Moonwalk is an ongoing project and the timeline for a 4.0.0 release is still open-ended as of late 2025. ([OpenAPI Initiative][1])

So today, we’ll **generate OpenAPI 3.x** from tRPC/Zod, but design with 4 in mind (good semantics, stable operation signatures, etc.).

---

## 4. One Source of Truth: Zod Schemas → tRPC → OpenAPI

The dream is:

> “I define my models *once*, and they become:
> – runtime validation
> – TypeScript types
> – OpenAPI schemas
> – eventually OpenAPI 4-compatible contracts”

Zod is the obvious candidate for that “once”.

### 4.1 Designing Zod schemas as your domain model

Let’s start by extracting reusable Zod schemas:

```ts
// src/schemas/user.ts
import { z } from 'zod';

export const UserId = z.string().uuid();

export const User = z.object({
  id: UserId,
  name: z.string().min(1),
  age: z.number().int().nonnegative(),
  email: z.string().email().optional(),
});

export type User = z.infer<typeof User>;
```

This one module now backs:

* Validation in your handlers.
* TypeScript types.
* (Soon) OpenAPI schemas.

### 4.2 Wiring these schemas into tRPC

```ts
// src/trpc/router.ts
import { initTRPC } from '@trpc/server';
import { z } from 'zod';
import { UserId, User } from '../schemas/user';

const t = initTRPC.create();

export const appRouter = t.router({
  getUser: t.procedure
    .meta({
      // will be useful when generating OpenAPI
      openapi: {
        summary: 'Get a user by ID',
        path: '/users/{id}',
        method: 'GET',
        tags: ['Users'],
      },
    })
    .input(z.object({ id: UserId }))
    .output(User)
    .query(async ({ input }) => {
      const user = await db.user.findById(input.id);
      if (!user) {
        throw new Error('User not found');
      }
      return user;
    }),
});
```

We’ve already got:

* **End-to-end TS types** for our own clients.
* **Runtime validation** for inputs and outputs.

Next step is to let these same Zod schemas feed OpenAPI.

---

## 5. Generating OpenAPI from Zod

There are several libraries that take Zod schemas and generate OpenAPI:

* `zod-openapi` ([npm][5])
* `@anatine/zod-openapi` ([npm][6])
* `@asteasolutions/zod-to-openapi` ([GitHub][7])

They all follow the same idea:

> “Decorate Zod schemas and routes with a bit of metadata → generate a full OpenAPI document.”

Here’s an example using `zod-openapi`-style APIs (simplified):

```ts
// src/openapi.ts
import { OpenAPIRegistry, OpenApiGeneratorV3 } from '@asteasolutions/zod-to-openapi';
import { z } from 'zod';
import { User, UserId } from './schemas/user';

const registry = new OpenAPIRegistry();

// Describe your schemas
registry.register('User', User);
registry.register('UserId', UserId);

// Describe your route
registry.registerPath({
  method: 'get',
  path: '/users/{id}',
  tags: ['Users'],
  description: 'Get a user by ID',
  request: {
    params: z.object({
      id: UserId,
    }),
  },
  responses: {
    200: {
      description: 'User found',
      content: {
        'application/json': {
          schema: User,
        },
      },
    },
    404: {
      description: 'User not found',
    },
  },
});

// Generate spec
const generator = new OpenApiGeneratorV3(registry.definitions);

export const openApiDoc = generator.generateDocument({
  openapi: '3.1.0',
  info: {
    title: 'My Service',
    version: '1.0.0',
  },
  servers: [{ url: 'https://api.example.com' }],
});
```

You can then serialize `openApiDoc` to YAML/JSON at build time and ship it with your service or publish it centrally.

> Note: Today these generators target OpenAPI 3.x. Because 4 is meant to be mechanically upgradable from 3.x, investing in well-structured 3.x docs is still future-proof. ([OpenAPI Initiative][1])

---

## 6. Generating OpenAPI from tRPC Routers

Hand-registering every path is boring. tRPC already knows:

* The input and output types (via Zod).
* The URL shape (via your router setup / meta).
* The HTTP method you want to expose.

The ecosystem has created several bridges to generate OpenAPI from tRPC:

* `trpc-openapi` (original, now archived but widely used and forked) ([GitHub][8])
* `@dokploy/trpc-openapi` (maintained fork) ([GitHub][9])
* `trpc-to-openapi` ([npm][10])
* `openapi-trpc` / similar tools ([GitHub][11])

These typically work like:

1. Extend `initTRPC` with OpenAPI metadata type.
2. Annotate tRPC procedures with `meta.openapi`.
3. Run a generator that walks your router and emits a spec.

Sketch with `trpc-to-openapi`-style configuration:

```ts
// src/trpc/openapi.ts
import { initTRPC } from '@trpc/server';
import { OpenApiMeta } from 'trpc-to-openapi'; // or @dokploy/trpc-openapi
import { z } from 'zod';
import { User, UserId } from '../schemas/user';

const t = initTRPC.meta<OpenApiMeta>().create();

const publicProcedure = t.procedure;

export const appRouter = t.router({
  getUser: publicProcedure
    .meta({
      openapi: {
        method: 'GET',
        path: '/users/{id}',
        summary: 'Get a user by ID',
        tags: ['Users'],
      },
    })
    .input(
      z.object({
        id: UserId,
      }),
    )
    .output(User)
    .query(async ({ input }) => {
      return db.user.findByIdOrThrow(input.id);
    }),
});

// Later, in some build script:
import { generateOpenApiDocument } from 'trpc-to-openapi';

const openApiDoc = generateOpenApiDocument(appRouter, {
  title: 'My Service',
  version: '1.2.3',
  baseUrl: 'https://api.example.com',
});
```

Now your **tRPC router is the single source of truth**, and the OpenAPI spec is derived from it.

This plays extremely well with Moonwalk’s goals of semantics, signatures, and mechanical upgrading: you already attach explicit summaries, tags, and paths that can later map into richer 4.0 structures. ([OpenAPI Initiative][1])

---

## 7. Preventing Silent Breaks with OpenAPI Diff in CI

So far, we have:

* tRPC + Zod: **type-safe implementation** and **type-safe TypeScript clients**.
* OpenAPI 3.x generated from the same source of truth.

Now we need to stop a developer from casually committing a breaking change and merging it.

### 7.1 Breaking-change detectors for OpenAPI

There’s a small ecosystem of tools that compare two OpenAPI specs and classify changes as **breaking** or **non-breaking**:

* **oasdiff** – diff, changelog, and breaking change detection; has a GitHub Action. ([OASDiff][12])
* **openapi-changes** – pb33f’s “world’s sexiest OpenAPI breaking change detector,” used as a general diff & changelog engine. ([pb33f.io][13])
* **openapi-diff** – libraries and CLIs from Azure and OpenAPITools used to detect breaking changes in large-scale API ecosystems. ([GitHub][14])

Under the hood, these tools:

* Parse both specs into an internal model.
* Compare operations, parameters, schemas.
* Tag changes as **added / removed / modified** and **breaking / non-breaking**. ([pb33f.io][15])

For example:

* **Breaking**: removing a path, changing a response type, making a required field missing or more restrictive.
* **Non-breaking**: adding a new optional field, adding an endpoint, relaxing a constraint.

### 7.2 Example: CI check with oasdiff

Let’s say your build produces `openapi.yaml`. You keep the last released spec in `openapi-baseline.yaml`.

A GitHub Actions workflow might look like:

```yaml
name: API Contract Check

on:
  pull_request:
    paths:
      - 'src/**'
      - 'openapi/**'

jobs:
  openapi-diff:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Install deps
        run: npm ci

      - name: Build OpenAPI spec
        run: npm run generate:openapi  # writes to openapi/current.yaml

      - name: Check for breaking changes
        uses: oasdiff/oasdiff-action@main
        with:
          base: openapi/baseline.yaml
          revision: openapi/current.yaml
          # Only fail on breaking changes
          additional-args: '--format text --breaking-only'
```

If someone changes `User.age` from `number` to `string`, or removes a field marked as required in the previous spec, the action fails and surfaces a human-readable report.

No more “oops we broke the mobile app in prod but TypeScript was fine.”

---

## 8. A Concrete Refactor Walkthrough

Let’s put the whole pipeline together with a small evolution story.

### 8.1 v1: Simple user model

Your Zod schema:

```ts
export const User = z.object({
  id: UserId,
  name: z.string(),
  age: z.number().int().nonnegative(),
});
```

Your tRPC procedure outputs `User`. You generate `openapi-v1.yaml` from tRPC.

### 8.2 Refactor: add emails, make age optional

Product decides:

* `age` should be optional (users can skip it).
* `email` should be required.

You change the schema:

```ts
export const User = z.object({
  id: UserId,
  name: z.string(),
  age: z.number().int().nonnegative().optional(),   // changed
  email: z.string().email(),                        // new, required
});
```

#### What happens?

1. **tRPC + TypeScript**

   Anywhere in your TS code that assumed `user.age: number` now sees `user.age: number | undefined` and fails to compile until you handle the optional case.

2. **Zod runtime validation**

   If some legacy record in the DB is missing `email`, Zod will throw on output, and you’ll discover that before it silently leaks incorrect shapes to consumers.

3. **OpenAPI diff**

   You regenerate `openapi-v2.yaml`.

   * oasdiff / openapi-changes compares v1 vs v2.
   * It sees that:

     * `age` became optional → typically **non-breaking** for clients (they can ignore it).
     * `email` is a new **required** response property → **potentially breaking**, because existing clients might not expect or handle it depending on your rules.

   Your CI policy might say:

   * “Required response fields added = breaking → major version bump or feature flag.”

   So the PR fails until you either:

   * Make `email` optional initially, or
   * Introduce a v2 endpoint or new versioned schema.

The result: **you can’t accidentally slide a contract-breaking change into main**. You must either:

* Explicitly version it.
* Explicitly loosen it.
* Or explicitly accept the breaking change and update the baseline spec.

---

## 9. Preparing for OpenAPI 4 (Without Waiting for It)

Moonwalk’s design principles – semantics, signatures, mechanical upgrade – reward teams that already treat their OpenAPI docs as **structured, semantically rich contracts**. ([OpenAPI Initiative][1])

The tRPC + Zod + OpenAPI stack helps you get there:

* **Semantics**
  You already attach meaningful `summary`, `description`, `tags`, and well-named schemas when generating from Zod/tRPC. That metadata is useful today and will be even more useful for LLM-driven tooling tomorrow.

* **Signatures**
  Explicit path + method + operationId in generated specs give each operation a stable identity, which aligns with Moonwalk’s focus on signatures as a first-class concept.

* **Mechanical upgrade**
  Because your OpenAPI documents are machine-generated with consistent patterns, automated 3.x → 4.x migration tools (one of Moonwalk’s goals) have an easier job. ([OpenAPI Initiative][1])

Meanwhile, diff tools like `openapi-changes` and `oasdiff` already support multiple OpenAPI versions and Swagger 2.0, and are likely to support 4.x as it stabilizes. ([GitHub][16])

You don’t need to wait for the 4.0.0 badge to start evolving safely.

---

## 10. A Practical Adoption Checklist

If you want to move towards **type-safe backend evolution** with this stack, here’s a pragmatic path:

1. **Introduce Zod for validation**

   * Start with one endpoint.
   * Replace ad-hoc checks with Zod schemas.
   * Export `z.infer<typeof Schema>` to use in your TypeScript types.

2. **Adopt tRPC where it makes sense**

   * Ideal for monorepo full-stack apps (Next.js, Remix, etc.). ([trpc.io][2])
   * Define routers using your existing Zod schemas.
   * Swap your frontend’s manual fetch calls for `trpcClient.procedure.query(...)`.

3. **Generate an OpenAPI 3.x spec**

   * Choose a **Zod → OpenAPI** library (`zod-openapi`, `@anatine/zod-openapi`, `zod-to-openapi`) or **tRPC → OpenAPI** bridge (`trpc-to-openapi`, `@dokploy/trpc-openapi`). ([GitHub][17])
   * Wire it into your build: `npm run generate:openapi`.
   * Publish the spec where other teams & tools can see it.

4. **Add OpenAPI diff to CI**

   * Pick a diff tool (e.g., `oasdiff` or `openapi-changes`). ([OASDiff][12])
   * Keep a baseline spec (last release).
   * Fail the pipeline on breaking changes.

5. **Gradually tighten rules**

   * Start by just **reporting** changes.
   * Later, fail on high-risk breaking changes (field removals, required → optional flips, etc.).
   * Finally, enforce a policy: “No breaking change without explicit versioning plan.”

6. **Add good semantics today**

   * Consistent tags, readable summaries, helpful descriptions.
   * Stable operation IDs for all endpoints.
   * These pay off now (docs & codegen) and later (LLM tooling, OpenAPI 4).

---

## 11. Key Takeaways & Further Reading

* **End-to-end type safety (tRPC + Zod)** eliminates a whole class of bugs by letting TypeScript infer types across the network boundary and validate payloads at runtime. ([trpc.io][2])
* **OpenAPI 3.x** is still the lingua franca for cross-language API contracts, and the path to **OpenAPI 4 “Moonwalk”** runs right through well-structured 3.x docs. ([OpenAPI Initiative Publications][4])
* Generating OpenAPI directly from Zod/tRPC makes your **code the canonical contract**, not some stale YAML file.
* Adding OpenAPI diff tools like `oasdiff` or `openapi-changes` to CI means **no more silent contract drift** – every breaking change becomes a deliberate choice. ([OASDiff][12])

If you want to dig deeper:

* tRPC docs (for v11) – how to structure routers, adapters, and clients. ([trpc.io][2])
* Zod docs – advanced schemas, transforms, and JSON Schema integration. ([Zod][3])
* `zod-openapi`, `zod-to-openapi`, and `trpc-to-openapi` READMEs – concrete generation examples. ([GitHub][17])
* OpenAPI “Moonwalk” SIG pages and blog posts – to understand where 4.0 is heading and why semantics & signatures matter. ([OpenAPI Initiative][1])

If your team maintains even a single non-trivial API, investing in this pipeline is one of those rare moves that **improves developer experience, reliability, and future-proofing at the same time**.

And ideally, it keeps you from debugging contract drift at 2:13 AM.

[1]: https://www.openapis.org/blog/2025/02/05/moonwalk-2025-update "Moonwalk – 2025 update – OpenAPI Initiative"
[2]: https://trpc.io/ "tRPC - Move Fast and Break Nothing. End-to-end typesafe APIs made easy. | tRPC"
[3]: https://zod.dev/?utm_source=chatgpt.com "Intro | Zod"
[4]: https://spec.openapis.org/oas/?utm_source=chatgpt.com "OpenAPI Specification | OpenAPI Initiative Publications"
[5]: https://www.npmjs.com/package/zod-openapi?utm_source=chatgpt.com "zod-openapi - npm"
[6]: https://www.npmjs.com/package/%40anatine/zod-openapi?utm_source=chatgpt.com "@anatine/zod-openapi - npm"
[7]: https://github.com/asteasolutions/zod-to-openapi?utm_source=chatgpt.com "GitHub - asteasolutions/zod-to-openapi: A library that generates ..."
[8]: https://github.com/trpc/trpc-openapi?utm_source=chatgpt.com "GitHub - trpc/trpc-openapi: OpenAPI support for tRPC"
[9]: https://github.com/Dokploy/trpc-openapi?utm_source=chatgpt.com "GitHub - Dokploy/trpc-openapi"
[10]: https://www.npmjs.com/package/trpc-to-openapi?utm_source=chatgpt.com "trpc-to-openapi - npm"
[11]: https://github.com/dtinth/openapi-trpc?utm_source=chatgpt.com "GitHub - dtinth/openapi-trpc: Generate OpenAPI v3 document from a tRPC ..."
[12]: https://www.oasdiff.com/?utm_source=chatgpt.com "oasdiff - OpenAPI Specification Comparison Tool"
[13]: https://pb33f.io/openapi-changes/?utm_source=chatgpt.com "openapi-changes: the world's sexiest OpenAPI breaking change detector"
[14]: https://github.com/Azure/openapi-diff?utm_source=chatgpt.com "GitHub - Azure/openapi-diff: Command line tool to detect breaking ..."
[15]: https://pb33f.io/libopenapi/what-changed/?utm_source=chatgpt.com "pb33f.io: OpenAPI change detection"
[16]: https://github.com/pb33f/openapi-changes/releases?utm_source=chatgpt.com "Releases: pb33f/openapi-changes - GitHub"
[17]: https://github.com/samchungy/zod-openapi?utm_source=chatgpt.com "GitHub - samchungy/zod-openapi: Use Zod Schemas to create OpenAPI v3.x ..."
