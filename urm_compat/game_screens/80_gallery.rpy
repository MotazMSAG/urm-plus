# The gallery switch in the corner of the menus (_urmg_interact). It keeps
# the older displays' look.

screen urmg_badge():
    zorder 1001
    style_prefix "urmk_old"
    textbutton urmg_badge_text() text_size urmk_px_cut(17) xalign 1.0 yalign 0.0 xoffset -urmk_px_cut(10) yoffset urmk_px_cut(8) substitute False action Function(urmg_toggle)
