# The corner line shown while the script index is built
# (_urmi_progress_text).

screen urmi_progress():
    zorder 1000
    add DynamicDisplayable(_urmi_progress_text) xpos 12 yalign 1.0 yoffset -10
