# Custom behaviors shipped by this module (see src/behaviors/). Behaviors
# only run on the central, mirroring how ZMK itself builds them.
if ((NOT CONFIG_ZMK_SPLIT) OR CONFIG_ZMK_SPLIT_ROLE_CENTRAL)
  target_sources_ifdef(CONFIG_ZMK_BEHAVIOR_CAPS_WORD_EXT app PRIVATE src/behaviors/behavior_caps_word_ext.c)
endif()
