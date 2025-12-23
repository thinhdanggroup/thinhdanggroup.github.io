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
    overlay_image: /assets/images/htmx-spa-model/banner.png
    overlay_filter: 0.5
    teaser: /assets/images/htmx-spa-model/banner.png
title: "HTMX at Scale: How Attribute-Driven Interactivity Challenges the SPA Model"
tags:
    - hmtx
    - server-side render
    - spa model
---

You know the app.

It’s not a consumer social network. It’s not a 3D game in the browser. It’s… an admin console. A dashboard. A CRUD-heavy internal tool where “interactivity” means:

-   Filter a table
-   Edit a row inline
-   Submit a form
-   Delete a thing (with a confirmation)
-   Update a badge in the navbar so someone feels alive inside

And yet, we’ve collectively been shipping these apps with architectures that assume we’re building Gmail.

Single Page Applications (SPAs) brought real wins, but they also smuggled in a cost model: **you pay upfront in JavaScript, hydration, and client-side state management**—even when your “state” is just “what the database says right now.”

HTMX flips that model on its head with a stubbornly simple idea: **HTML is already a great UI format.** Instead of building an “API + frontend app,” you let the server return HTML fragments and you use attributes to stitch interactions together.

That sounds quaint. It also… works shockingly well.

But “works well” in a demo and “works well” at scale are different beasts. Let’s talk about the trade-offs: latency, server load, operational complexity, and security—plus where the SPA model still wins.

---

## The SPA bargain (and why CRUD apps feel heavier than they should)

A modern SPA typically means:

1. Ship a JavaScript application (plus a framework runtime).
2. Fetch JSON from an API.
3. Maintain client-side state and reconcile UI updates.
4. Handle routing, caching, optimistic updates, error states, edge cases…
5. Repeat until your “simple admin tool” has a webpack therapy budget.

SSR frameworks (Next.js, Remix, etc.) reduce time-to-first-paint by rendering HTML on the server, but then the browser still needs to **hydrate**: attach event handlers, reconcile server markup with client expectations, and “wake up” the app. React explicitly frames hydration as “attaching” React to HTML generated on the server. ([uk.react.dev][1])

Hydration is powerful—but it’s also a tax:

-   You ship more JS.
-   You pay parse/compile/execute costs.
-   You can get mismatches when server output and client render disagree (Next.js calls this out as a common hydration error class). ([Next.js][2])
-   Your architecture often duplicates work: validation rules on client _and_ server, routing rules on client _and_ server, etc.

None of this is “bad.” It’s just… a lot, if your app is mostly forms and tables.

**Section summary:** SPAs optimize for rich client-side apps, but CRUD-heavy tools often end up paying for complexity (hydration, state, and tooling) that doesn’t buy them much.

---

## HTMX’s counter-offer: HTML is the payload

HTMX is not “a smaller React.” It’s closer to a set of hypermedia primitives:

-   Attach an HTTP request to an element.
-   Decide what event triggers it.
-   Decide where the response goes.
-   Decide how it swaps into the DOM.

All with attributes.

For example, `hx-get` / `hx-post` and friends “issue a request of the specified type to the given URL when the element is triggered,” and you can tune the trigger behavior with `hx-trigger`. ([htmx][3])

A minimal “search as you type” might look like:

```html
<input
    name="q"
    placeholder="Search users..."
    hx-get="/users"
    hx-trigger="keyup changed delay:300ms"
    hx-target="#results"
    hx-swap="innerHTML"
/>

<div id="results">
    <!-- Server-rendered results land here -->
</div>
```

And `hx-swap` lets you choose _how_ content is inserted; by default it swaps `innerHTML`. ([htmx][4])

This changes the contract:

-   In an SPA: **JSON is the contract**, and your frontend code turns it into UI.
-   In HTMX: **HTML is the contract**, and your backend renders UI directly.

That sounds like going backwards until you remember: the web already knows how to render HTML quickly. Browsers are basically HTML accelerators wearing trench coats.

HTMX also gives you a practical way to tell “this is an HTMX request” on the server using request headers; the docs specifically mention checking the `HX-Request` header to differentiate HTMX-driven vs regular requests and decide what to render. ([htmx][3])

**Section summary:** HTMX shifts work from “client renders UI from data” to “server renders UI and client swaps it in,” using a small set of attribute-driven primitives. ([htmx][3])

---

## “But do I lose navigation?” No—`hx-boost` and history exist

One common fear is that HTMX makes your app feel like a pile of partial updates with no navigation story.

This is where `hx-boost` is sneakily important.

`hx-boost` can “boost” normal links and forms to use AJAX instead, while keeping the nice fallback that **if JavaScript is disabled, the site still works**. ([htmx][5])

It also pushes URLs for boosted anchor navigation (history entries), with `<body>` as the default target and `innerHTML` swaps by default. ([htmx][5])

And if you _explicitly_ want to push a URL during some interaction, `hx-push-url` exists; HTMX can snapshot the DOM into a history cache and restore it during back/forward navigation. ([htmx][6])

**Section summary:** HTMX isn’t “no navigation.” With `hx-boost` and `hx-push-url`, you can get SPA-like transitions while keeping progressive enhancement. ([htmx][5])

---

## A concrete “scale-shaped” pattern: one route, two render modes

Once you build more than a toy, you hit a real question:

> Do I need separate endpoints for fragments vs full pages?

You _can_, but many teams prefer a single route that returns either:

-   a full layout for normal navigation, or
-   a fragment for HTMX “component” requests.

The nuance: **boosted navigation wants the full page**, because the default target is the `<body>`. HTMX notes you can detect boosted requests by looking for `HX-Boosted` in the request headers. ([htmx][5])

Here’s a Flask example that handles both:

```python
# app.py
from flask import Flask, request, render_template

app = Flask(__name__)

def load_users(q: str | None):
    # Pretend this hits your DB and returns a list of dicts
    # In real life, page, filter, order, etc.
    return [
        {"id": 1, "email": "a@example.com", "role": "admin"},
        {"id": 2, "email": "b@example.com", "role": "member"},
    ]

@app.get("/users")
def users():
    q = request.args.get("q")
    users = load_users(q)

    is_htmx = request.headers.get("HX-Request") == "true"
    is_boosted = request.headers.get("HX-Boosted") == "true"

    # If it's an HTMX "component" update (not boosted navigation),
    # return only the fragment that will be swapped into a target.
    if is_htmx and not is_boosted:
        return render_template("_users_table.html", users=users)

    # Otherwise return the full page.
    return render_template("users.html", users=users)
```

This pattern is exactly what HTMX’s docs hint at when they say you can check `HX-Request` to decide what to render. ([htmx][3])

Now the templates.

Full page:

```html
<!-- templates/users.html -->
<!DOCTYPE html>
<html>
    <head>
        <meta charset="utf-8" />
        <title>Users</title>
        <script src="/static/htmx.min.js"></script>
    </head>
    <body hx-boost="true">
        <h1>Users</h1>

        <label>
            Search:
            <input
                name="q"
                value=""
                hx-get="/users"
                hx-trigger="keyup changed delay:300ms"
                hx-target="#users-table"
                hx-swap="innerHTML"
            />
        </label>

        <div id="users-table">{% include "_users_table.html" %}</div>
    </body>
</html>
```

Fragment:

```html
<!-- templates/_users_table.html -->
<table>
    <thead>
        <tr>
            <th>Email</th>
            <th>Role</th>
        </tr>
    </thead>
    <tbody>
        {% for u in users %}
        <tr id="user-{{ u.id }}">
            <td>{{ u.email }}</td>
            <td>{{ u.role }}</td>
        </tr>
        {% endfor %}
    </tbody>
</table>
```

This is the “aha” moment: **the server owns rendering.** The client is a swap engine.

Now scale enters the chat:

-   Your fragment HTML becomes a **public contract** between backend and frontend.
-   IDs and selectors (`#users-table`, `#user-123`) become your “API surface.”
-   You need conventions, testing, and discipline… like you would for JSON endpoints.

**Section summary:** At scale, HTMX apps benefit from “dual render mode” routes (full vs fragment), especially when using `hx-boost` navigation and `HX-Boosted` detection. ([htmx][5])

---

## Latency: the hidden race between “HTML now” and “JS later”

When people compare HTMX vs SPAs, they often argue about _SSR latency_ as if that’s the whole story.

It isn’t.

For user experience, there are two clocks:

1. **TTFB / first paint** — can the user see something?
2. **Time to interactive** — can the user _do_ something?

React SSR can stream HTML (for example via `renderToPipeableStream`) to improve perceived performance. ([React][7])
But the page still becomes fully interactive after hydration (`hydrateRoot` attaches React to the server-rendered HTML). ([uk.react.dev][1])

HTMX changes the equation:

-   You typically ship **far less JS**.
-   Interactivity is “opt-in” per element (only elements with HTMX attributes participate).
-   There’s no global hydration step for “the whole app,” because the whole app isn’t a JS runtime.

That doesn’t mean HTMX is “always faster.” It means your latency work shifts:

-   In SPA land: optimize bundles, hydration, client CPU, caching JSON, reducing re-renders.
-   In HTMX land: optimize server render time, caching fragments, DB queries, network payloads.

### What to benchmark (without lying to yourself)

If you want a fair benchmark between “HTMX SSR fragments” and “SPA/SSR framework,” measure these separately:

-   **Server render time** (p50/p95): how long to generate the response?
-   **Payload size** (compressed): HTML fragment vs JSON + client templates + JS bundle
-   **Client main-thread time**: JS parse/execute/hydration vs DOM swap
-   **Interaction latency**: click → visible update (p95 matters more than p50 in real life)

And for SSR frameworks, include the “double phase”: **HTML arrives, then hydration finishes**. React’s docs explicitly treat hydration as a distinct step (“attach” React to server-rendered HTML). ([uk.react.dev][1])

**Section summary:** Performance comparisons are often really “hydration vs swap” comparisons. React SSR can stream HTML, but hydration is still a distinct cost; HTMX often avoids that global cost and shifts focus to server render + fragment caching. ([React][7])

---

## Server load: yes, HTMX can move work back to the server

Here’s the honest part: HTMX often increases server-side rendering work because you’re rendering HTML for more interactions.

But two things are also true:

1. SPAs still hit your server (or BFF) for data.
2. The expensive part is frequently **I/O and database work**, not whether you serialized JSON or rendered a template.

So the right question isn’t “does HTMX increase server load?” It’s:

> Does HTMX increase _render CPU_ enough to matter compared to your DB, caching, and network costs?

### A practical load-test harness

You can benchmark HTMX endpoints the same way you benchmark any HTTP service.

Here’s a k6 script that simulates:

-   full page loads
-   fragment updates (search)
-   write operations (create)

```javascript
// loadtest.js
import http from "k6/http";
import { sleep, check } from "k6";

export const options = {
    vus: 50,
    duration: "60s",
};

export default function () {
    // Full navigation load (non-HTMX)
    let res1 = http.get("http://localhost:5000/users");
    check(res1, { "users page 200": (r) => r.status === 200 });

    // HTMX fragment update (HX-Request header)
    let res2 = http.get("http://localhost:5000/users?q=a", {
        headers: { "HX-Request": "true" },
    });
    check(res2, { "fragment 200": (r) => r.status === 200 });

    sleep(0.2);
}
```

Then, measure:

-   server CPU (per worker)
-   response times
-   DB query counts per request
-   cache hit rates

And remember: **fragment endpoints are cacheable** when they’re GETs and depend only on URL + auth context. Treat them like view functions with a stable input/output contract.

### “Scale-shaped” HTMX tricks: concurrency and perceived performance

At scale, concurrency isn’t just server concurrency—it’s _user concurrency_ on the same page.

HTMX requests can overlap: fast typers, double-clickers, slow networks.

Two useful tools:

-   `hx-indicator` lets you add a visual indicator during in-flight requests by toggling the `htmx-request` class. ([htmx][8])
-   `hx-sync` lets you synchronize requests across elements (e.g., cancel or queue). ([htmx][9])

This is the kind of detail that starts to matter when your app isn’t a demo and your users have opinions (and caffeine).

**Section summary:** HTMX can increase server rendering work, but the dominant costs are often DB/I/O. Load testing should isolate full page vs fragment endpoints, and HTMX provides tools (`hx-sync`, `hx-indicator`) to manage concurrency and perceived performance. ([htmx][9])

---

## UI consistency at scale: out-of-band updates and “HTML as a contract”

In CRUD apps, one interaction often affects multiple UI regions:

-   Add item → update list + update “count” badge in navbar
-   Change role → update row + update filters summary

SPAs solve this with shared client state.

HTMX solves it with **out-of-band swaps**: you can “piggyback” updates to other elements in the same response using `hx-swap-oob`. ([htmx][10])

Example response to “add user” might include:

```html
<!-- Main target content -->
<tr id="user-3">
    <td>c@example.com</td>
    <td>member</td>
</tr>

<!-- Out-of-band update -->
<span id="user-count" hx-swap-oob="true">3</span>
```

This is powerful—and it’s also a place where “HTML as an API” becomes real:

-   IDs must be stable.
-   DOM structure changes are breaking changes.
-   Your backend response is now “multi-part UI.”

This is why teams that scale HTMX successfully tend to adopt conventions:

-   predictable IDs (`user-{{id}}`)
-   component-like template organization (macros/partials)
-   integration tests that assert key fragments exist

**Section summary:** HTMX scales best when you treat HTML fragments like an API contract. Out-of-band swaps (`hx-swap-oob`) help coordinate multi-region updates without a client state store. ([htmx][10])

---

## Security trade-offs: HTMX is “boring web,” and that’s a compliment

Security is where HTMX’s “just HTTP” approach is both a win and a responsibility.

### CSRF: nothing magical, but nothing weird either

A CSRF attack tricks an authenticated browser into making an unwanted request. OWASP’s CSRF cheat sheet describes the core issue: if a user is authenticated, an unprotected site can’t distinguish legitimate requests from forged ones. ([OWASP Cheat Sheet Series][11])

HTMX typically uses cookies like any normal web app (because it’s making same-origin requests), so you should use standard CSRF protections:

-   SameSite cookies where appropriate
-   anti-CSRF tokens for state-changing requests
-   verify Origin/Referer as defense-in-depth (depending on your stack)

The good news: you can apply the same mitigations you’d apply to server-rendered apps. The bad news: you still have to apply them (HTMX doesn’t make CSRF disappear).

### XSS: HTML rendering makes output encoding non-negotiable

If your server returns HTML fragments that get inserted into the DOM, XSS prevention is not optional. OWASP’s XSS Prevention Cheat Sheet is blunt about this being a serious class of vulnerability and focuses on output encoding and contextual defenses. ([OWASP Cheat Sheet Series][12])

HTMX’s own security guidance emphasizes practical “golden rules,” including:

-   use an auto-escaping template engine
-   set cookies with `Secure`, `HttpOnly`, and `SameSite=Lax` when using authentication cookies ([htmx][13])

That’s not HTMX-specific advice—it’s “build web apps like a responsible adult” advice. Which is exactly the point: HTMX encourages you to stay in the world of well-understood browser security mechanisms.

### Response-driven behaviors: redirects and triggers

As you scale, you’ll inevitably want server responses to do more than swap HTML.

HTMX supports response headers like:

-   `HX-Redirect` to trigger a client-side redirect with a full reload ([htmx][14])
-   `HX-Trigger` to trigger client-side events from a response ([htmx][15])

These are convenient, but also “security-shaped”: treat them as part of your server’s behavior surface area. Don’t let untrusted upstream systems inject them.

**Section summary:** HTMX leans on standard browser security (cookies, CSRF defenses, output encoding). OWASP guidance applies directly, and HTMX’s own security writeups emphasize auto-escaping templates and secure cookie settings. ([OWASP Cheat Sheet Series][11])

---

## Where HTMX challenges the SPA model… and where SPAs still win

HTMX’s core challenge to the SPA model is philosophical:

> If your UI is mostly a projection of server state, why build a client-side state machine?

At scale, this can be a **massive** simplifier:

-   fewer frontend build artifacts
-   fewer “API shape” negotiations
-   fewer hydration issues
-   fewer duplicated validation rules

But HTMX is not a universal replacement.

SPAs (and rich client frameworks) still win when you need:

-   complex client-side state (offline mode, heavy optimistic UI, local-first apps)
-   rich interactions (drag/drop editors, canvas/3D, collaborative real-time tools)
-   large in-browser computation
-   a truly decoupled frontend team shipping independently of backend deploys

The mature take is: **choose a cost model.**

-   HTMX cost model: server rendering + fragment contracts + caching discipline
-   SPA cost model: client runtime + hydration/bundles + state discipline

Both require discipline. They just ask for it in different places.

**Section summary:** HTMX can dramatically simplify CRUD-heavy apps by avoiding “client state machines for server state,” but SPAs remain best for rich client interactivity, offline/local-first, and complex UI state.

---

## Key takeaways

-   **HTMX shifts interactivity from “JS app” to “HTML + attributes.”** The primitives (`hx-trigger`, `hx-swap`, etc.) are intentionally small but powerful. ([htmx][3])
-   **The real SPA tax for CRUD apps is often hydration and state complexity, not raw rendering speed.** React hydration is explicitly a distinct step after SSR. ([uk.react.dev][1])
-   **At scale, HTML fragments become an API contract.** Stable IDs/selectors and template conventions matter as much as API versioning does in SPA land.
-   **Server load concerns are real but measurable.** Benchmark full loads vs fragment updates separately; optimize DB/I/O first, then template CPU.
-   **Security stays “boring web.”** Apply OWASP CSRF and XSS guidance; use auto-escaping templates and secure cookies. ([OWASP Cheat Sheet Series][11])

---

## Further reading

If you want to keep digging:

-   HTMX docs (core attributes, request/response headers, swapping behavior). ([htmx][3])
-   `hx-boost` and progressive enhancement + `HX-Boosted` detection. ([htmx][5])
-   History behavior with `hx-push-url`. ([htmx][6])
-   Out-of-band swaps (`hx-swap-oob`) for multi-region updates. ([htmx][10])
-   OWASP CSRF and XSS prevention cheat sheets (good, sober, unglamorous reading). ([OWASP Cheat Sheet Series][11])
-   React SSR streaming (`renderToPipeableStream`) and hydration (`hydrateRoot`) for a clear view of what the “modern SSR SPA” pipeline actually does. ([React][7])

[1]: https://uk.react.dev/reference/react-dom/client/hydrateRoot?utm_source=thinhdanggroup.github.io "hydrateRoot – React"
[2]: https://nextjs.org/docs/messages/react-hydration-error?utm_source=thinhdanggroup.github.io "Text content does not match server-rendered HTML - Next.js"
[3]: https://htmx.org/docs/?utm_source=thinhdanggroup.github.io "Documentation - htmx"
[4]: https://htmx.org/attributes/hx-swap/?utm_source=thinhdanggroup.github.io "htmx ~ hx-swap Attribute"
[5]: https://htmx.org/attributes/hx-boost/ "</> htmx ~ hx-boost Attribute"
[6]: https://htmx.org/attributes/hx-push-url/?utm_source=thinhdanggroup.github.io "htmx ~ hx-push-url Attribute"
[7]: https://react.dev/reference/react-dom/server/renderToPipeableStream?utm_source=thinhdanggroup.github.io "renderToPipeableStream – React"
[8]: https://htmx.org/attributes/hx-indicator/?utm_source=thinhdanggroup.github.io "htmx ~ hx-indicator Attribute"
[9]: https://htmx.org/attributes/hx-sync/?utm_source=thinhdanggroup.github.io "htmx ~ hx-sync Attribute"
[10]: https://htmx.org/attributes/hx-swap-oob/?utm_source=thinhdanggroup.github.io "htmx ~ hx-swap-oob Attribute"
[11]: https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html?utm_source=thinhdanggroup.github.io "Cross-Site Request Forgery Prevention Cheat Sheet - OWASP"
[12]: https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html?utm_source=thinhdanggroup.github.io "Cross Site Scripting Prevention - OWASP Cheat Sheet Series"
[13]: https://htmx.org/essays/web-security-basics-with-htmx/?utm_source=thinhdanggroup.github.io "Web Security Basics (with htmx)"
[14]: https://htmx.org/headers/hx-redirect/?utm_source=thinhdanggroup.github.io "htmx ~ HX-Redirect Response Header"
[15]: https://htmx.org/headers/hx-trigger/?utm_source=thinhdanggroup.github.io "HX-Trigger Response Headers - htmx"
