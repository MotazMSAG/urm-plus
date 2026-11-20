# UX rules for anything URM+ shows the player

The reader is a **player in the middle of a scene**, glancing at the overlay
for two seconds before clicking a choice. Not a developer reading a debugger.
Every screen, card, notification and tooltip is judged against that.

This file exists because of a real failure: the "Choices detected" maze
cards (2026-11-19) were correct but unreadable - raw variable names, label
names like `ch3choice6_done`, `== "no"`, "1 always", "+1 more checked later",
the same flag repeated under every choice, 15 lines for a 2-option menu.
The user's verdict: "notifications have become unhuman, it's now for AI
consumption". Accuracy is necessary; it is not sufficient.

## Scope

These rules cover **every** display in URM and URM+: the ones being built
and the ones already there (the variable window and its panel, flags, alerts,
search, options, URM's own screens that URM+ patches). When the user shows
one bad display, it is an example of a class - sweep the rest for the same
problem (2026-11-19: "I give examples not to fix that specific example, but
to understand what I mean and apply it on everything").

## Rules

0. **Consistency.** The same thing looks and behaves the same wherever it is
   opened from: one window per kind of thing, the same actions in the same
   place, the same words and colours for the same meaning. The user's
   example: a variable opened from a notification offers Delete; the same
   variable in the remembered list does not. "URM and URM+ are full of
   inconsistency and things that look different depending on where you
   opened it from." A new entry point reuses the existing component; it
   never gets its own variant.
1. **Answer the player's question first.** For a choice that question is
   "what does this get me, and does it matter?" - in words. Mechanism
   (which label, which line, which operator) comes second, on demand.
2. **Translate, don't transcribe.** `carol_love += 1` reads "Carol: love +1".
   `ch3bloody = "yes"` reads "the bloody version of the next scene". Code
   view stays one click away for people who want it.
3. **Show the difference between choices, not their union.** A flag every
   choice sets to the same value is not information. A flag every choice
   sets to different values is the whole point - lead with it.
4. **No plumbing on the default view.** Label names, file:line, "always",
   "2 choices, 2 open", "+N more", condition operators: hidden until asked.
5. **Budget: about 3 short lines per choice.** If it does not fit, the
   design is wrong, not the font size.
6. **Put information where the eye already is** - on or beside the thing it
   describes (the choice button), not in a panel across the screen.
7. **Say when something does not matter.** "Flavour only - nothing later
   checks this" is one of the most useful things we can tell a player.
8. **Turn later checks into goals.** "Chapter 4 needs Carol's nerve 3 - you
   have 1" beats "checked later: carol_nerve >= 3 (ch04begin)".
9. **Colour and icons carry meaning, text carries detail.** Gain / loss /
   neutral should be readable without reading. **A status that can be good
   or bad is never grey text**: it is a chip in a tone - green (met,
   reachable), amber (tight, differs), red (short, not reachable). The user,
   about a grey "Reachable by playing" line: "I just don't like that its
   grey, so I have to notice it and read it because it looks the same if I
   can reach the points goal or not". This covers every such line: "needs 3,
   you have 1" on the cards and the map footer, the verdict in the variable
   window, whether a rung can still be reached. Grey is for things that have
   no good or bad side (a label name, a count).
10. **Anything that can cover the game can be closed.** A notification that
    hides what is behind it gets a close button; closing lasts until the
    situation changes (the next choice), so nothing disappears for good
    without the player knowing where it went.
11. **No breadcrumbs.** Never write a route as "Right › Leave" or
    "Check out the noise › Go to my left". Where something sits (its column
    on the map, its indent on a card) already says how you got there; each
    step shows only its own text. To link a route to something further away,
    use its colour (a lane, a dot), not a spelled-out path. The user: it
    "feels like it's counter to the entire idea of the map".
12. **One shape, one meaning.** On the map a card is a choice the player
    makes, and the first screen teaches that. Anything else - the game
    deciding by itself, a scene that plays in versions, a place where paths
    meet - must look different (another border, no number, its own header),
    or the player will read it as more choices. The user, about condition
    branches drawn as cards: it "gives the impression that those are 2
    different paths ... since it trains you from the beginning that a card =
    scene".
13. **Don't say what the shape already says.** A ◆ inside a block means
    "a check that only changes some lines" - no words after it. A menu
    that splits the path is drawn as the split, never also named in a block;
    only a menu whose options all rejoin unchanged gets an icon inside its
    block. A check inside a block that *does* something without splitting
    (points given later for an earlier choice) shows its chips: ◆
    `Carol love +2`. The user: "don't be verbose, I'm not retarded";
    colour carrying meaning ("green gives points") is the kind of thing that
    works.
14. **Look at it before calling it done.** Headless tests prove the data, not
    the reading. Mock it up (a rendered mockup in chat is fine) or ask the
    user for a screenshot; never ship a new display unseen.

15. **Never show a box whose only content is an apology.** "Goes on off
    the map" in an otherwise empty box told the player nothing about the
    option and looked like a defect - and it was one: the option had not
    been read. If something cannot be shown, either read it properly or
    draw that it continues (three dashes off the box); never fill a box
    with the tool's own limits. The user: "sometimes many many options are
    off the map" (2026-11-20).
16. **A mark belongs to what it stands next to.** A lone check diamond
    drawn in front of a chip reads as that chip's check. Marks that qualify
    a chip go in front of it; marks that stand alone go after the chips.
17. **Nothing gets a box unless it has something to say.** A merge with no
    changes is a dot on the track; a scene name with nothing under it is
    not drawn. Every empty box is a column the player has to drag past.
18. **Size follows content.** Every box as tall as the tallest made a
    2,600 px map of mostly empty space. Things take the room they need.
19. **Put it where the eye is, and let the player move it.** The branch
    chip went from the top corner to bottom left, on the quick menu's row,
    "closer to dialogue for me to see" - and since every game uses that
    corner differently, it is a drag that stays where it is dropped.
20. **One mark per cause.** Things that happen under the same check stand
    together behind ONE diamond, not one diamond each: four chips with four
    diamonds read as four checks. What happens anyway comes first, without
    a mark (the user's pick "A", 2026-11-20).
21. **Show what holds now.** Of several outcomes, the ones that will not
    happen as the game stands are faded - never hidden, never faded on a
    guess: when it cannot be told, nothing is faded.
22. **A size is asked, not guessed.** A box is as large as what the engine
    will draw in it (`Text.size`, as URM does). A height worked out apart
    from the layout that draws the content drew a chip outside its box.
23. **What a mark says appears beside the mark.** A hover text in a fixed
    place far from the mouse (the map's header) ran under what was already
    there and made the eye travel. It is a bubble beside the mark, inside
    what is in view, never on the mark itself, at the side where it covers
    nothing a box says - not the chips the mark stands for, not the title
    of the way it leads to - standing a little off the mark when it must
    (the user's pick "1b", 2026-11-20; the second half learnt from the
    1:1 drawings). The place of every mark that can be pointed at is worked
    out by the layout and checked against the engine's own
    (`map_trace.py`, "screen").
24. **Marks on a line never stand side by side, and each has one meaning.**
    Big diamond: the game picks the way. Small diamond: only lines change.
    Where one would stand beside the other there is one mark, and it says
    both. Nothing marks what the lines already show: paths that join need
    no ring (pick "2b"). The legend names exactly the marks on the screen.
25. **A way the game picks is titled with its reason, and shows where the
    player stands.** The test in plain words, then a chip for what the
    player has - green when the test holds as things stand, amber when
    not; "Otherwise" for the last way. Never "Yes" / "Or" (they say
    nothing without the line under them), never a script's own label,
    never code. One rule for two ways and for many, on every display that
    has the form (`urm_way_words`; pick "3a").
26. **Decide from the data, not from the picture.** "It looks mirrored"
    was two different things on one screenshot: the same statements walked
    twice (a fault, fixed in the walk) and a menu the author wrote twice
    (true, left alone). Rebuild the screen from the real game and read
    which statements stand behind each box before changing a drawing.

## The approved look (2026-11-19)

The route map was approved as-is ("perfect map"), and the user asked for
more of that style over URM's plain one ("much better than the brutal plain
URM"). Reuse it rather than inventing a new look per feature:

- **Word chips** coloured by tone: green = you gain, red = you lose,
  purple = sets something, plain = anything else. Same colours everywhere.
  A chip that starts "you:" is what the player has, after the test it
  belongs to: green = the test holds as things stand, amber = it does not.
- **Theme colours only**, through `urm_map_colour`, so every URM theme works.
- **Cards** on `buttonBgHover`, the player-facing text first (the real choice
  text, never "1 always"), muted italic notes for anything secondary.
- **Lines, not lists,** when something branches (the subway map).

## Known offender: the variable window (2026-11-19)

Shown by the user as "way too verbose ... this design is not human": a
sentence listing thresholds ("The numbers that change something: 1 or more,
4 or more, 5 or more, 6 or more"), three count sentences, a paragraph per
choice, two red warning lines, three tab buttons, then more text below. It
breaks rules 1, 4, 5 and 13. It is the worst case, not the only one - treat
every text-heavy URM+ panel as suspect until checked.

## Process - required for every new or changed display

- **Before building, propose at least three presentations**, including at
  least one unconventional one (a map, a goal tracker, prose, badges on the
  game's own buttons, colour only, sound...). Show them as quick visual
  mockups, say what each costs to build, recommend one, let the user pick.
- After building, check the result against the rules above and say which
  ones it still breaks.
- When the user reports a display problem, the fix is a design change, not
  a wording tweak - go back to the proposal step.
- **Be proactive.** Bring ideas without being asked, and argue against a
  request that would make the tool less consistent, more cluttered, slower
  or riskier - say why, offer a better option, then follow the decision.
  Suggesting is not building: unapproved ideas wait in IDEAS.md.
