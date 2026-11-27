# Multiversal Ren'Py Mod (MRM)

MRM adds choices and checks, a visual Story line, search, variable tools,
scene replay, save browsing, and play controls to Ren'Py games on Windows.
It grew out of URM+ and was inspired by the original Universal Ren'Py Mod
by 0x52. MRM runs independently. [0x52's website](https://0x52.dev/)

## Install

1. Download **URM_fix.bat** from the [latest GitHub release](https://github.com/MotazMSAG/urm-plus/releases/latest).
2. Close the game. Put the BAT next to the game's executable and choose
   **Install MRM**, or drag the game folder onto the BAT.
3. Start the game and click **MRM** or press **Alt+U**. Press **Alt+F**
   for Search, **Alt+G** for Story line when available, or **Alt+O** for Console.

The installer writes one mod archive, `game/urmplus.rpa`, using the game's
Ren'Py compiler. The release gate covers Ren'Py 7.3.5 through 8.5.0 on
Windows. Story and scene tools depend on what MRM can read in each game.

## What you can do

- **Follow the story.** Review choice effects and conditions, follow
  branches through Story line, or inspect places and exits in Free roam.
- **Find and inspect.** Search for variables, flags, lines and choices.
  Inspect thresholds and source in supported scenes, remember useful
  results, edit values, replay eligible scenes, and manage Alerts & Mutes.
- **Control play.** Pause on checks, configure skip and rollback behavior,
  customize Quick access, and browse saves in Timeline or Pages.
- **Make dialogue easier to read.** Use the game's own textbox, Glass strip,
  or Subtitles, adjust textbox opacity, and rename detected characters.

## Update, switch from URM, or remove

In MRM, open **Settings → Updates**. If a newer release is offered,
save before choosing **Close & install**. To update manually, download the
current BAT and run **Install MRM** again with the game closed.

If you used original URM in this game, keep your saves. Move any existing
`game/0x52_URM.rpa` and extracted `game/0x52-URM` folder outside `game/`
as backups before switching to standalone MRM. This also applies to a
combined URM and URM+ install made before the separate `urmplus.rpa`.
MRM supports legacy saves that used original URM names.

To remove MRM, close the game and move `game/urmplus.rpa` out of `game/`.
Keep your saves. Legacy saves that refer to original URM objects need
either original URM or MRM to read those names.

## Build from source

Run `python urm_compat/single/build.py` to create `dist/URM_fix.bat`.
See [LICENSE](LICENSE) for the source licence and
[urm_compat/fonts](urm_compat/fonts) for bundled font notices.
