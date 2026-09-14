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
    overlay_image: /assets/images/zero-config-backend-rikta/banner.webp
    og_image: /assets/images/zero-config-backend-rikta/og.jpg
    overlay_filter: 0.5
    teaser: /assets/images/zero-config-backend-rikta/teaser.webp
title: "Zero-Config Backends: The Architectural Future of TypeScript Frameworks"
tags:
    - Web Development
    - TypeScript
categories:
    - web-development
description: "How TypeScript backends are moving from explicit module wiring to build-time inference, and what zero-config actually means in practice."
last_modified_at: 2026-01-12
---
There’s a particular kind of frustration that only backend engineers know: you wrote the controller, you wrote the service, the types look great, the tests compile… and then your framework refuses to boot because you forgot to add one class name to one array in one module.

That array is *always* an array.
It’s *always* nested two directories away from where you were working.
And it *always* looks like a CVS receipt by the time your app hits 20 features.

For years, TypeScript backends have swung between two poles:

* **“Just Express it”**: maximum freedom, minimum structure, and a lot of “wait, where do we wire this?”
* **“Enterprise framework”**: batteries included, incredible capabilities, and a configuration surface area that grows faster than your feature count.

Now a new wave of frameworks (Rikta is an interesting current example) is trying to move the middle: keep structure and productivity, but **delete the ceremony**. Not by doing less, but by **inferring more**. ([Rikta][1])

This post is a deep dive into that shift: how “dependency injection + decorators + build-time metadata” got us where we are, what “zero-config” actually means in practice, and why the next generation of TypeScript backends is leaning into runtime inference, conventions, and manifest-style bootstrapping.

---

## The thing NestJS got right: architecture is a feature

Let’s start by giving credit where it’s due.

Frameworks like NestJS popularized a genuinely valuable idea: **backend systems scale better when architecture is explicit**.

* Controllers handle routing
* Providers/services encapsulate logic
* Modules define boundaries, share providers, and make dependencies visible
* A DI container builds and manages a dependency graph

That’s not just “enterprise fluff.” It’s a strategy for building systems that survive their second year. Nest’s module system is explicit about what a module provides (`providers`), what it exposes (`exports`), and what it depends on (`imports`). ([NestJS Documentation][2])

In NestJS, even a “simple” feature tends to look like:

```ts
// cats.module.ts (NestJS)
import { Module } from "@nestjs/common";
import { CatsController } from "./cats.controller";
import { CatsService } from "./cats.service";

@Module({
  controllers: [CatsController],
  providers: [CatsService],
  exports: [CatsService],
})
export class CatsModule {}
```

That explicit wiring is *the point*: it prevents accidental coupling and makes dependencies visible. Nest’s docs explicitly call out that exporting providers is how other modules gain access to shared instances. ([NestJS Documentation][2])

**Section takeaway:** NestJS’s “complexity” is largely the cost of making architecture explicit and enforceable.

---

## The thing NestJS made painful: your dependency graph is written twice

Here’s the rub: in many TS backends, you define your system in *two parallel representations*:

1. **The code you actually run** (controllers, services, functions)
2. **The registration graph** (modules, providers arrays, exports/imports)

And the registration graph is typically redundant. The controller already imports the service. The service already imports the repository. Your editor already knows this. TypeScript already knows this. But your runtime container doesn’t—so you tell it again.

Nest itself describes the “three key steps” in DI as: mark provider, request injection, then register provider with the module/container. ([NestJS Documentation][3])

That third step is where the “why do I have to keep doing this?” energy comes from.

It’s not just busywork. The duplication has consequences:

* **Refactors require updating “lists of things”** far from the code being changed
* **Circularity shows up at the module layer**, even when the underlying code is fine
* **Tooling has to model framework concepts** (modules/providers/exports), not just TypeScript code

If you’ve ever spent time tracking down “why isn’t this injectable?” and the fix was “it’s not exported from the module,” you’ve felt this pain in your bones. ([NestJS Documentation][2])

**Section takeaway:** The module graph is valuable, but hand-maintaining it is the part that feels outdated.

---

## The hidden dependency: decorators + metadata are doing more work than you think

A lot of TS backend frameworks lean on a specific stack of mechanics:

* **Decorators** to annotate classes/methods/parameters
* **Metadata reflection** to read those annotations at runtime
* **Compiler-emitted type metadata** (optional) to infer types for DI/validation/etc.

TypeScript’s `emitDecoratorMetadata` option exists specifically to emit extra runtime metadata for decorators, and it’s commonly used with the `reflect-metadata` library. ([TypeScript][4])

When you enable it, TypeScript emits metadata such as:

* `design:type`
* `design:paramtypes`
* `design:returntype`

This is incredibly powerful. It’s also a little… *special*. You’ve now coupled your runtime behavior to a TypeScript-specific emit mode.

A great way to understand why this matters is to look at what TypeScript itself says about decorators:

* `experimentalDecorators` enables a **legacy decorator implementation** that predates the eventual JS standard. ([TypeScript][5])
* TypeScript 5.0 introduced support for **the newer Stage 3 decorators proposal**, but it’s *different*: it’s emitted differently, it’s not compatible with `emitDecoratorMetadata`, and it doesn’t allow parameter decorators. ([TypeScript][6])

That last clause is a big deal for backend frameworks, because parameter decorators are everywhere in the classic style:

```ts
@Get("/users/:id")
getUser(@Param("id") id: string) { /* ... */ }
```

If your framework architecture depends on parameter decorators and emitted metadata, you’re on the legacy decorators track for now. And that pushes architects to ask a question:

**What would it look like to get the same developer experience without depending on this decorator/metadata pipeline?**

That question is one of the forces behind “zero-config” design.

**Section takeaway:** The TypeScript decorator story is changing, and frameworks that depend heavily on legacy decorator metadata are feeling pressure to evolve. ([TypeScript][6])

---

## Zero-config doesn’t mean “no architecture.” It means “stop hand-wiring the obvious.”

“Zero-config” is an overloaded phrase. In practice, for backends, it usually means:

* **No manual registration for common cases**
* **Conventions over configuration**
* **A default project layout that the runtime understands**
* **Inference of wiring from code structure and runtime exports**

Importantly, it doesn’t mean you can’t configure things. It means:

> *The framework should only ask you for configuration when the code cannot be inferred safely.*

Rikta’s own positioning is blunt about this: it’s “born from frustration with complex module systems,” and wants “zero configuration by default”—specifically calling out eliminating `imports`, `exports`, and `providers` arrays. ([Rikta][1])

That’s a useful lens: **what configuration exists only because the framework runtime can’t see your program structure?** If we can make the runtime see it, we can delete that configuration.

**Section takeaway:** Zero-config is about deleting duplicated wiring, not deleting structure.

---

## Rikta as a case study: auto-discovery replaces modules, not DI

Rikta is interesting because it’s not “minimalist Express 2.0.” It keeps a familiar architectural shape—controllers, providers, decorators, DI container—while trying to remove the *manual module graph*.

### What it claims (in plain terms)

From Rikta’s docs:

* It uses **Fastify as the HTTP layer**. ([Rikta][1])
* It relies on **auto-discovery** instead of explicit module registration. ([Rikta][7])
* You decorate controllers/providers, and they’re **registered automatically**. ([Rikta][7])
* You point it at directories to scan via `autowired: ['./src']`. ([Rikta][7])
* It has a DI container with scopes and tokens, including property injection using `@Autowired()`. ([Rikta][8])

So it’s not “DI is dead.” It’s “DI should not require you to maintain a module graph by hand.”

### How “auto-discovery” works under the hood (conceptually)

Rikta’s docs describe the boot flow as a pipeline:

1. **Decoration phase**: decorators register classes in a global registry
2. **Bootstrap**: `Rikta.create()` discovers registered classes
3. **Resolution**: the DI container resolves dependencies
4. **Route registration**: controllers are scanned for route decorators and registered with Fastify ([Rikta][7])

That maps to a pretty understandable internal model:

```ts
// PSEUDO-CODE: what "auto-discovery" tends to look like
async function createApp({ autowiredDirs }: { autowiredDirs: string[] }) {
  // 1) Import every module in certain directories
  //    so decorators run and register things.
  for (const dir of autowiredDirs) {
    for (const file of glob(`${dir}/**/*.{ts,js}`)) {
      await import(file);
    }
  }

  // 2) Pull everything out of a registry.
  const controllers = Registry.getAllControllers();
  const providers = Registry.getAllProviders();

  // 3) Build a container graph once at startup.
  const container = new Container();
  container.registerAll(providers);
  container.resolveAll(); // pre-warm singletons, etc.

  // 4) Register routes with the HTTP engine.
  const fastify = makeFastify();
  for (const controller of controllers) {
    registerControllerRoutes(fastify, controller, container);
  }

  return fastify;
}
```

Notice what’s happening: instead of maintaining a curated module graph, you let **the filesystem + imports + decorators** “hydrate” a runtime registry, and you build the app from there.

That’s a different architectural center of gravity:

* NestJS: *“You declare the graph explicitly.”*
* Rikta: *“We’ll discover the graph if you follow conventions.”* ([NestJS Documentation][2])

And yes, this introduces new tradeoffs (we’ll get there).

**Section takeaway:** Rikta’s “zero-config” is mostly “zero module wiring”—the DI container and controller structure still exist, but they’re bootstrapped via discovery. ([Rikta][7])

---

## The real shift: from build-time reflection to runtime inference

Now we can zoom out.

The big architectural change isn’t “frameworks use fewer features.” It’s that they’re changing *where truth lives*.

### Old world: metadata is the source of truth

In decorator-heavy frameworks, your runtime behavior is effectively defined by:

* decorators attached to classes/methods/params
* metadata keys stored via reflection APIs
* possibly compiler-emitted type metadata (`emitDecoratorMetadata`) ([TypeScript][4])

This is powerful, but it’s also fragile:

* it depends on specific compiler settings
* it depends on legacy decorator behavior (for parameter decorators)
* it can be hard for bundlers/transpilers to support consistently ([TypeScript][6])

### New world: values are the source of truth

“Inference-driven” backends try to move truth into things that exist at runtime *as normal JavaScript values*:

* route tables are arrays/objects/functions
* schemas are runtime values (Zod, JSON Schema, etc.)
* wiring is inferred by exports/imports and conventions
* DI becomes optional or can be explicit only where needed

This is the heart of the “runtime inference” move: **make your runtime behavior depend on runtime values, not compiler-emitted metadata.**

**Section takeaway:** TypeScript types disappear at runtime; zero-config backends increasingly anchor behavior in runtime values and conventions instead of emitted metadata. ([TypeScript][4])

---

## Three concrete patterns replacing “decorators + reflection” in modern TS backends

Let’s make this practical. Here are three architecture patterns that show up in “zero-config” thinking.

### 1) Schema-first typing: define once, validate everywhere

Rikta explicitly markets “native Zod integration” where validation schemas infer TS types. ([Rikta][9])

This pattern is bigger than any one framework. The idea:

* A **schema object** is a runtime value.
* TypeScript can infer a static type from that schema.
* Your runtime uses the schema to validate inputs.
* No reflection required.

Example:

```ts
import { z } from "zod";

// Runtime value
const CreateUserBody = z.object({
  email: z.string().email(),
  name: z.string().min(1),
});

// Compile-time type inferred from runtime value
type CreateUserBody = z.infer<typeof CreateUserBody>;

export async function createUser(body: unknown) {
  // Runtime validation
  const parsed: CreateUserBody = CreateUserBody.parse(body);

  // Now you're operating on typed, validated data.
  return { id: "user_123", ...parsed };
}
```

You didn’t need `emitDecoratorMetadata`. You didn’t need parameter decorators. You didn’t need “DTO classes” whose only job is to be reflected upon.

You just needed a value.

**Mini-summary:** schema-first turns “types” into something your runtime can actually see.

---

### 2) “Export-based routing”: routes are discovered, not decorated

A different pattern is to avoid decorators entirely for routing:

* Each file exports handlers and metadata
* The framework discovers them via `import()` / directory scanning
* The router is built from exports

Conceptually:

```ts
// users.routes.ts
export const routes = [
  {
    method: "GET",
    path: "/users/:id",
    handler: async ({ params }) => ({ id: params.id }),
  },
];
```

Then the framework does:

```ts
for (const mod of discoveredModules) {
  if (mod.routes) register(mod.routes);
}
```

This is runtime inference at its cleanest:

* “If you export a thing with shape X, we treat it as a route.”

There’s no metadata reflection pipeline. There’s just JavaScript.

**Mini-summary:** export-based routing makes discovery mechanical and bundler-friendly.

---

### 3) Standard decorators are coming… but they change the game

It’s worth calling out: we’re not necessarily heading toward a decorator-free future.

TypeScript 5.0 introduced support for the newer decorators proposal (Stage 3), but it differs significantly from the legacy `experimentalDecorators` mode—especially around parameter decorators and compatibility with `emitDecoratorMetadata`. ([TypeScript][6])

TypeScript 5.2 also added support for the decorators metadata proposal, exposing metadata through `context.metadata` and backing it via `Symbol.metadata`. ([TypeScript][10])

That suggests a possible long-term direction:

* frameworks may adopt *standard* decorators and metadata storage
* frameworks that rely heavily on parameter decorators may need new APIs
* reflection might become more standardized, but the ergonomics may shift

In other words: some of the “runtime inference” trend is a reaction to the uncertainty and constraints around legacy decorators.

**Mini-summary:** even if decorators stay, the old “parameter decorators + emitDecoratorMetadata” stack is under pressure. ([TypeScript][6])

---

## The tradeoffs: zero-config is not free lunch (it’s just a different bill)

When you delete module wiring, you’re moving complexity, not eliminating it.

Here are the big tradeoffs you should expect.

### 1) Explicit boundaries vs. global availability

Nest’s module system forces boundaries: providers live in a module scope unless exported or made global. ([NestJS Documentation][2])

Rikta’s docs describe a “global providers” model where providers can be injected anywhere without explicit exports. ([Rikta][7])

That’s *great* for speed of development—and risky for long-lived architectures unless you add conventions:

* feature folders
* naming rules
* lint rules around imports
* “public API” index files per feature

You can absolutely build boundaries without modules. But the framework won’t enforce them for you by default.

### 2) Startup work: discovery costs time (unless you cache it)

Auto-discovery generally means some combination of:

* scanning directories
* importing modules for side effects
* building registries/graphs at runtime

Rikta’s benchmark docs include “startup time” as a measured metric and describe how it optimizes bootstrapping. ([Rikta][11])

That’s the right instinct: once you build a system around discovery, you start caring about cold-start costs, serverless packaging, and caching manifests.

The “future” version of auto-discovery often looks like:

* discovery in dev (fast iteration)
* emitted manifest in prod (fast boot)

### 3) Debuggability: “magic” needs visibility

When the framework is inferring wiring, you need tooling to answer:

* Why is this provider registered twice?
* Why wasn’t this controller discovered?
* What did the container actually resolve?

Nest advertises graph visualization via Devtools. ([NestJS Documentation][2])
Rikta surfaces a `Registry` API to inspect discovered controllers/providers. ([Rikta][8])

Zero-config frameworks live or die by how inspectable their “magic” is.

**Section takeaway:** zero-config improves ergonomics, but it raises the importance of conventions, startup strategy, and introspection tooling. ([NestJS Documentation][2])

---

## A practical mental model: “Your backend is a graph; stop writing the adjacency list.”

If you want one mental model to carry forward, it’s this:

> A backend framework’s primary job is to build a graph:
>
> * nodes: controllers/services/providers
> * edges: “A depends on B”
> * plus a route table that maps HTTP → handler

In classic DI frameworks, you write that graph explicitly (modules/providers/exports/imports).

In zero-config frameworks, you **describe nodes**, and the runtime infers edges and builds the graph for you—using conventions, exports, registries, schemas, and scanning.

That’s why this shift feels inevitable: your code already *contains* the graph. “Zero-config” is a bet that the runtime can reconstruct it reliably.

**Section takeaway:** the future isn’t “less architecture”—it’s “architecture reconstructed automatically from your code.”

---

## What this means for teams building TypeScript backends in 2026

If you’re building (or choosing) a TS backend framework today, here’s what I’d watch for:

### If you love NestJS

Nest’s architecture is still a great fit when you need:

* strict boundaries
* explicit module APIs
* lots of ecosystem integrations
* predictable patterns across a large team ([NestJS Documentation][2])

But keep an eye on:

* how it evolves with the changing decorator landscape ([TypeScript][6])
* how you manage the module graph (codegen, conventions, devtools)

### If you’re tempted by “zero-config”

Frameworks like Rikta are exploring a compelling middle ground:

* keep controllers/providers/DI
* remove manual module wiring via auto-discovery
* lean on runtime values for type-safe validation (e.g., Zod)
* optimize for Fastify-style performance ([Rikta][7])

But you’ll want to intentionally add:

* boundary conventions
* visibility into discovery/DI
* a production boot strategy (manifest/caching) once the app grows

### If you’re designing your own internal platform

Steal the idea, not the logo:

* Represent routes as values.
* Represent validation as schemas (values).
* Make discovery explicit and inspectable.
* Treat configuration as an escape hatch, not the default workflow.

---

## Summary

Here’s the architectural arc in one breath:

* **NestJS-style frameworks** made backend architecture explicit and scalable—at the cost of manual module wiring. ([NestJS Documentation][2])
* **Decorator + metadata-driven design** gave us ergonomic DI/routing, but it’s increasingly constrained by the evolving TypeScript/ECMAScript decorators story. ([TypeScript][6])
* **Zero-config frameworks** are not rejecting DI or structure—they’re rejecting duplicated registration, shifting “truth” into runtime values, exports, conventions, and discovery pipelines. ([Rikta][7])
* **Rikta** is a concrete example of this direction: auto-discovery replaces manual modules, while retaining a familiar controller/provider model, Fastify under the hood, and type-safe validation workflows. ([Rikta][7])

---

## Further reading

* NestJS docs on **modules and provider export/import patterns**. ([NestJS Documentation][2])
* NestJS docs on **DI fundamentals and how the dependency graph is created during bootstrapping**. ([NestJS Documentation][3])
* TypeScript docs on **`experimentalDecorators`** and **`emitDecoratorMetadata`**. ([TypeScript][5])
* TypeScript 5.0 release notes on **new decorators vs. legacy decorators**, including compatibility notes. ([TypeScript][6])
* TypeScript 5.2 release notes on **decorators metadata (`Symbol.metadata`)**. ([TypeScript][10])
* Rikta docs: **First Steps**, **Modules (Auto-Discovery)**, **Dependency Injection**, and **Benchmarks**. ([Rikta][1])

[1]: https://rikta.dev/docs/overview/first-steps "First Steps | Rikta"
[2]: https://docs.nestjs.com/modules "Modules | NestJS - A progressive Node.js framework"
[3]: https://docs.nestjs.com/fundamentals/dependency-injection "Custom providers | NestJS - A progressive Node.js framework"
[4]: https://www.typescriptlang.org/tsconfig/emitDecoratorMetadata.html "TypeScript: TSConfig Option: emitDecoratorMetadata"
[5]: https://www.typescriptlang.org/tsconfig/experimentalDecorators.html "TypeScript: TSConfig Option: experimentalDecorators"
[6]: https://www.typescriptlang.org/docs/handbook/release-notes/typescript-5-0.html "TypeScript: Documentation - TypeScript 5.0"
[7]: https://rikta.dev/docs/overview/modules "Modules (Auto-Discovery) | Rikta"
[8]: https://rikta.dev/docs/fundamentals/dependency-injection "Dependency Injection | Rikta"
[9]: https://rikta.dev/ "Rikta - The Zero-Config TypeScript Framework for Modern Backends | Rikta"
[10]: https://www.typescriptlang.org/docs/handbook/release-notes/typescript-5-2.html "TypeScript: Documentation - TypeScript 5.2"
[11]: https://rikta.dev/docs/benchmarks "Benchmarks | Rikta"
