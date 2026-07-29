---
description: Search the 500+ persona library by name, era, domain, tags, or description. Returns matching personas with their HPEP profiles. Use when user wants to find or browse personas.
---

# Persona Search

Search the persona library using `$ARGUMENTS` as the query.

## Instructions

Run this Python search against the installed library:

```python
from persona_math.persona_library import search_personas
results = search_personas(query="$ARGUMENTS")
for r in results[:10]:
    print(f"[{r['id']}] {r['name']} ({r['era']}) — {r['tagline'][:60]}")
```

## Search Strategies

If `$ARGUMENTS` is empty → list all 500+ personas grouped by category:
- Ancient (91): Greek, Roman, Eastern philosophers and scientists
- Medieval/Modern (83): Scholastics, Renaissance, Enlightenment, 19th century
- Scientists/Artists (95): Physicists, mathematicians, writers, musicians
- Fictional (81): Literary, film, TV, game characters
- Mythological (71): Greek, Norse, Hindu, Jungian archetypes
- Leaders/Warriors (113): Political and military leaders across history

If query matches a domain:
- `philosophy`, `science`, `leadership`, `fiction`, `mythology`, `art`

If query matches an era:
- `ancient`, `medieval`, `renaissance`, `modern`, `contemporary`

## Output Format
Show each result as:
```
[id] Name (Era/Domain)
"Tagline"
Tags: tag1, tag2, tag3
Price: $X.XX
```

After showing results, ask: "Which persona would you like to activate?"
