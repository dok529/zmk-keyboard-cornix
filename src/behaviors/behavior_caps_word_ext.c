/*
 * Copyright (c) 2021 The ZMK Contributors
 *
 * SPDX-License-Identifier: MIT
 *
 * Copy of ZMK's behavior_caps_word.c (app/src/behaviors/) with two extra
 * lists, for OS keyboard layouts whose letters don't all live on the HID
 * A-Z keycodes (Colemak: "o" is on SEMI, ";" is on P):
 *
 *   shift-list: keys outside A-Z that are shifted and keep caps word on
 *   break-list: keys inside A-Z that are NOT shifted and end caps word
 *
 * Everything else behaves exactly like upstream caps word. If upstream
 * changes behavior_caps_word.c, compare and carry the changes over here.
 */

#define DT_DRV_COMPAT zmk_behavior_caps_word_ext

#include <zephyr/device.h>
#include <drivers/behavior.h>
#include <zephyr/logging/log.h>
#include <zmk/behavior.h>

#include <zmk/endpoints.h>
#include <zmk/event_manager.h>
#include <zmk/events/position_state_changed.h>
#include <zmk/events/keycode_state_changed.h>
#include <zmk/events/modifiers_state_changed.h>
#include <zmk/keys.h>
#include <zmk/hid.h>
#include <zmk/keymap.h>

LOG_MODULE_DECLARE(zmk, CONFIG_ZMK_LOG_LEVEL);

#if DT_HAS_COMPAT_STATUS_OKAY(DT_DRV_COMPAT)

struct caps_word_item {
    uint16_t page;
    uint32_t id;
    uint8_t implicit_modifiers;
};

struct behavior_caps_word_ext_config {
    zmk_mod_flags_t mods;
    const struct caps_word_item *continuations;
    uint8_t continuations_count;
    const struct caps_word_item *shifts;
    uint8_t shifts_count;
    const struct caps_word_item *breaks;
    uint8_t breaks_count;
};

struct behavior_caps_word_ext_data {
    bool active;
};

static void activate_caps_word(const struct device *dev) {
    struct behavior_caps_word_ext_data *data = dev->data;

    data->active = true;
}

static void deactivate_caps_word(const struct device *dev) {
    struct behavior_caps_word_ext_data *data = dev->data;

    data->active = false;
}

static int on_caps_word_binding_pressed(struct zmk_behavior_binding *binding,
                                        struct zmk_behavior_binding_event event) {
    const struct device *dev = zmk_behavior_get_binding(binding->behavior_dev);
    struct behavior_caps_word_ext_data *data = dev->data;

    if (data->active) {
        deactivate_caps_word(dev);
    } else {
        activate_caps_word(dev);
    }

    return ZMK_BEHAVIOR_OPAQUE;
}

static int on_caps_word_binding_released(struct zmk_behavior_binding *binding,
                                         struct zmk_behavior_binding_event event) {
    return ZMK_BEHAVIOR_OPAQUE;
}

static const struct behavior_driver_api behavior_caps_word_ext_driver_api = {
    .binding_pressed = on_caps_word_binding_pressed,
    .binding_released = on_caps_word_binding_released,
#if IS_ENABLED(CONFIG_ZMK_BEHAVIOR_METADATA)
    .get_parameter_metadata = zmk_behavior_get_empty_param_metadata,
#endif // IS_ENABLED(CONFIG_ZMK_BEHAVIOR_METADATA)
};

static int caps_word_keycode_state_changed_listener(const zmk_event_t *eh);

ZMK_LISTENER(behavior_caps_word_ext, caps_word_keycode_state_changed_listener);
ZMK_SUBSCRIPTION(behavior_caps_word_ext, zmk_keycode_state_changed);

#define GET_DEV(inst) DEVICE_DT_INST_GET(inst),
static const struct device *devs[] = {DT_INST_FOREACH_STATUS_OKAY(GET_DEV)};

static bool caps_word_is_caps_includelist(const struct behavior_caps_word_ext_config *config,
                                          uint16_t usage_page, uint8_t usage_id,
                                          uint8_t implicit_modifiers) {
    for (int i = 0; i < config->continuations_count; i++) {
        const struct caps_word_item *continuation = &config->continuations[i];
        LOG_DBG("Comparing with 0x%02X - 0x%02X (with implicit mods: 0x%02X)", continuation->page,
                continuation->id, continuation->implicit_modifiers);

        if (continuation->page == usage_page && continuation->id == usage_id &&
            (continuation->implicit_modifiers &
             (implicit_modifiers | zmk_hid_get_explicit_mods())) ==
                continuation->implicit_modifiers) {
            LOG_DBG("Continuing capsword, found included usage: 0x%02X - 0x%02X", usage_page,
                    usage_id);
            return true;
        }
    }

    return false;
}

// shift-list / break-list match on the key alone, ignoring modifiers.
static bool caps_word_in_list(const struct caps_word_item *items, uint8_t count,
                              uint16_t usage_page, uint8_t usage_id) {
    for (int i = 0; i < count; i++) {
        if (items[i].page == usage_page && items[i].id == usage_id) {
            return true;
        }
    }

    return false;
}

static bool caps_word_is_alpha(uint8_t usage_id) {
    return (usage_id >= HID_USAGE_KEY_KEYBOARD_A && usage_id <= HID_USAGE_KEY_KEYBOARD_Z);
}

static bool caps_word_is_numeric(uint8_t usage_id) {
    return (usage_id >= HID_USAGE_KEY_KEYBOARD_1_AND_EXCLAMATION &&
            usage_id <= HID_USAGE_KEY_KEYBOARD_0_AND_RIGHT_PARENTHESIS);
}

// A "letter" of the OS layout: A-Z minus break-list, plus shift-list.
static bool caps_word_is_letter(const struct behavior_caps_word_ext_config *config,
                                uint16_t usage_page, uint8_t usage_id) {
    if (caps_word_in_list(config->shifts, config->shifts_count, usage_page, usage_id)) {
        return true;
    }

    return usage_page == HID_USAGE_KEY && caps_word_is_alpha(usage_id) &&
           !caps_word_in_list(config->breaks, config->breaks_count, usage_page, usage_id);
}

static void caps_word_enhance_usage(const struct behavior_caps_word_ext_config *config,
                                    struct zmk_keycode_state_changed *ev) {
    if (!caps_word_is_letter(config, ev->usage_page, ev->keycode)) {
        return;
    }

    LOG_DBG("Enhancing usage 0x%02X with modifiers: 0x%02X", ev->keycode, config->mods);
    ev->implicit_modifiers |= config->mods;
}

static int caps_word_keycode_state_changed_listener(const zmk_event_t *eh) {
    struct zmk_keycode_state_changed *ev = as_zmk_keycode_state_changed(eh);
    if (ev == NULL || !ev->state) {
        return ZMK_EV_EVENT_BUBBLE;
    }

    for (int i = 0; i < ARRAY_SIZE(devs); i++) {
        const struct device *dev = devs[i];

        struct behavior_caps_word_ext_data *data = dev->data;
        if (!data->active) {
            continue;
        }

        const struct behavior_caps_word_ext_config *config = dev->config;

        caps_word_enhance_usage(config, ev);

        if (!caps_word_is_letter(config, ev->usage_page, ev->keycode) &&
            !caps_word_is_numeric(ev->keycode) && !is_mod(ev->usage_page, ev->keycode) &&
            !caps_word_is_caps_includelist(config, ev->usage_page, ev->keycode,
                                           ev->implicit_modifiers)) {
            LOG_DBG("Deactivating caps_word for 0x%02X - 0x%02X", ev->usage_page, ev->keycode);
            deactivate_caps_word(dev);
        }
    }

    return ZMK_EV_EVENT_BUBBLE;
}

#define PARSE_ITEM(i)                                                                              \
    {.page = ZMK_HID_USAGE_PAGE(i), .id = ZMK_HID_USAGE_ID(i), .implicit_modifiers = SELECT_MODS(i)}

#define LIST_ITEM(i, n, prop) PARSE_ITEM(DT_INST_PROP_BY_IDX(n, prop, i))

#define LIST_LEN(n, prop) DT_INST_PROP_LEN_OR(n, prop, 0)

// +1 so an absent/empty list still yields a valid (unused) array.
#define LIST_ARRAY(n, prop)                                                                        \
    static const struct caps_word_item caps_word_ext_##prop##_##n[LIST_LEN(n, prop) + 1] = {      \
        LISTIFY(LIST_LEN(n, prop), LIST_ITEM, (, ), n, prop)};

#define KP_INST(n)                                                                                 \
    LIST_ARRAY(n, continue_list)                                                                   \
    LIST_ARRAY(n, shift_list)                                                                      \
    LIST_ARRAY(n, break_list)                                                                      \
    static struct behavior_caps_word_ext_data behavior_caps_word_ext_data_##n = {.active = false}; \
    static const struct behavior_caps_word_ext_config behavior_caps_word_ext_config_##n = {        \
        .mods = DT_INST_PROP_OR(n, mods, MOD_LSFT),                                                \
        .continuations = caps_word_ext_continue_list_##n,                                          \
        .continuations_count = LIST_LEN(n, continue_list),                                         \
        .shifts = caps_word_ext_shift_list_##n,                                                    \
        .shifts_count = LIST_LEN(n, shift_list),                                                   \
        .breaks = caps_word_ext_break_list_##n,                                                    \
        .breaks_count = LIST_LEN(n, break_list),                                                   \
    };                                                                                             \
    BEHAVIOR_DT_INST_DEFINE(n, NULL, NULL, &behavior_caps_word_ext_data_##n,                       \
                            &behavior_caps_word_ext_config_##n, POST_KERNEL,                       \
                            CONFIG_KERNEL_INIT_PRIORITY_DEFAULT,                                   \
                            &behavior_caps_word_ext_driver_api);

DT_INST_FOREACH_STATUS_OKAY(KP_INST)

#endif
