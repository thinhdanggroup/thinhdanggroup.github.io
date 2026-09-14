# Voice

Rules derived from the existing archive. The voice gate in `gates.md` checks a draft
against this file, so it must describe what the blog actually sounds like — not a
generic style guide.

## Shape of a daily post

1,000–1,500 words. One idea, one worked example, one takeaway. Deliberately lighter
than the 2,000–3,300 word flagship posts, without being thinner in substance.

- **Cold open on a concrete failure or situation**, not a definition. The archive
  opens posts with lines like "At 02:13, your control plane sneezes" and "There's a
  particular kind of frustration that only backend engineers know". Never open with
  "In today's fast-paced world" or "X is a powerful tool that...". A tutorial-shaped
  post (a setup walkthrough, a version-pinned how-to) may open by naming the concrete
  problem the setup solves instead of a failure scene — but it still opens on a
  specific situation, never a category definition.
- **H2 sections** carrying real claims as headings, not labels. "The failure mode:
  when retry becomes attack" beats "Background".
- **A worked example with runnable code**, commented, in the language the topic
  actually uses. Snippets are short and adapted for a reader to lift.
- **Tradeoffs stated plainly**, including when the thing being described is the wrong
  choice.
- **The post ends with a real "Further reading" section** — a short list of the actual
  sources used, with working links, never invented ones. That heading (some spelling
  of "Further reading", "Further Reading & References", or "References") is
  consistently the *last* section in the archive. A "Key takeaways" section, when the
  post has one, comes immediately *before* it, not after — "Key takeaways" is never
  the final heading of a post. For a daily post's length, one closing section is
  usually enough: fold the takeaway into a short "Key takeaways" list only when the
  post makes more than one distinct claim worth restating; otherwise go straight from
  the last body section into "Further reading".

## Register

Direct and technical, second person ("your control plane", "you end up copy-pasting"),
with occasional dry humor that never displaces the explanation. Bold for the term
being defined. Em dashes for asides. Short paragraphs — two to four sentences.

Write as an engineer who has run this in production, showing the reader what broke
and why. Not a vendor, not a tutorial mill.

## Hard blocks

The voice gate blocks the draft on any of these:

- **Filler openings** — "In today's fast-paced world", "In the ever-evolving landscape
  of", "Let's dive in", "Buckle up".
- **Hedging that carries no information** — "it's important to note that", "it's worth
  mentioning", "generally speaking", "in many cases" used to avoid committing.
- **Listicle padding** — a numbered list whose items are one sentence each and could
  be a paragraph; sections that exist to hit a count.
- **Restating the heading as the first sentence** of the section.
- **Conclusions that summarise without concluding** — a final section that repeats the
  post rather than saying what the reader should do.
- **Unearned superlatives** — "revolutionary", "game-changing", "seamless",
  "cutting-edge", "robust" used as filler.
- **The triad tic** — reflexively grouping everything into three adjectives or three
  clauses.
- **Vague attribution** — "studies show", "experts agree", "it is widely known"
  without a link.
- **A fabricated "Further reading" entry** — every link in that section must be one
  actually consulted while researching the post (see `sources.md`'s evidence ledger).
  An invented-sounding citation is worse than no citation.

## Two things that are not slop

Dry humor and strong opinions are in-voice. A gate that strips them produces exactly
the bland, hedged prose the gate exists to prevent. Block on the patterns listed
above, not on personality.
