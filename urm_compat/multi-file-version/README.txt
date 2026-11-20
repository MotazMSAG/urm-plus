URM for Ren'Py games that encrypt their script cache
====================================================

Some games ship a modified Ren'Py that writes its .rpyc files in its own
format and refuses to load anything a normal Ren'Py produced. Drop URM into
one of those and the game dies on startup with:

    Exception: Could not load from archive 0x52-URM/classes/API.rpyc.

This converts URM into the format that game expects, so it loads normally.
No game file is patched - the only thing that changes is the URM archive in
game/.


HOW TO USE
----------

1. Put this whole folder inside the game folder - the one containing the
   game's .exe, next to game/ and renpy/.

2. Double-click "INSTALL URM.bat".

3. Start the game normally. URM opens with the little tab in the top-left
   corner, same as always.

That's it. You can delete this folder afterwards if you like.

You can also drag a game folder onto "INSTALL URM.bat" instead of step 1.


IF YOU UPDATE URM
-----------------

Replace 0x52_URM.rpa in this folder with the new one and run the .bat again.
The conversion is tied to both the game and the URM build, so redo it for
each game and after each URM update.


IF IT DOES NOT WORK
-------------------

  "Could not find the game's bundled Python"
      The folder is not inside the game folder. Move it next to the .exe.

  Still "Could not load from archive" after installing
      That game encrypts its archives differently. Try the fallback route
      below.

  "Could not load image ...: Unsupported image format"
      You have UnRen output sitting in game/. On these games extraction
      bypasses the asset decryption, so the unpacked files are unreadable
      and shadow the real archives. Delete them from game/.

Fallback route - patches the engine instead of converting URM, which means
you can then drop in any URM build without re-running anything:

    python install.py --check "<game folder>"
    python install.py "<game folder>"
    python install.py --uninstall "<game folder>"

--check reports what the build does and which engine files it hash-checks,
without changing anything.


WHAT IS IN HERE
---------------

  INSTALL URM.bat     double-click this
  repack.py           does the conversion
  hyperlink_fix.rpy   compiled into the archive; see below
  0x52_URM.rpa        URM itself - replace to update
  install.py          fallback route
  modcompat.py        used by the fallback route


ABOUT hyperlink_fix.rpy
-----------------------

Separate problem, worth having either way. URM's variable and label editors
are registered as link protocols. A game that sets config.hyperlink_callback,
usually to open its Patreon or Discord link in a browser, makes Ren'Py throw
away the code that routes protocols - so clicking a variable in URM asks
Windows to find an app for a "urmvardialog:" link instead of opening the
editor. This puts the routing back and leaves the game's own links working.


URM is 0x52's work, not mine. If you pass this on, keep the credit and a
link to the original thread.
