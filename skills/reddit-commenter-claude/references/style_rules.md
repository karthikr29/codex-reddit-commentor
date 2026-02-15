# Human Writing Rules (Strict)

## Hard Blocks

1. No em dash character: `—`
2. No semicolon: `;`
3. No fake personal experience.
4. No forced engagement hooks.
5. No editor-like boilerplate cadence.
6. No fabricated personal claims (invented job titles, company names, team experiences, or made-up stories).

## Banned Terms and Phrases

- delve
- dive into
- unpack
- navigate
- landscape
- realm
- leverage
- utilize
- robust
- comprehensive
- streamline
- furthermore
- moreover
- additionally
- it is worth noting
- it is important to note
- at the end of the day
- game changer
- paradigm shift
- crucial
- vital
- essential
- fascinating
- intriguing
- i would be happy to
- absolutely
- definitely
- that being said
- on one hand

## Discouraged Openers

- great question
- i totally agree
- this is underrated
- as someone who
- in my humble opinion

## Fabrication Hard Blocks

The following patterns are automatically detected and rejected by the style guard:

- "we had", "what worked for us", "when I ran"
- "at my company", "our company", "my team", "our team"
- "in my experience at", "I used to work", "back when I was"
- "in my previous role", "clients I've worked with"
- "my startup/agency/firm/business/shop"
- "our team/org/department/startup"
- "I ran a/an/the/my...", "I managed a/an/the/my..."
- "I led a/an/the/my..."

Only personal references from the `personal_facts.md` fact bank are permitted.

## Preferred Natural Style

1. Use plain words: `use`, `help`, `show`, `get`, `need`.
2. Use contractions naturally: `don't`, `can't`, `it's`.
3. Mix short and medium sentence lengths.
4. Keep direct tone. Avoid excessive hedging.
5. End with a question only when it naturally helps the thread.

## Validation Outcome

A candidate fails style validation when:

1. Any hard block is present.
2. Any banned phrase is detected.
3. Promotional or salesy language appears while promotion is disabled.
4. Fabrication pattern is detected (invented personal claims).
