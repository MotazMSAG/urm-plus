# -*- coding: utf-8 -*-
"""
Script shapes every story-graph comparison runs over.

Each entry is a small Ren'Py script. Together they cover the shapes the
existing tests pin (mazes, plain menus, loops, calls, endings, the chapter 4
check) and the ones the walkers disagree on or were never tested with:
computed jumps and calls, a missing label, a while loop holding a menu, one
label called twice, a python jump plain and indented, nested ifs, empty arms,
a caption-only menu line, `if True`, a hub menu with `set`.

Label names are unique per script; scripts are loaded one at a time.
Statements that need the engine's run-time registrations (play, stop, pause,
scene with transitions) are left out: the bare parser rejects them.
"""

SCRIPTS = [

    ("now_and_then", u'''
label c6:
    if soaked == "early":
        "This test is before the choice."
    menu:
        "Left: Begin walking home now.":
            jump c6_left
        "Right: Try to find a gift for Elena now.":
            jump c6_right
    label c6_left:
        $ soaked = "no"
        $ sawhunters = "yes"
        "A cart rumbles by."
        jump c6_done
    label c6_right:
        $ sawhunters = "no"
        menu:
            "Look into the sound.":
                jump c6_check
            "Be wiser: Go home.":
                jump c6_leave
        label c6_leave:
                $ soaked = "no"
                jump c6_done
        label c6_check:
                menu:
                    "Go up the hill.":
                        jump c6_right2
                    "Go down below.":
                        jump c6_left2
                label c6_right2:
                    $ soaked = "no"
                    $ renpy.pause ()
                    jump c6_done
                label c6_left2:
                    $ elena_nerve += 1
                    $ elena_love += 1
                    $ soaked = "yes"
                    jump c6_done
label c6_done:
    $ chapter = 4
    if soaked == "no":
        "Still."
    return
'''),

    ("plain_menu", u'''
label p:
    menu:
        "Kiss her.":
            $ love += 1
            "She smiles."
        "Leave.":
            $ love -= 1
    $ after = 1
    return
'''),

    ("loop_back", u'''
label hall:
    "A hallway."
    menu:
        "North.":
            $ steps += 1
            jump hall
        "East.":
            jump hall_east
label hall_east:
    $ found_key = True
    jump out
label out:
    return
'''),

    ("calls_and_hops", u'''
label q:
    menu:
        "Help.":
            call q_help
            jump q_done
        "Python.":
            $ renpy.jump("q_py")
        "Depends.":
            if has_key:
                jump q_open
            else:
                jump q_done
label q_help:
    $ kindness += 2
    return
label q_py:
    $ py_flag = True
    jump q_done
label q_open:
    $ opened = True
    jump q_done
label q_done:
    $ after = 1
    return
'''),

    ("ending_arm", u'''
label e:
    menu:
        "Stay.":
            $ stayed = True
            jump e_done
        "Open the door.":
            $ dead = True
            return
label e_done:
    $ x = 1
    return
'''),

    ("shared_mid_label", u'''
label r:
    menu:
        "A.":
            menu:
                "A1.":
                    $ a1 = True
                    jump r_done
                "A2.":
                    $ a2 = True
                    jump r_mid
        "B.":
            $ b = True
            jump r_mid
label r_mid:
    $ m = True
    jump r_done
label r_done:
    $ after = 1
    return
'''),

    ("deferred_flag", u'''
label d:
    menu:
        "Take the left road.":
            $ path = "left"
        "Take the right road.":
            $ path = "right"
    "The roads meet again."
    jump d_later
label d_later:
    "Much later."
    if met_anna:
        "Anna waves."
    if path == "left":
        $ love += 1
    return
'''),

    ("bad_end_inside", u'''
label b:
    menu:
        "Run.":
            menu:
                "Into the woods.":
                    $ lost = True
                    return
                "Down the road.":
                    $ safe = 1
                    jump b_done
        "Hide.":
            $ safe = 2
            jump b_done
label b_done:
    if safe == 1:
        "Safe."
    return
'''),

    ("chapter_four", u'''
label a3:
    menu:
        "Left.":
            $ soaked = "no"
            jump a3_done
        "Right.":
            $ soaked = "yes"
            jump a3_done
label a3_done:
    if soaked == "no":
        "Still."
    else:
        "Loud."
label a_shower:
    $ persistent.saw_a_shower = True
    if soaked == "yes":
        "Scrub."
label a_movie:
    menu:
        "Comedy.":
            "Ha."
        "Drama.":
            "Hm."
    if met_before:
        $ elena_love += 2
label a4:
    menu:
        "Stay here and mind the old fire.":
            jump a4_mark
        "Send her to Tom's.":
            $ elena_trust += 1
            jump a4_elena
        "Let Elena choose.":
            $ elena_trust += 1
            if elena_nerve >= 3:
                "She thinks about it."
                jump a4_mark
            else:
                "She shrugs."
                jump a4_elena
    label a4_mark:
        "He goes."
        jump a4_done
    label a4_elena:
        "She goes."
    label a4_done:
        $ chapter = 5
    return
'''),

    ("gates", u'''
label g:
    "Before."
    if elena_love >= 3:
        $ ending = "good"
        jump g_good
    elif met:
        $ trust += 2
    else:
        $ trust -= 1
    "Between."
    if a == 1:
        jump g_one
    elif a == 2:
        jump g_two
    if b == 1:
        jump g_three
    jump g_four
label g_good:
    "Good."
    return
label g_one:
    "One."
    return
label g_two:
    "Two."
    return
label g_three:
    "Three."
    return
label g_four:
    "Four."
    return
'''),

    ("computed_targets", u'''
label ct:
    "Start."
    if pick == 1:
        jump expression target_var
    elif pick == 2:
        call expression target_var
        "Back."
    else:
        jump ct_missing_label
    "After."
    menu:
        "Go.":
            jump expression target_var
        "Call.":
            call expression target_var
            jump ct_done
        "Nowhere.":
            jump ct_missing_label
label ct_done:
    return
'''),

    ("while_with_menu", u'''
label w:
    $ n = 0
    while n < 3:
        "Round."
        menu:
            "Again.":
                $ n += 1
            "Stop.":
                jump w_done
    "Loop over."
label w_done:
    if n == 3:
        "Three rounds."
    return
'''),

    ("called_twice", u'''
label t:
    menu:
        "Twice.":
            call t_sub
            call t_sub
            jump t_done
        "Once.":
            call t_sub from t_site
            jump t_done
label t_sub:
    $ visits += 1
    return
label t_done:
    return
'''),

    # Idea 5 (design fix C4): one way calls a scene twice, and so does the
    # stretch after the paths meet. (In "called_twice" above the scene is
    # called by both ways, so it is taken for the meeting point and never
    # walked a second time.)
    ("twice_alone", u'''
label ta:
    menu:
        "Twice.":
            call ta_sub
            $ ta_a = 1
            call ta_sub
            jump ta_done
        "Once.":
            jump ta_done
label ta_sub:
    $ ta_visits += 1
    return
label ta_after:
    $ ta_later += 1
    return
label ta_done:
    call ta_after
    $ ta_b = 1
    call ta_after
    return
'''),

    # Idea 3 (design fix C2): two candidates for the meeting point that
    # tie - two labels that jump to each other, each way entering the round
    # at another of them.
    ("tied_rejoin", u'''
label tr:
    menu:
        "A.":
            jump tr_later
        "B.":
            jump tr_earlier
label tr_earlier:
    $ tr_e = 1
    jump tr_later
label tr_later:
    $ tr_l = 1
    jump tr_earlier
'''),

    ("python_hops", u'''
label h:
    "Start."
    python:
        counted = 1
        if counted:
            renpy.jump("h_inner")
    "Fell through."
    $ renpy.call("h_called")
    "After the call."
    $ renpy.jump("h_end")
label h_inner:
    "Inner."
    return
label h_called:
    $ was_called = True
    return
label h_end:
    return
'''),

    ("deep_and_empty", u'''
label n:
    if a:
        if b:
            if c:
                if d:
                    if e:
                        $ deep = 5
                        "Five down."
    if empty:
        pass
    else:
        $ other = 1
    if True:
        $ always = 1
    menu:
        "This line is only a caption."
        "First." if True:
            pass
        "Second." if unlocked:
            $ picked = 2
    "End."
    return
'''),

    ("hub_with_set", u'''
label hub:
    menu:
        set hub_seen
        "Kitchen.":
            jump hub_kitchen
        "Garden.":
            jump hub_garden
        "Leave.":
            jump hub_out
label hub_kitchen:
    $ saw_kitchen = True
    jump hub
label hub_garden:
    $ saw_garden = True
    jump hub
label hub_out:
    "Out."
    return
'''),

    ("lost_chains", u'''
label lc:
    "Start."
    if a == 1:
        $ x = 1
    jump lc_nowhere

label lc_two:
    "Second."
    if b == 1:
        $ y = 1
    jump expression lc_target

label lc_three:
    "Third."
    if c == 1:
        $ z = 1
    call lc_gone
    "After."

label lc_four:
    "Fourth."
    if d == 1:
        $ w = 1
    $ quiet = 1
    if e == 1:
        jump lc_two
    return
'''),

    ("eight_ifs", u'''
label many:
    "Start."
    if c1:
        $ v1 = 1
    if c2:
        $ v2 = 1
    if c3:
        $ v3 = 1
    if c4:
        $ v4 = 1
    if c5:
        $ v5 = 1
    if c6:
        $ v6 = 1
    if c7:
        $ v7 = 1
    if c8:
        $ v8 = 1
    if c9:
        $ v9 = 1
    "End."
    return
'''),

    # Idea 13, the user's pick 2a: a menu whose every option has a test is
    # passed when none holds - one more way, "If none apply". Last in the
    # list, so the scripts before it keep their numbers in a prop game.
    ("menu_all_tested", u'''
label mat:
    menu:
        "Look around.":
            jump mat_in
        "Leave.":
            jump mat_done
label mat_in:
    menu:
        "Kiss." if mat_love >= 3:
            $ mat_k = 1
        "Hug." if mat_trust >= 3:
            $ mat_h = 1
    $ mat_out = 1
    jump mat_done
label mat_done:
    return
'''),

    # The mirrored paths of Now and Then (_URMSG_FIX_MEET, 2026-11-20): the
    # ways share a scene of more than a dozen statements that one way goes
    # around - an option that jumps into another scene, which comes back
    # behind it. The ways meet where that scene comes back (bs_continue),
    # not at the first statement they share (bs_talk). Its shape is
    # script_part2.rpy:21014 of that game. Last in the list, so the scripts
    # before it keep their numbers in a prop game.
    ("bypassed_scene", u'''
label bs:
    menu:
        "Ask her.":
            menu:
                "Now.":
                    jump bs_talk
                "Not today.":
                    jump bs_alt
        "Say nothing.":
            jump bs_talk
label bs_talk:
    "Talk 1."
    "Talk 2."
    "Talk 3."
    "Talk 4."
    "Talk 5."
    "Talk 6."
    "Talk 7."
    "Talk 8."
    "Talk 9."
    "Talk 10."
    "Talk 11."
    "Talk 12."
    "Talk 13."
    "Talk 14."
    $ bs_talked = 1
label bs_continue:
    $ bs_done = 1
    return
label bs_alt:
    $ bs_alt_seen = 1
    jump bs_continue
'''),
]
