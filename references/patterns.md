# Logseq → Obsidian Pattern Reference

## Properties → YAML Frontmatter

**Logseq:**
```markdown
title:: My Page Title
tags:: tag1, tag2
date:: 2025-01-03
custom-prop:: some value
```

**Obsidian:**
```markdown
---
title: My Page Title
tags:
  - tag1
  - tag2
date: 2025-01-03
custom-prop: some value
---
```

## Admonition Blocks → Callouts

| Logseq | Obsidian |
|--------|----------|
| `#+BEGIN_TIP` | `> [!tip]` |
| `#+BEGIN_NOTE` | `> [!note]` |
| `#+BEGIN_WARNING` | `> [!warning]` |
| `#+BEGIN_CAUTION` | `> [!caution]` |
| `#+BEGIN_IMPORTANT` | `> [!important]` |
| `#+BEGIN_QUOTE` | `> [!quote]` or standard `>` blockquote |
| `#+BEGIN_EXAMPLE` | `> [!example]` |

**Logseq:**
```markdown
#+BEGIN_TIP
This is a tip
with multiple lines
#+END_TIP
```

**Obsidian:**
```markdown
> [!tip]
> This is a tip
> with multiple lines
```

## Block References

**Logseq block ID:**
```markdown
- Some content
  id:: 68dcf0eb-ef8f-441a-843d-9e2d65a705ff
```

**Obsidian block ID:**
```markdown
- Some content ^68dcf0eb
```

**Logseq block reference:**
```markdown
See ((68dcf0eb-ef8f-441a-843d-9e2d65a705ff))
```

**Obsidian block embed (requires knowing the page):**
```markdown
![[PageName#^68dcf0eb]]
```

Note: Full conversion requires building a block ID → page mapping. Default behavior is to flag for manual fix.

## Numbered Lists

**Logseq:**
```markdown
- First item
  logseq.order-list-type:: number
- Second item
  logseq.order-list-type:: number
```

**Obsidian:**
```markdown
1. First item
2. Second item
```

## Collapsed State

**Logseq:**
```markdown
- Some heading
  collapsed:: true
	- Hidden content
```

**Obsidian:** Remove `collapsed:: true` (no equivalent; use headings + folding)

## Image Sizing

**Logseq:**
```markdown
![image.png](../assets/image_123.png){:height 244, :width 574}
```

**Obsidian:**
```markdown
![image.png](../assets/image_123.png)
```

Or with Obsidian's sizing syntax:
```markdown
![[image_123.png|574]]
```

## Journal Filenames

| Logseq | Obsidian |
|--------|----------|
| `journals/2025_01_03.md` | `Daily/2025-01-03.md` |

## Namespaces → Folders

**Logseq:** `pages/Projects%2FClientA%2FTask1.md` (URL-encoded slash)

**Obsidian Option A (flat):** `pages/Projects-ClientA-Task1.md`

**Obsidian Option B (folders):** `pages/Projects/ClientA/Task1.md`

## Wiki Links

`[[Page Name]]` — works identically in both ✓

## Tags

`#tag` — works identically in both ✓

Note: In Logseq, `#tag` creates a page. In Obsidian, it's just a tag (no page created).

## Task States

| Logseq | Obsidian |
|--------|----------|
| `TODO task` | `- [ ] task` |
| `DOING task` | `- [/] task` (with Tasks plugin) |
| `NOW task` | `- [/] task` |
| `LATER task` | `- [ ] task` |
| `DONE task` | `- [x] task` |
| `WAITING task` | `- [!] task` (custom) |
| `CANCELLED task` | `- [-] task` |

## Logseq Queries

**Logseq:**
```markdown
{{query (and (task TODO) (page "Projects"))}}
```

**Obsidian (Dataview):**
```markdown
```dataview
TASK FROM "Projects"
WHERE !completed
```​
```

Note: Query conversion is complex. Default behavior is to flag for manual conversion.

## LOGBOOK Blocks

**Logseq:**
```markdown
:LOGBOOK:
CLOCK: [2025-01-03 Fri 10:00]--[2025-01-03 Fri 11:30] => 01:30
:END:
```

**Obsidian:** Remove entirely (no equivalent)

## Embeds

| Logseq | Obsidian |
|--------|----------|
| `{{embed [[Page]]}}` | `![[Page]]` |
| `{{embed ((block-id))}}` | `![[Page#^block-id]]` |

## Special Properties to Remove

- `collapsed:: true`
- `logseq.order-list-type:: number`
- `id:: ...` (convert to `^block-id` at end of line)
- `:LOGBOOK:` blocks
