URM_fix.bat - installs URM into any Ren'Py game
===============================================

URM is built into this file. There is nothing else to download and nothing
to copy around.

Some games ship a modified Ren'Py that writes its script files in its own
encrypted format and refuses to load anything a normal Ren'Py produced. Drop
URM into one of those and the game dies on startup with:

    Exception: Could not load from archive 0x52-URM/classes/API.rpyc.

This file installs URM either way. On a game like that it re-encodes URM to
match; on a normal game it just installs it. You do not have to know which
kind you have.


HOW TO USE
----------

1. Put URM_fix.bat in the game folder - the one with the game's .exe in it,
   next to game\ and renpy\.

2. Double-click it.

3. Press 1, then start the game. URM's tab is in the top-left corner once
   you are in-game.

You can also drag a game folder onto URM_fix.bat instead of step 1.

The only file it writes is game\0x52_URM.rpa. It never reads or touches the
game's own archives.


THE MENU
--------

  1) Install URM into this game
       Does everything. Start here.

  2) Patch the engine instead
       A fallback. Instead of converting URM, this teaches the game's engine
       to read normal URM files. Only worth using if option 1 reports that it
       cannot work on your game.

  3) Undo the engine patch
       Reverses option 2.

  4) Show me what this game does
       Prints the Ren'Py version, whether the game encrypts its scripts, what
       is in game\, and which engine files the game hash-checks. Changes
       nothing.


UPDATING URM
------------

Put a newer 0x52_URM.rpa next to URM_fix.bat and press 1 - a copy sitting
beside the .bat is always used in preference to the built-in one. A copy you
already installed into game\ is used ahead of the built-in one too.


IF SOMETHING GOES WRONG
-----------------------

  "Could not find the game's bundled Python"
      URM_fix.bat is not inside the game folder. Move it next to the .exe.

  "No module named 'store.x52URM'"
      A save made with URM cannot be opened without URM present. Install URM
      into that copy of the game and the save opens normally. The save is not
      damaged.

  "Could not load image ...: Unsupported image format"
      Nothing to do with URM - there is UnRen output sitting in game\. On
      these games extraction bypasses the asset decryption, so the unpacked
      files are unreadable and shadow the real archives. Delete them.


URM is 0x52's work, not mine. If you pass this on, keep the credit and a link
to the original thread.
