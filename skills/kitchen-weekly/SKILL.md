---
name: kitchen-weekly
description: Runs Claude's Kitchen weekly Woolworths jobs — the weekly proposal, the on-request cart run, removals, order checks, pantry tidy and the evening notes round. Use when a scheduled task or the user says "run the weekly proposal", "push to cart", "check for my order", "read my notes", "Claude's Kitchen runbook", or asks about their grocery proposal.
---

# Claude's Kitchen weekly runs

1. Read `references/runbook.md` in full before doing anything. It is the source of truth.
2. Fill its placeholders from the user's folder: `smart/rules.json` (name, members, timezone, location) and `smart/config.json` (page URL, cart task id). If `smart/config.json` is missing, the household isn't set up — run the kitchen-setup skill instead.
3. Run the section asked for (§A weekly proposal, §C cart run, §D removals, §E order check, §F pantry tidy, §G evening notes). "Run it" in chat means build proposals only — never change the cart unless it is the cart run or the user explicitly says to add ("push to cart").
4. Hard limits, always: never check out or pay, never enter passwords, never change account settings, only add approved items, stop and report on sign-in prompts or CAPTCHAs. If the household asked for no spoilers, never mention or look up event results.
5. Send one short summary at the end, signed as the helper's name.
