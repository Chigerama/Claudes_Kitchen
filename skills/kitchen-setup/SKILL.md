---
name: kitchen-setup
description: Sets up Claude's Kitchen for a new household. Use when the user says "set up Claude's Kitchen", "set up my Woolworths helper", "start the grocery planner", or installs this plugin for the first time.
---

# Set up Claude's Kitchen

Follow these steps in order. Keep messages plain and short. Read `../kitchen-weekly/references/runbook.md` first so you know how the weekly runs work.

## 1. Folder and invoices
1. Ask the user to connect a folder on their computer that holds their Woolworths order invoice PDFs (downloaded from My Account → Orders). At least 4 orders are needed; 10+ works best. (After setup, new orders are read from the website automatically — PDFs are only needed for the starting history.)
2. Copy the engine and starter files into that folder without overwriting anything that exists:
   - `${CLAUDE_PLUGIN_ROOT}/engine/extract_orders.py`, `build_ranking.py` → folder top level
   - `${CLAUDE_PLUGIN_ROOT}/starter/item_groups.csv` → folder top level
   - `${CLAUDE_PLUGIN_ROOT}/engine/friday.py`, `build_page.py`, `order_extract.js`, `page_template.html` and `${CLAUDE_PLUGIN_ROOT}/starter/rules.json`, `recipes.json` → `<folder>/smart/`
   - create `smart/runs/`, and empty `smart/learned.json` `{}`, `smart/meal_history.json` `[]`, `smart/outof_map.json` `{}`, `smart/stock.json` `{}`, `smart/catalog.json` `{}`, `smart/never.json` `{}`, `smart/schedule.json` `{}`, `smart/pantry.json` `[]`.
   Work on the user's computer (device_bash) when available; otherwise stage, build and commit back.
3. Check `python3` and the `pdfplumber` (or `pypdf`) package are available; install if missing.
4. Run `python3 smart/friday.py refresh`. Show the user their top 20 most-bought groups from `smart/stats.json`.

## 2. Interview (use AskUserQuestion; 1–4 questions per round)
- **Name:** what to call the helper (default "Claude"). Save to `rules.json → household_name`. If changed, replace the helper's name in the visible text of `smart/page_template.html` (the page title and heading, "A word with …", messages), but never inside tool or product names such as "Claude Code Remote", "Claude in Chrome" or "claude.ai".
- **Household:** first names of the people who cook (e.g. two names) → `rules.json → household_members`. Used for the dinner schedule, the note box ("from" buttons) and how the butler addresses people.
- **Location:** city and timezone (IANA, e.g. `Australia/Sydney`). Look up the city's latitude/longitude to 2 decimals. Save to `rules.json → timezone` and `location`. Store no more detail than the city.
- **Public and bank holidays:** which state or region's holidays apply (default: the state their city is in). Ask whether to include any local or regional days. Look up the official government list for the rest of this year and next, and keep it for step 3 (`settings/holidays`). Never copy another household's holidays.
- **Events they plan around:** ask whether they follow any sports or other regular events that affect meals or the shop (e.g. a motorsport series, football code, cricket). If yes: which ones, and do they watch live or delayed? If delayed, they want **no spoilers**: Claude must never mention results. Look up the official season calendars (never results pages) and keep them for `settings/events`; ask which day the weekly preview should appear (default Thursday). If none, `settings/events` stays empty.
- **Core items:** which groups to propose every week → `rules.json → core`.
- **Never buy:** groups or products to never propose → `rules.json → never`.
- **Unmatched items:** if many top items are in group "Other", add sensible patterns to `item_groups.csv` and re-run refresh.
- **Recipes:** keep all starter dinners, or remove any the household doesn't eat. They can also import their own from Paprika later on the page, or post a recipe in the note box.

## 3. Cart task, then the page
1. **Create the on-request cart task first** (no schedule; requires the user's computer with the folder attached), named "<NAME>'s Kitchen – add to cart (on request)", prompt: "You are <NAME>. The household pressed Confirm complete on the page (<PAGE_URL once known>). Use the kitchen-weekly skill and carry out runbook §C exactly, following its hard rules; folder: <FOLDER>." Save its id to `smart/config.json` as `cart_trigger`.
2. Run `friday.py watchlist`/`codes`/`ingest`/`propose`/`meals` as in runbook §A steps 2–7 (read-only: no cart writes) so the page has real data. Requires the user signed in to woolworths.com.au in Chrome with Claude in Chrome connected.
3. Build the page with `python3 smart/build_page.py <today>` (fills `__BOOK__`, `__DATA__`, `__PRICED__`, `__TODAY__`, `__COOKS__` and `__CART_TRIGGER__`). Load the artifact-capabilities skill, then publish `smart/page_publish.html` as a NEW artifact titled "<NAME>'s Kitchen" with capabilities `db`, `downloads`, `assets` and `mcp` (the Claude Code Remote connector's `fire_trigger` tool, so Confirm complete can start the cart task). Save its URL to `smart/config.json` as `page_url`, and update the cart task's prompt with the URL.
4. Seed the database as in §A step 8, plus:
   - `settings/holidays` ← `{region, updated, source, holidays:[{date, name}], notes}` from the interview.
   - `settings/events` ← `{events:[{series, name, from, to, local}], spoilers:"avoid"|"ok", preview_day}` (empty `events` if they follow nothing).
   - one welcome note in `notes`: `{kind:"helper", status:"done", created, text}` in the butler's voice, explaining that notes left here are seen to each evening.

## 4. Scheduled tasks
Create these in the user's timezone (`CRON_TZ=<tz>`), each requiring the user's computer with the folder attached, with prompts that name the folder and page URL and say "follow the Claude's Kitchen runbook section X". Offer to change days/times first:
- Friday 5:48am — weekly proposal / specials refresh (§A). It must leave a week whose `weekly/flow.status` is "placed" alone.
- Every evening ~7:48pm — order check (§E; read-only). When the current list's order is found it starts the next list straight away (§E 5b).
- Every night ~9:45pm — evening notes (§G): act on notes, reply once, weekly holiday/event preview on the preview day, never spoilers if they asked.
- Every night ~10:18pm — pantry tidy (§F).
- (Already made in step 3) the on-request cart run (§C), fired by **Confirm complete**.
Tell the user which approval setting each task got.

## 5. Finish
Tell the user in 3–4 lines: where the page is, when the first proposal arrives, that they can leave notes for <NAME> at the top of the page, that nothing reaches their cart until they press Confirm complete, and that checkout is always theirs (press **I've placed the order** once they've paid).
