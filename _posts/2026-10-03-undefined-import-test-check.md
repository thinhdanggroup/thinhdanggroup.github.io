---
title: "Would Your Test Pass If Every Import Returned Undefined?"
description: "A one-config Jest run that hollows out every import and lists the tests that stay green — the ones that cannot fail for a defect."
tags:
    - Testing
    - TypeScript
    - AI Agents
categories:
    - software-engineering
header:
    overlay_image: /assets/images/undefined-import-test-check/banner.webp
    overlay_filter: 0.5
    teaser: /assets/images/undefined-import-test-check/teaser.webp
toc: true
toc_sticky: true
---

The pricing PR has forty new tests, all green, and a coverage bump the bot is proud of. Two weeks later a customer gets free shipping on a $12 order. You open the test file looking for the test that should have caught it, and find six that look like they test checkout. None of them would have noticed if `checkout` returned nothing at all.

That last sentence is a check you can actually run. It comes from [pstack](https://github.com/cursor/plugins/tree/main/pstack), Lauren Tan's Cursor plugin of agent skills, which at version 0.15.5 ships twenty-three short skills with one engineering principle each. One of them, **test behavior, not implementation**, carries the sharpest testing heuristic I have read in a while:

> before you keep a test, ask whether it would still pass if every function it imports returned `undefined`. If yes, it observes no behavior and cannot fail for a defect.

pstack treats it as a thought experiment for an agent to apply when it writes, changes, or keeps a test. This post turns it into a job: one Jest config, one results processor, and a list of tests to rewrite or delete.

## A test that survives a hollow module is not testing the module

The argument is short. A test exists to fail when the code is wrong. "Returns `undefined` from everything" is about as wrong as code gets — no arithmetic, no branching, no side effects. A test that stays green against that cannot be distinguishing correct code from broken code. It is spending CI minutes and reviewer attention to assert something about itself.

pstack names five shapes that pass this way:

- **Weak or no assertion** — `not.toThrow`, `toBeDefined`, `toBeTruthy`, or no `expect` at all.
- **Mock or absence only** — `toHaveBeenCalled`, `toBeUndefined`, `toEqual([])`.
- **Self-referential** — the expected value comes from the code under test, as in `expect(f(a)).toBe(f(a))`.
- **Constant pin** — `expect(LIMITS.maxTools).toBe(8)`, restating a value the code already holds.
- **Fixture asserts fixture** — the assertion reads data the test built in `beforeEach`, and the subject never runs.

The constant pin is the one people defend, so it deserves its own sentence. pstack's point is that it does worse than catch nothing: it "fails when someone edits the constant or the prompt it restates, so it prevents that edit." It is a test that only ever goes red for a deliberate, correct change.

## The worked example: a checkout module and six tests

Here is a small pricing module. Shipping is flat $5 under a $50 threshold, and one coupon exists.

```ts
// pricing.ts
export const FREE_SHIPPING_THRESHOLD = 50;
export const FLAT_SHIPPING = 5;

export type Line = { sku: string; price: number; qty: number };
export type Receipt = { subtotal: number; shipping: number; total: number };

const COUPONS: Record<string, number> = { SAVE10: 0.1 };

export function findCoupon(code: string): number | undefined {
  return COUPONS[code];
}

export function checkout(lines: Line[], code?: string): Receipt {
  const gross = lines.reduce((sum, l) => sum + l.price * l.qty, 0);
  const discount = code ? (findCoupon(code) ?? 0) : 0;
  const subtotal = gross * (1 - discount);
  const shipping = subtotal >= FREE_SHIPPING_THRESHOLD ? 0 : FLAT_SHIPPING;
  return { subtotal, shipping, total: subtotal + shipping };
}
```

And six tests, every one of which passes against the real module:

```ts
// pricing.test.ts
import { checkout, findCoupon, FREE_SHIPPING_THRESHOLD, type Line } from "./pricing";

describe("checkout", () => {
  let cart: Line[];

  beforeEach(() => {
    cart = [
      { sku: "mug", price: 12, qty: 2 },
      { sku: "tee", price: 18, qty: 1 },
    ];
  });

  test("does not throw on a normal cart", () => {
    expect(() => checkout(cart)).not.toThrow(); // weak assertion
  });

  test("is deterministic", () => {
    expect(checkout(cart)).toEqual(checkout(cart)); // self-referential
  });

  test("free shipping starts at 50", () => {
    expect(FREE_SHIPPING_THRESHOLD).toBe(50); // constant pin
  });

  test("cart has two lines", () => {
    expect(cart).toHaveLength(2); // fixture asserts fixture
  });

  test("unknown coupon is ignored", () => {
    expect(findCoupon("BOGUS")).toBeUndefined(); // absence only
  });

  test("charges flat shipping under the threshold", () => {
    expect(checkout(cart)).toEqual({ subtotal: 42, shipping: 5, total: 47 });
  });
});
```

Read cold, five of these look like reasonable coverage. Only the last one would have caught the $12 free-shipping bug.

## Jest already ships the hollow module

You do not need to write the stubs. Jest's [`automock`](https://jestjs.io/docs/configuration#automock-boolean) option "tells Jest that all imported modules in your tests should be mocked automatically", and an automocked function is a mock that "when called will return `undefined`", `async` functions included. That is the thought experiment, implemented. It also mocks the module under test, because the test imports it like any other module — which is exactly what the check needs.

One detail makes the constant pin fall out for free: automock keeps primitive exports at their original value. `FREE_SHIPPING_THRESHOLD` is still `50` in the hollow run, so the pin stays green and lands on the list where it belongs.

Point a second config at the same tests with automock on, and a results processor that records whatever still passed:

```js
// jest.hollow.config.js
const base = require("./jest.config.js");

module.exports = {
  ...base,
  automock: true,
  testResultsProcessor: "./hollow-report.js",
};
```

```js
// hollow-report.js — Jest calls this once, after all tests have finished
const fs = require("node:fs");

module.exports = (results) => {
  const hollow = results.testResults.flatMap((file) =>
    file.testResults
      .filter((t) => t.status === "passed")
      .map((t) => `${file.testFilePath}: ${[...t.ancestorTitles, t.title].join(" > ")}`),
  );
  fs.writeFileSync("hollow.txt", hollow.length ? hollow.join("\n") + "\n" : "");
  return results;
};
```

In this run, green is the failure. Most of your suite should go red, so the Jest exit code means nothing and the file is the signal. As a CI step:

```bash
rm -f hollow.txt
npx jest --config jest.hollow.config.js > /dev/null 2>&1 || true
# No file means the run never reached the processor: a broken run, not a clean one.
test -f hollow.txt || { echo "hollow run did not complete" >&2; exit 2; }
cat hollow.txt
test ! -s hollow.txt
```

The `rm` and the `test -f` matter. Without them, a config typo leaves a stale or missing file, and `test ! -s` on a missing file succeeds. A check that passes when it never ran is the very thing this post is hunting.

On the example, `hollow.txt` lists five tests. The sixth goes red because `undefined` is not `{ subtotal: 42, shipping: 5, total: 47 }`.

## Fixing the five, or deleting them

pstack's fix is to "call the subject inside the test body with one concrete input and assert the literal output or the observable effect". Applied to the list:

- `not.toThrow` and the self-referential test collapse into the literal-output test that already exists. Delete them.
- The cart-length test never runs `checkout`. Delete it.
- The constant pin becomes a test of the mechanism that reads it, on both sides of the boundary: a `price: 50` cart expects `shipping` of `0`, and a `price: 49.99` cart expects `5`. Now moving the threshold in either direction breaks one of them, which is a real behavior change worth a red build.
- The absence test gets its presence twin in the same body, as pstack prescribes: assert that `checkout(cart, "BOGUS").subtotal` is `42` and `checkout(cart, "SAVE10").subtotal` is close to `37.8` — `toBeCloseTo`, not `toBe`, because `42 * 0.9` is `37.800000000000004` in floating point. Now a coupon table that silently stops matching anything goes red.

Rerun the hollow config and `hollow.txt` comes back empty.

## Where the check leaks

The undefined run catches less than the list of five suggests, and you should know which parts. `toBeDefined`, `toBeTruthy`, `toEqual([])` and `toHaveLength(0)` all fail on `undefined`, so tests built on them go red in the hollow run and look healthy. They are still weak — they pass for any wrong answer that happens not to be `undefined`. The same goes for a bare `toHaveBeenCalled`: in the hollow run the subject never calls its collaborators, so the assertion fails, even though asserting a call without its payload proves very little. For those, pstack's rule is a reading rule, not a script: assert the payload the mock received, not that it was called.

That gap has a name. "Returns `undefined`" is a single mutant applied to every function at once, and the general tool is mutation testing. In [Stryker's](https://stryker-mutator.io/docs/) terms, a test run that fails against a changed program **kills** the mutant, and one that passes lets it **survive**. A mutation tool introduces many small changes to your code. The hollow run introduces one huge one, which is why it is cheap enough to run on every PR and blunt enough to miss the subtle cases. Treat it as a floor, and run a mutation tool when the floor is clean.

Two practical edges. Node core modules such as `fs` are not automocked unless you mock them explicitly, so a test that only exercises `fs` behavior can survive for an honest reason. And under native ESM, Jest applies automock on Node 24.9+ only to synchronously evaluable module graphs — a graph with top-level `await` still needs `jest.unstable_mockModule`, so check that the hollow run actually hollowed something before trusting an empty list.

## Make it a job, not a review comment

The reason this lives in an agent toolkit is that agents write a lot of tests, and "please don't write weak tests" is a sentence that gets read once and forgotten. A sibling pstack principle, **encode lessons in structure**, says to turn a recurring correction into "a lint, metadata flag, runtime check, or script instead of more text", and gives the reason that matters most with agents in the loop: "agents copy whatever the surrounding code already does and a weaker guard becomes the next template." Five hollow tests in a file are an invitation to write a sixth.

So run the hollow config in CI on changed test files and fail the job on a non-empty `hollow.txt`, with an allowlist for the cases pstack says to keep — relations across a table's rows, and compile-time checks in `*.test-d.ts` files. Coverage will keep reporting that the lines ran. This job reports whether anything would have noticed if they ran wrong.

## Further reading

- [pstack — cursor/plugins](https://github.com/cursor/plugins/tree/main/pstack)
- [pstack principle: test behavior, not implementation](https://github.com/cursor/plugins/blob/main/pstack/skills/principle-test-behavior-not-implementation/SKILL.md)
- [pstack principle: encode lessons in structure](https://github.com/cursor/plugins/blob/main/pstack/skills/principle-encode-lessons-in-structure/SKILL.md)
- [Jest configuration: `automock` and `testResultsProcessor`](https://jestjs.io/docs/configuration)
- [Jest object: `jest.createMockFromModule`](https://jestjs.io/docs/jest-object)
- [Jest: ECMAScript modules](https://jestjs.io/docs/ecmascript-modules)
- [Stryker Mutator: introduction to mutation testing](https://stryker-mutator.io/docs/)
