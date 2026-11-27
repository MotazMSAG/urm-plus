"""
The new map's story line drawn by each prop's own engine (37_newmap_view,
game_screens/37_newmap; the user's picks 1b(20) and 3a).

    python check_newmap_drawn.py <props folder> [--pictures <folder>]

Each prop's engine is started read-only with its `lint` command replaced,
on a base folder of its own (a temporary folder: nothing is written to the
prop): game/ holds URM's archive as URM ships it, the add-on as the one file a player can install
(make_rpy.build()), our fonts, a small story of our own words and the
probe. The probe asks the model from the story's lines as if the game
stood there (no call around it), builds the cards and lays out and renders
the screen with the engine: a short reply (the note), a way 20 lines
longer (a lane that comes back), a check of the game 20 lines apart (the
big diamond), versions of one value (the block, folded and opened), a way
that ends the game (red). What the engine drew is read back as words.

--pictures writes the screen as the engine drew it, 1:1, per engine.

An engine that reads only archives the installer re-encodes is skipped
here (check_saves.py has the installed way); at least two engines must be
checked.
"""
# run_tests: props
# prop_probe: standalone

from __future__ import print_function

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import prop_probes  # noqa  (shared 1-boot-per-prop runner)

def said(text, n, indent):
    return u"\n".join(u'%s"%s %d."' % (u" " * indent, text, i) for i in range(n))


# The drawings' own made-up stretch (research/newmap q1 panel b, q3 panel a),
# with their line counts: so the pictures can be laid beside the drawings.
STORY = u"""
label nmd_start:
    "Start."
    menu:
        "Tell her the truth":
            $ carol_trust += 1
            $ nerve += 1
%s
        "Distract her":
%s
        "Open the door":
%s
            return
    "Supplies."
    menu:
        "I go":
%s
        "Ted goes":
%s
        "Let Carol choose" if carol_nerve >= 3:
%s
    jump nmd_search
label nmd_search:
    "Search."
    menu:
        "Search the hospital":
%s
        "Search the mall":
%s
    "Later."
    if branch == "Jill":
%s
    elif branch == "Isabella":
%s
    elif branch == "Sage":
%s
    else:
%s
    jump nmd_checks
label nmd_checks:
    "Night."
    if carol_trust >= 1:
%s
    else:
        "Carol is quiet."
    if carol_nerve >= 5:
%s
    elif nerve >= 3:
        "A short word."
    else:
        "Another short word."
    if nerve >= 1:
        jump nmd_hold
    "Not yet."
label nmd_back:
    if carol_trust > 5:
        "The end, together."
        return
    "Morning again."
    return
label nmd_hold:
    "You hold her hand."
    jump nmd_back
label nmd_tail_dot:
    if carol_trust > 5:
        "Leaves early."
        return
    "Loop back."
    jump nmd_tail_dot
label nmd_roam_entry:
    menu:
        "Explore":
            jump nmd_roam_hub
        "Finish":
            jump nmd_roam_done
label nmd_roam_hub:
    $ nmd_roam_room = "nmd_roam_hub"
    menu:
        "Dorm":
            jump nmd_roam_dorm
        "Walk East":
            jump nmd_roam_cafe
        "Phone":
            "Call to continue."
            jump nmd_roam_done
label nmd_roam_dorm:
    if carol_trust >= 2:
        jump nmd_roam_dorm_ev
    "Dorm empty."
    jump nmd_roam_go
label nmd_roam_dorm_ev:
    "Dorm evening."
    jump nmd_roam_go
label nmd_roam_cafe:
    $ nmd_roam_room = "nmd_roam_cafe"
    menu:
        "Coffee":
            "Coffee."
            jump nmd_roam_go
        "Walk West":
            jump nmd_roam_hub
label nmd_roam_go:
    $ renpy.jump(nmd_roam_room)
label nmd_roam_done:
    "Episode continues."
    return
label nmd_sandbox_hub:
    $ nmd_sb_room = "nmd_sandbox_hub"
    menu:
        "Library":
            jump nmd_sb_lib
        "Courtyard":
            jump nmd_sb_cafe
        "Gym":
            jump nmd_sb_gym
label nmd_sb_lib:
    if carol_nerve >= 3:
        jump nmd_sb_lib_ev
    jump nmd_sb_go
label nmd_sb_lib_ev:
    "Special study."
    jump nmd_sb_go
label nmd_sb_gym:
    if nerve >= 0:
        jump nmd_sb_gym_ev
    jump nmd_sb_go
label nmd_sb_gym_ev:
    "Training."
    jump nmd_sb_go
label nmd_sb_cafe:
    $ nmd_sb_room = "nmd_sb_cafe"
    menu:
        "Coffee break":
            "Coffee break."
            jump nmd_sb_go
        "Back inside":
            jump nmd_sandbox_hub
label nmd_sb_go:
    $ renpy.jump(nmd_sb_room)
""" % (said("Truth line", 37, 12), said("Distract line", 30, 12), said("Door line", 4, 12),
       said("I go line", 20, 12), said("Ted line", 15, 12), said("Carol line", 18, 12),
       said("Hospital line", 310, 12), said("Mall line", 180, 12),
       said("Jill line", 500, 8), said("Isabella line", 247, 8), said("Sage line", 221, 8),
       said("Other line", 40, 8), said("Trust line", 25, 8), said("Brave line", 30, 8))

PROBE_CODE = u'''
init 1999 python:
    _nmd_last = []
    _nmd_at = []     # (words, x, y) of every text drawn, where it sits on screen

    def _nmd_words(opened, picture=None):
        """The screen laid out and rendered by the engine: the words drawn;
        with picture, also written into that PNG."""
        root = renpy.display.layout.Fixed()
        sd = renpy.display.screen.ScreenDisplayable(
            renpy.display.screen.get_screen_variant("urmnm_story"), "urmnm_story", "screens",
            scope={"_kwargs": {}, "_urmnmOpen": opened})
        sd.update()
        sd.visit_all(lambda d: d.per_interact())
        root.add(sd)
        _nmd_last[:] = [sd]
        rv = renpy.display.render.render_screen(root, config.screen_width, config.screen_height)
        out = []
        _nmd_at[:] = []

        def walk(r, x, y):
            for d in getattr(r, "render_of", ()) or ():
                if isinstance(d, renpy.text.text.Text):
                    said = u"".join(t for t in d.text if isinstance(t, (type(u""), type(""))))
                    out.append(said)
                    _nmd_at.append((said, x, y))
            for c in r.children:
                if isinstance(c[0], renpy.display.render.Render):
                    walk(c[0], x + c[1], y + c[2])
        walk(rv, 0, 0)
        if picture:
            import pygame_sdl2 as pygame
            surf = pygame.Surface((config.screen_width, config.screen_height), pygame.SRCALPHA)
            surf.fill((0, 0, 0, 255))
            renpy.display.swdraw.draw(surf, None, rv, 0, 0, True)
            pygame.image.save(surf, picture)
        return out

    def _nmd_cards(label, steps):
        node = renpy.game.script.lookup(label)
        store._urmsg_here = lambda: node
        store._urmsg_live_stack = lambda: ()
        st = urmnm_view()
        urmnm_story_load(urmnm_model(None, steps))
        return st.cards

    def _nmd_probe(lines, check, pic):
        was_here = getattr(store, "_urmsg_here", None)
        was_stack = getattr(store, "_urmsg_live_stack", None)
        try:
            store.carol_trust, store.nerve, store.carol_nerve, store.branch = 0, 0, 1, "Jill"
            _urmsg_stretches()

            check("the story line is shown in the menu alongside Route map for side-by-side comparison",
                  "story_line" in _urm_offers().entries and _urm_offers().entries["story_line"].shown())
            short_cards = _nmd_cards("nmd_short_checks", 2)
            short_words = _nmd_words((), pic("short_check_diamonds"))
            check("only the next connector carries the 6 and 12 line checks, in order",
                  len(short_cards) == 2 and not short_cards[0].short_checks
                  and [(n, large) for n, large, _tip in short_cards[1].short_checks]
                  == [("+6", False), ("+12", True)]
                  and "+6" in short_words and "+12" in short_words and "+4" not in short_words
                  and "extra dialogue" in short_words,
                  repr(([c.short_checks for c in short_cards], short_words)))
            check("hover words name the conditions behind the extra lines",
                  [tip for _n, _size, tip in short_cards[1].short_checks]
                  == ["nerve is at least 3", "carol_trust is at least 2"],
                  repr(short_cards[1].short_checks))
            sd = _nmd_last[0]
            focus = renpy.display.focus
            was_mouse = renpy.get_mouse_pos
            size = urmnm_font_px(16, 13)
            gap = urmk_px_cut(16)
            first = next((x, y + urmk_px_cut(18)) for words, x, y in _nmd_at if words == "+6")
            try:
                for i, (mouse, expected) in enumerate([
                        (first, "nerve is at least 3"),
                        ((config.screen_width - 2, first[1]), "carol_trust is at least 2")]):
                    renpy.get_mouse_pos = lambda: mouse
                    focus.set_focused(sd.widgets[("short_check", 1, i)], None, sd)
                    hovered = _nmd_words((), pic("short_check_hover_%s" % i))
                    boxes = [(x, y) for words, x, y in _nmd_at if words == expected]
                    top = min(y for words, _x, y in _nmd_at if words.startswith("meet again after"))
                    check("hover draws the whole condition above the card captions and inside the screen",
                          len(boxes) == 1 and hovered.count(expected) == 1 and
                          gap <= boxes[0][0] <= config.screen_width - gap - urmnm_text_w(expected, size)
                          and boxes[0][1] + size + urmk_px_cut(6) < top,
                          repr((mouse, boxes, top, hovered)))
            finally:
                renpy.get_mouse_pos = was_mouse
                focus.set_focused(None, None, None)
            nested = _nmd_cards("nmd_nested_checks", 1)[0].short_checks
            check("nested extra dialogue includes its enclosing condition",
                  nested == (("+6", False, "nerve is at least 3 and carol_trust is at least 2"),
                             ("+12", True, "nerve is under 3 and carol_trust is at least 4")),
                  repr(nested))
            alternate = _nmd_cards("nmd_alternate_checks", 1)[0].short_checks
            check("each qualifying alternative keeps its own count and condition",
                  alternate == (("+6", False, "nerve is at least 3"),
                                ("+12", True, "nerve is under 3 and carol_trust is at least 2")),
                  repr(alternate))
            mixed = _nmd_cards("nmd_mixed_checks", 2)
            check("a short check in one arm does not hide the full card in its sibling",
                  mixed[0].title == "The game checks" and mixed[0].mark == "big"
                  and mixed[0].short_checks
                  == (("+6", False, "nerve is at least 3 and carol_trust is at least 2"),),
                  repr([(c.title, c.mark, c.short_checks) for c in mixed]))
            check("a check after the full card appears only on its outgoing connector",
                  len(mixed) == 2
                  and mixed[1].short_checks == (("+8", False, "carol_nerve is at least 5"),),
                  repr([(c.title, c.short_checks) for c in mixed]))
            wrapped = _nmd_cards("nmd_wrapped_mixed_checks", 2)
            check("the full-card boundary also holds inside a scene condition",
                  [(c.title, [n for n, _size, _tip in c.short_checks]) for c in wrapped]
                  == [("The game checks", ["+6"]), ("You choose", ["+8"])],
                  repr([(c.title, c.short_checks) for c in wrapped]))
            cards = _nmd_cards("nmd_start", 4)
            words = _nmd_words((), pic("1_story_line"))
            check("four cards: three choices, then the versions", [(c.title, c.versions is not None) for c in cards]
                  == [("You choose", False)] * 3 + [("The game checks", True)], repr([c.title for c in cards]))
            check("the options numbered; 37 and 30 lines of their own: both leave the line (the user's rule); the "
                  "door drops in red; the ways meet again at a box",
                  "YOU ARE HERE" in words and "1" in words and "Tell her the truth" in words
                  and u"3 \u00b7 the game ends" in words and "Ways meet again" in words
                  and [(l.words, l.cap) for l in cards[0].lanes] == [("Tell her the truth", None), ("Distract her", None), ("Open the door", "end")], repr(words))
            check("q1b: the second card's closed option says what it needs",
                  [r.have for r in cards[1].rows][2] == (u"carol_nerve 1/3", "loss"), repr(cards[1].rows[2].have))
            # The line is wider than a screen: the rest is drawn from the third split.
            cards = _nmd_cards("nmd_search", 2)
            words = _nmd_words((), pic("2_fork_versions"))
            check("q1b, the user's b: the hospital is 130 lines longer than the mall: both leave the line, each in its box, and meet again at a box",
                  [(l.words, l.cap) for l in cards[0].lanes] == [("Search the hospital", None), ("Search the mall", None)]
                  and u"1 \u00b7 ~310 lines" in words and u"2 \u00b7 ~180 lines" in words and "Ways meet again" in words
                  and u"\u201cLater.\u201d" in words,
                  repr(([(l.words, l.cap) for l in cards[0].lanes], cards[0].meet_line, words)))
            check("q3a: one dashed block, yours lit with its length, the others folded",
                  "Plays in 4 versions" in words and "you: true" in words and "branch is Jill" in words
                  and not [w for w in words if "Nmd" in w or "nmd" in w] and "3 other versions" in words
                  and "Isabella line 0." not in words, repr(words))
            words = _nmd_words((1,), pic("3_versions_open"))
            check("q3a opened in place: every version, the others 'you: false'",
                  words.count("you: false") == 3 and "Otherwise" in words and "fold" in words
                  and not [w for w in words if "other version" in w], repr(words))
            store.branch = None
            del store.branch
            cards = _nmd_cards("nmd_search", 2)
            words = _nmd_words((), pic("4_versions_undecided"))
            check("q3a: the route not decided yet: nothing lit", "not decided yet" in words
                  and "4 versions" in words and "you: true" not in words, repr(words))
            store.branch = "Jill"
            cards = _nmd_cards("nmd_checks", 4)
            words = _nmd_words((), pic("5_game_checks"))
            check("splits the game decides: one that splits has no card, its test on the diamond; one that "
                  "does not split stays a bordered card",
                  [c.title for c in cards][:3] == ["The game checks"] * 3 and cards[0].mark == "big"
                  and cards[2].mark == "small" and "carol_trust is at least 1" in words
                  and u"carol_trust is at least 1 \u00b7 ~25 lines" in words and "Otherwise" in words
                  and urmnm_check_split(cards[0]) and not urmnm_check_split(cards[2]),
                  repr([(c.title, c.mark, [(l.words, l.cap) for l in c.lanes]) for c in cards]))
            store.nerve = 3
            cards = _nmd_cards("nmd_checks", 4)
            words = _nmd_words((), pic("7_check_two_stay"))
            # Where each staying way is drawn: on its own row, never on top of the other.
            nerve = [(x, y) for said, x, y in _nmd_at if said == "nerve is at least 3"]
            other = [(x, y) for said, x, y in _nmd_at if said == "Otherwise"
                     and nerve and abs(x - nerve[0][0]) < 40]
            check("a check that splits with two ways staying: both named in one box on the line, each on its "
                  "own row (never on top of each other), the holding one bright",
                  nerve and other and abs(other[0][1] - nerve[0][1]) >= 10
                  and "nerve is at least 3" in words and "Otherwise" in words and words.count("as things stand") >= 1
                  and len(cards) > 1 and [l.words for l in cards[1].lanes] == ["carol_nerve is at least 5"],
                  repr(([(c.title, [l.words for l in c.lanes]) for c in cards], nerve, other)))
            store.nerve = 0
            cards = _nmd_cards("nmd_back", 2)
            words = _nmd_words((), pic("6_game_check_ends"))
            check("a game check whose way ends the game fans out to the right in neutral words, never game over",
                  cards and [l.cap for l in cards[0].lanes] == ["end", "end"] and u"carol_trust is over 5 \u00b7 the game ends" in words
                  and u"Otherwise \u00b7 the game ends" in words
                  and not [w for w in words if "game over" in w], repr(words))
            import pickle
            scope = dict((k, w) for k, w in _nmd_last[0].scope.items() if k.startswith("_urmnm"))
            try:
                pickle.dumps(scope, 2)
                kept = None
            except Exception as e:
                kept = repr(e)
            def _plain_scope(v):
                if v is None or isinstance(v, (bool, int, float) + (type(u""), type(""))):
                    return True
                if isinstance(v, (tuple, list)):
                    return all(_plain_scope(x) for x in v)
                return False
            bad_scope = dict((k, type(w).__name__) for k, w in scope.items() if not _plain_scope(w))
            check("a save with the version block drawn: the screen's scope holds plain builtins only and pickles",
                  kept is None and not bad_scope, "" if (kept is None and not bad_scope) else repr((kept, bad_scope)))
            dot_cards = _nmd_cards("nmd_tail_dot", 1)
            dot_words = _nmd_words((), pic("8_last_card_end_dot"))
            check("a last card whose lane ends renders its staying row and end dot cleanly",
                  dot_cards and [l.cap for l in dot_cards[0].lanes] == ["end"]
                  and bool(urmnm_staying_rows(dot_cards[0])) and "Otherwise" in dot_words
                  and u"carol_trust is over 5 \u00b7 the game ends" in dot_words,
                  repr(([(l.words, l.cap) for l in dot_cards[0].lanes] if dot_cards else [], dot_words)))
            st_parity = urmnm_view()
            st_parity.later = ((u"At ending: carol_trust is at least 2", u"0/2", "loss", "carol_trust"),)
            parity_words = _nmd_words((), pic("9_parity_footer_overview"))
            st_parity.later = ()
            check("goals footer renders 'What these choices decide later' and chips cleanly alongside overview",
                  "What these choices decide later" in parity_words
                  and "At ending: carol_trust is at least 2" in parity_words
                  and "0/2" in parity_words,
                  repr(parity_words))
            # Wave 5.3 Free roam and Sandbox views drawn
            roam_cards = _nmd_cards("nmd_roam_hub", 4)
            roam_words = _nmd_words((), pic("10_free_roam"))
            check("q2b Free roam draws dashed frame, place rows, needs chip, and moves the story on",
                  roam_cards and getattr(roam_cards[0], "roam", False)
                  and "Free roam" in roam_words and "Dorm" in roam_words and "Phone" in roam_words
                  and "moves the story on" in roam_words,
                  repr((getattr(roam_cards[0], "roam", None) if roam_cards else None, roam_words)))
            sb_cards = _nmd_cards("nmd_sandbox_hub", 4)
            sb_words = _nmd_words((), pic("11_sandbox"))
            check("q4a Sandbox draws by-place cards with open and needs chips and pickle-safe scope",
                  sb_cards and urmnm_story_mode() == "sandbox"
                  and "Sandbox" in sb_words and "Library" in sb_words and "Gym" in sb_words
                  and "open" in sb_words,
                  repr((urmnm_story_mode(), sb_words)))
        finally:
            if was_here is not None:
                store._urmsg_here = was_here
            if was_stack is not None:
                store._urmsg_live_stack = was_stack
            for name in ("carol_trust", "nerve", "carol_nerve", "branch"):
                if hasattr(store, name):
                    delattr(store, name)
'''

SHORT_CHECKS = u"""
label nmd_short_checks:
    menu:
        "Tell her the truth":
            "A moment passes."
        "Play it cool":
            "Another moment passes."
    "The room falls quiet."
    if nerve >= 3:
%s
    "A bell rings."
    if carol_trust >= 2:
%s
    "The door opens."
    if nerve >= 2:
%s
    "They wait."
    menu:
        "Sympathize with her":
            "That's difficult."
        "Be practical":
            "Let's go."
    return
label nmd_nested_checks:
    if nerve >= 3:
        if carol_trust >= 2:
%s
    else:
        if carol_trust >= 4:
%s
    "They wait."
    menu:
        "Speak":
            "Hello."
        "Leave":
            "Goodbye."
    return
label nmd_alternate_checks:
    if nerve >= 3:
%s
    elif carol_trust >= 2:
%s
    "They wait."
    menu:
        "Speak":
            "Hello."
        "Leave":
            "Goodbye."
    return
label nmd_mixed_checks:
    if nerve >= 3:
        if carol_trust >= 2:
%s
    else:
        if carol_trust >= 4:
%s
    "They wait."
    if carol_nerve >= 5:
%s
    "The room quiets."
    menu:
        "Speak":
            "Hello."
        "Leave":
            "Goodbye."
    return
""" % (said("Courage", 6, 8), said("Trust", 12, 8), said("Pause", 4, 8),
       said("Nested", 6, 12), said("Other nested branch", 12, 12),
       said("Courage", 6, 8), said("Trust", 12, 8),
       said("Short sibling", 6, 12), said("Long sibling", 25, 12), said("After rejoin", 8, 8))

WRAPPED = u'\nlabel nmd_wrapped_mixed_checks:\n    if branch == "Jill":\n'
WRAPPED_BODY, WRAPPED_CONTINUATION = SHORT_CHECKS.split("label nmd_mixed_checks:\n")[-1].split("\n    menu:", 1)
WRAPPED += u"\n".join(u"    " + line for line in WRAPPED_BODY.splitlines())
# Keep the alternate arm from reaching the later menu before the existing
# breadth-first search has found the large check in Jill's arm.
WRAPPED += u"\n    else:\n" + u"        pass\n" * 8
WRAPPED += u"\n    menu:" + WRAPPED_CONTINUATION
PROBE_FILES = {"nmd_story.rpy": (STORY + SHORT_CHECKS + WRAPPED).encode("utf-8")}
PROBE_ENTRY = "_nmd_probe"
PROBE_PIC_ENV = "URMNMD_PICTURES"
PROBE_TAG_ENV = "URMNMD_TAG"
PROBE_MIN_ENGINES = 2


if __name__ == "__main__":
    sys.exit(prop_probes.main_single(__file__, sys.argv))
