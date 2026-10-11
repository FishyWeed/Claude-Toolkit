---
name: design-directions
description: Use when the user asks you to create a new design system from scratch (a brand's or a product's colors, typography, components and spacing) and has not already fixed the visual direction. Instead of asking what direction they want, propose three distinct, visually rendered directions to choose from, then build the full system from their pick.
---

# Design directions: show options, don't ask

## When this applies

Use these instructions when I ask you to create a design system from scratch and you would normally ask me what design direction, style or mood I want.

They do not apply when:
- I'm extending, auditing or documenting an existing design system or brand guide. Follow that instead.
- I've already stated a concrete direction (specific colors, fonts and style). Build it directly.

## What to do instead of asking

Don't open with questions about style, mood, colors or fonts. Go straight to proposing directions.

### 1. Work from what I gave you

- Use my description: the product, audience, purpose and any adjectives or constraints I mentioned.
- If I give one inspiration (a brand, site, image or other reference), take cues from it: palette tendencies, type personality, shape language, density. Don't copy logos, trademarked assets or exact proprietary typefaces. The inspiration is optional; if I give none, work from the description alone.
- If my description is too thin to produce meaningfully different options, make reasonable assumptions and list them in up to three short lines (for example "Assuming a consumer mobile app for adults"). Then proceed. Don't stall with a list of questions.

### 2. Propose three distinct directions

- Default to **three** options. Use four only if my description is very open-ended. Never offer fewer than three.
- Make them truly different, not minor variations. Vary them on several axes at once: color temperature and saturation, typography personality (geometric, humanist, serif, mono), shape (sharp or rounded), density (airy or compact) and overall mood.
- If I gave an inspiration, make one option stay close to it and let the others deliberately diverge, so I can see the range.
- Label them A, B, C. Give each a short evocative name and a one-line rationale tied directly to my description, for example: "B · Field Notes: warm and tactile, matching the 'handmade, trustworthy' feel you described."

### 3. Render every option so I can choose by looking

- Use the best rendering method you have: an artifact, an HTML/CSS preview, an image or a canvas. Put all options on one page or view, side by side or stacked, so I can compare them at a glance.
- Give every option exactly the same layout, in the same order, with the same sample content:
  1. Name and one-line rationale
  2. Color palette: primary, secondary/accent, neutrals (background, surface, border, text) and semantic colors (success, warning, error), each as a swatch with its hex value
  3. Typography: font names, plus a specimen with a display heading, a section heading, body text and a small caption
  4. Buttons: primary, secondary and ghost/tertiary, with a hover or disabled state if possible
  5. Basic components: a text input with label, a card, a badge or tag, and an alert or toast
  6. Style cues: corner radius, shadow or elevation, and a strip showing the spacing scale
- Use fonts that actually load in your environment, such as web fonts or system stacks with named fallbacks. Pick colors that meet WCAG AA contrast for text.
- If you have no way to render visuals, fall back to a compact, comparable text specification for each option in the same order. Say once that a visual preview wasn't available.
- Keep the text around the previews short: assumptions (if any), then the options, then the next step.

### 4. Let me choose, combine or tweak

End with one line inviting me to pick, for example: "Pick A, B or C, or mix them (e.g. 'B's colors with A's type, rounder corners')."

- If I pick one option, confirm it in one line and start building.
- If I combine or tweak options, render the merged direction once in the same layout so I can confirm it. Skip this if the change is trivial.
- If I reject all of them, ask at most one focused question, or infer what was wrong from my reply. Then propose a fresh set of three that moves in the direction I indicated.

### 5. Build the full system from my choice

Once I've chosen, build the complete design system from that direction. Typically that includes:
- Design tokens: a full color scale per hue, semantic and state colors, light/dark modes if relevant, a type scale with line heights, spacing, radius, elevation and motion
- Components with their states
- Short usage guidance
- Accessibility notes

Keep every decision consistent with the direction I picked. Ask further questions only when a decision truly depends on information you can't reasonably assume.
