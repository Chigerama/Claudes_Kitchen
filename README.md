# Claude's Kitchen

A weekly Woolworths (Australia) grocery and meal-planning assistant, packaged as a plugin for the Claude desktop app.

Claude acts as your household's butler. It learns what you buy from your own order history, checks prices and genuine specials each week, suggests dinners that suit the week's weather and season, takes notes from you on a private page, and adds to your Woolworths cart **only what you confirm**. Checkout and payment are always yours.

> **Unofficial project.** This is a community plugin. It is not made, endorsed or supported by Anthropic or Woolworths.
>
> **Unofficial interface.** Claude talks to Woolworths through the same web interface your browser uses while you're signed in. It is not an official or supported API: it may change or break without notice, and you use it at your own risk and subject to Woolworths' terms. Claude never checks out, pays, enters passwords or changes account settings, and stops if Woolworths asks for sign-in or a CAPTCHA.

## Features at a glance

**Shopping**
- Learns your usual products, quantities and how often you buy them from your past orders, grouping similar products together.
- Builds a weekly list of core items, things due for a re-buy, and genuine specials. Price history is used to spot items that are "on special" almost every week.
- Suggests stock-ups on long-life items when the discount is deep, and holds back items you're overstocked on.
- "We're out of…" list: type items in your own words and Claude matches them to your usual product or the best option on Woolworths.
- Never order list, brand alternatives, "buy whichever is cheaper" and rotating products.
- Reads each delivered order back from your Woolworths account, so you don't need to keep saving invoices, and starts the next week's list automatically.

**Meals**
- Twelve dinner ideas each week, matched to the evening forecast and the season, with five pre-picked.
- Adjustable serves, optional vegetables (remembered), shuffle for new ideas, and a full recipe book you can add from.
- Favours recipes that use what's already in your pantry and learns which meals your household keeps choosing.
- Dinner schedule for the next seven nights, with who's cooking.
- Paprika export, recipe photos, and a **User notes** box on every recipe.

**Your private page**
- A five-step weekly flow: Specials → Core items → Meals → Extra items → Review & send.
- **Confirm complete** fills your cart straight away. **I've placed the order** locks the week until the order is read back.
- **A word with Claude**: leave notes (a new recipe, a change of rules, a product nickname) and Claude acts on them each evening and replies.
- Plans around your public holidays and any events you follow (for example a sports season), with a no-spoilers mode for people who watch later.

**Safety**
- Nothing reaches your cart until you confirm it, and Claude never checks out, pays or touches account settings.
- All your data stays in your own folder and your own private page.

---

## 1. What you need

| Requirement | Why |
|---|---|
| A Claude plan with **Cowork** and the **Claude desktop app** | Runs Claude and the scheduled tasks |
| A **folder on your computer** linked to the task | Holds your history, settings and recipes |
| **Claude in Chrome**, signed in to woolworths.com.au | Price checks, reading orders, adding approved items |
| **4 or more Woolworths tax-invoice PDFs** (10+ is better) | Your starting purchase history |
| **Python 3** on your computer | Runs the engine (setup installs `pdfplumber` if missing) |

To get invoices: woolworths.com.au → **My Account → Orders** → **Download** on each tax invoice. Save them all into one folder.

---

## 2. Installation

1. Download `claudes-kitchen.plugin` from this repository's **Releases** page (or zip the repository's contents yourself and rename the file to `.plugin`). In the Claude desktop app, open the file or drag it into a chat, and press **Install**.
2. Start a new Cowork task from the desktop app with your computer linked.
3. Make sure Chrome is open, the Claude in Chrome extension is connected, and you're signed in to Woolworths.

---

## 3. Setup

Say **"set up Claude's Kitchen"**. Claude walks you through it:

1. **Connect your invoices folder.** Claude copies its engine and starter files into a `smart/` subfolder. Nothing existing is overwritten.
2. **Reads your history.** Invoices are turned into a purchase history, and similar products are grouped (e.g. all chicken breast cuts count as one item). You'll see your top 20 items.
3. **Asks a few questions:**
   - **Name.** "Claude" is the default; pick any name.
   - **Household.** First names of the people who cook, for the dinner schedule.
   - **City and timezone.** Used for the weather forecast and schedule. Only the city is stored.
   - **Public holidays.** Which state or region's public and bank holidays apply, so Claude can plan around them.
   - **Events you follow.** Any sports or other events you plan meals around, and whether you watch live or delayed. If delayed, Claude never mentions results (no spoilers).
   - **Core items.** Things you want on the list every week (milk, eggs, bread…).
   - **Never buy.** Things Claude should never suggest.
   - **Recipes.** Keep the starter dinners or remove any you don't eat.
4. **Publishes your page.** A private claude.ai page where you review and approve each week. Only you can open it unless you share it.
5. **Creates five scheduled tasks** in your timezone (you can change the times):

| When | What | Changes your cart? |
|---|---|---|
| Friday ~6am | Weekly list: staples, genuine specials, 12 dinner ideas (or a specials refresh of a list you haven't finished) | No |
| When you press **Confirm complete** | Adds everything you confirmed to your cart | Yes, confirmed items only |
| Every evening ~7:50pm | Reads your delivered order from the website, then starts next week's list | No |
| Every night ~9:45pm | Reads your notes, does what you asked, and replies on the page | No |
| Every night ~10:20pm | Tidies the "In the pantry…" list | No |

After setup you don't need to save invoice PDFs any more. Claude reads each delivered order from your Woolworths account. Saving a PDF still works and replaces the website copy for that order.

---

## 4. Using Claude each week

Your page is ready from Friday morning (or straight after your last order arrives). Work through it whenever suits; there's no fixed cart day.

### A word with Claude
At the top of the page. Leave Claude a note in plain words: a new recipe to add, a change to how he shops, a product nickname, a complaint about the bananas. Choose who it's from and press **Leave note**. Each evening Claude does what you asked and replies in the same box, saying exactly what he changed. The box keeps a fixed height and scrolls. On the preview day (Thursday by default) he also mentions any public holiday coming up and what's on in the events you follow, never results if you watch delayed.

### This week's dinners
Tonight's dinner and who's cooking, then the next six nights. Pick a dinner for each night from this week's meals (or Leftovers / Eating out / Takeaway) and tap who's cooking. Each night links to its recipe.

### This week's shop: five steps
1. **Specials**: genuine specials on things you usually buy. Claude checks price history, so an item that's "on special" most weeks isn't treated as a special.
2. **Core items**: weekly regulars, drinks and anything due for a re-buy.
3. **Meals**: twelve dinners matched to the week's evening temperatures and the season, with 5 pre-picked. Adjust serves, untick ingredients you have, **Shuffle recipes** for new ideas, or add any recipe from the book.
4. **Extra items**: the "We're out of…" list. Type anything in your own words; Claude matches it to your usual product or the best option on Woolworths.
5. **Review & send**: check the lot and press **Confirm complete**. Claude adds it all to your Woolworths cart straight away (your computer needs to be on). **Reopen to make changes** if you need to.

Once you've checked out on Woolworths, press **I've placed the order** (two taps). The week locks until Claude reads the order back from your account, then next week's list starts automatically. Pressed it by mistake? Use **Undo**.

### I have extra…
Overstocked? Enter how many you have ("4 shampoo"). Claude holds the item back until you're down to about one usual buy's worth, then puts it back on the list when about 10 days' supply is left.

### In the pantry…
Everyday ingredients you keep on hand: sauces, spices, oils, stocks. Claude favours recipes that use them and leaves them out of the meal cost. He tidies duplicates and typos each night.

### Never order
Any product line has a **Never order** link. Claude won't suggest it again (and skips it in the cart run) until you undo it.

### Recipes
Browse all recipes on the page and filter them. Open one to see ingredients and method, change the serves, tick optional vegetables (remembered), add a photo, add it to this week's meals, or **Export to Paprika**. Each recipe has a **User notes** box: write something like "too salty, halve the soy" and Claude makes the change that evening, marks your note **[resolved]** so it's never done twice, and lists the change in the note box. **Delete recipe** (two taps) removes one; Claude keeps a backup.

### Talking to Claude
You can ask in chat at any time, for example:
- "Run the weekly proposal now" (builds a proposal; never touches the cart)
- "Add my approved items to the cart"
- "Never suggest X again" / "Always get 2 of Y"
- "I have 6 toilet rolls spare"
- "Add a recipe for …"
- "Push to cart" (if the page couldn't reach Claude)

---

## 5. Customisation

Settings live in your folder, mainly `smart/rules.json`. The easiest way to change anything is to ask Claude in chat ("make milk a core item, 2 each week"). If you edit the files yourself, keep them valid JSON, and changes apply from the next run.

### Things most households should review in the first few weeks

| What | Where | Example |
|---|---|---|
| **Core items** (every week, fixed quantity) | `rules.json → core` | `"Milk 3L": 2, "Eggs": 1` |
| **Never buy** | `rules.json → never` | `["Soft drink cans"]` |
| **Brand alternatives** (fallbacks if your usual is out) | `rules.json → alternatives` | `"Coffee": ["Brand B 200g", "Brand C 250g"]` |
| **Buy whichever is cheaper** | `rules.json → cheapest` (plus `alternatives`) | `"cheapest": ["Sparkling water"]` |
| **Rotate between products** (variety week to week) | `rules.json → rotate` | `"Yoghurt": ["Flavour A", "Flavour B"]` |
| **Fixed buying cycle** (e.g. every 8 days) | `staples_policy → cycle_days` | `"Soda syrup": 8` |
| **Drinks** (suggested when due or on special) | `staples_policy → drink_groups`, `drink_patterns` | add `"kombucha"` |
| **Product grouping** (what counts as the same item) | `item_groups.csv` | `soda water\|mineral water,Sparkling water` |

### Specials and stock-ups

| Setting | Default | Meaning |
|---|---|---|
| `min_special_pct` | 20 | Minimum discount to count as a special |
| `stockup_special_pct` | 35 | Discount at which Claude suggests stocking up on long-life items |
| `stockup_weeks` | 6 | How many weeks' supply a stock-up covers |
| `stockup_max_multiple` | 4 | Never more than this × your usual quantity |
| `price_jump_pct` | 50 | Flags and unticks items this much above their usual price |
| `cheaper_per_unit_pct` | 10 | Flags an alternative this much cheaper per unit |
| `stock_buffer_days` | 10 | Days of supply left when an overstocked item comes back |

Household members for the dinner schedule: `rules.json → household_members` (e.g. `["Sam", "Alex"]`).

### Meals
- **Weather fit:** `rules.json → meal_weather`. Temperature bands for hearty, medium and light meals, the hot-day cap and the rain bonus. Raise the hearty thresholds if you like hearty food in warmer weather.
- **Seasons:** `rules.json → meal_seasons`. Set up for the Southern Hemisphere. **In the Northern Hemisphere, swap the months** (summer = Jun–Aug, etc.).
- **Dinner-only groups:** `rules.json → dinner_groups`. Items only bought for recipes, never as staples (e.g. mince, fresh herbs).
- **Recipes:** `smart/recipes.json`. Each ingredient is either a product group from your history (`g`, with a fallback product `fb`) or a specific product (`p`). Ask Claude to add, edit or remove recipes rather than editing by hand.

### Personality
Claude is written as a courteous, discreet household butler with a dry sense of humour, who very occasionally gets into a harmless tizz. Change the **Personality** paragraph at the top of `skills/kitchen-weekly/references/runbook.md` (or just ask) for a different voice.

### Schedule and identity
- **Times and days:** change the scheduled tasks in Cowork, or ask Claude ("move the weekly list to Thursday evening").
- **Holidays and events:** stored on your page (`settings/holidays`, `settings/events`). Ask Claude to add a series, drop one, change the preview day, or switch spoilers on or off.
- **Name:** `rules.json → household_name`. Ask Claude to rename the page as well.
- **Location:** `rules.json → timezone` and `location`. Update these if you move.

### Things Claude learns on its own
- Items you untick, or remove before checkout, score lower next time (`smart/learned.json`).
- Your out-of picks are remembered (`smart/outof_map.json`).
- Meals cooked in the last two weeks drop down the list (`smart/meal_history.json`).

To reset what Claude has learned, ask Claude to clear these files. Your purchase history is not affected.

---

## 6. Privacy

- Everything stays in your own folder and your own private page. This plugin contains no personal data, invoices or purchase history.
- When reading orders from the website, Claude keeps only the grocery lines: product, quantity, supplied, price. It saves no address, payment or rewards card details.
- Your location is stored only as a city, its coordinates and a timezone, and is used for the weather forecast (open-meteo.com).
- Notes you leave for Claude, your holidays and your events are stored only on your private page.

---

## 7. Troubleshooting

| Problem | Fix |
|---|---|
| "Signed out" or CAPTCHA reported | Sign in to Woolworths in Chrome, then ask Claude to re-run. |
| Scheduled run didn't happen | Your computer must be on with the Claude desktop app running and Chrome open. |
| An item is grouped wrongly | Ask Claude to fix the grouping, or add a line to `item_groups.csv`. |
| No order found after delivery | Claude checks every evening; you can also save the invoice PDF into your folder. |
| Confirm complete says it couldn't reach Claude | Make sure your computer is on with the Claude desktop app open, then press **Send to Claude again**, or say "push to cart" in chat. |
| Something changed on the Woolworths site | The unofficial interface may have changed. Save invoice PDFs and add items by hand until it's fixed. |

---

## 8. Files

- `engine/`: invoice reader, ranking, weekly engine (`friday.py`), page builder (`build_page.py`), website order reader (`order_extract.js`), page template
- `starter/`: starter rules, product groups and original starter recipes
- `skills/kitchen-setup`: first-time setup
- `skills/kitchen-weekly`: weekly runs (full runbook in `references/runbook.md`)

---

## License

Copyright © 2026 Chigerama. Released under the [MIT License](LICENSE).
