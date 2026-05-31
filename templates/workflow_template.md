# Workflow: {{title}}

> **Source:** https://www.youtube.com/watch?v={{video_id}}
> **Generated:** {{date}}
> **Transcript:** {{language}} ({{transcript_type}}) — {{duration}}
{{#if auto_generated}}> **Warning:** Auto-generated transcript — verify technical terms manually.{{/if}}

---

## Summary

{{summary}}

---

## Prerequisites

Before starting, ensure you have:

{{#each prerequisite}}
- [ ] {{this}}
{{/each}}

---

## Tools & Commands Referenced

{{#each tool}}
- `{{this}}`
{{/each}}

---

## Step-by-Step Instructions

{{#each step}}
### Step {{number}}: {{title}}

{{description}}

{{#if command}}
```bash
{{command}}
```
{{/if}}

{{#if expected_output}}
**Expected output:** {{expected_output}}
{{/if}}

---
{{/each}}

## Warnings & Gotchas

{{#each warning}}
> **Warning:** {{this}}
{{/each}}

## Tips & Optimizations

{{#each tip}}
- {{this}}
{{/each}}

---

*Auto-generated from YouTube transcript. Review all steps before running in production.*
