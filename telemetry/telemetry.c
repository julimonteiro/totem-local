/* Local-only TOTEM telemetry; no typed text is persisted by the companion. */
#include <zephyr/kernel.h>
#include <zephyr/sys/printk.h>
#include <zephyr/bluetooth/gatt.h>
#include <zephyr/bluetooth/conn.h>
#include <zmk/event_manager.h>
#include <zmk/battery.h>
#include <zmk/usb.h>
#include <zmk/events/battery_state_changed.h>
#include <zmk/events/position_state_changed.h>
#include <zmk/events/split_peripheral_status_changed.h>
#if IS_ENABLED(CONFIG_ZMK_SPLIT_ROLE_CENTRAL)
#include <zmk/keymap.h>
#include <zmk/ble.h>
#include <zmk/endpoints.h>
#include <zmk/events/layer_state_changed.h>
#include <zmk/events/keycode_state_changed.h>
#endif
#include "build_id.h"

static int battery = -1;
static int peer_battery = -1;
static bool split_connected;
static uint64_t pressed;
static uint8_t held_modifiers;

#if IS_ENABLED(CONFIG_ZMK_SPLIT_ROLE_CENTRAL)
#define SIDE "left"
#define SIDE_ID 0
#else
#define SIDE "right"
#define SIDE_ID 1
#endif

/* Packet v1: version, side, battery, peer battery, flags, layer, profile,
 * five bytes pressed positions (little endian), four-byte build identity. */
static uint8_t packet[16];
#if IS_ENABLED(CONFIG_ZMK_SPLIT_ROLE_CENTRAL)
#define SERVICE_UUID BT_UUID_DECLARE_128(BT_UUID_128_ENCODE(0x5fbc1000,0x6c8d,0x4f43,0xa01a,0xa6d18a88c001))
#define STATE_UUID BT_UUID_DECLARE_128(BT_UUID_128_ENCODE(0x5fbc1001,0x6c8d,0x4f43,0xa01a,0xa6d18a88c001))
#define OUTPUT_UUID BT_UUID_DECLARE_128(BT_UUID_128_ENCODE(0x5fbc1002,0x6c8d,0x4f43,0xa01a,0xa6d18a88c001))
static ssize_t read_state(struct bt_conn *conn, const struct bt_gatt_attr *attr,
                         void *buf, uint16_t len, uint16_t offset) {
    return bt_gatt_attr_read(conn, attr, buf, len, offset, packet, sizeof(packet));
}
BT_GATT_SERVICE_DEFINE(totem_service,
    BT_GATT_PRIMARY_SERVICE(SERVICE_UUID),
    BT_GATT_CHARACTERISTIC(STATE_UUID, BT_GATT_CHRC_READ | BT_GATT_CHRC_NOTIFY,
                           BT_GATT_PERM_READ_ENCRYPT, read_state, NULL, NULL),
    BT_GATT_CCC(NULL, BT_GATT_PERM_READ_ENCRYPT | BT_GATT_PERM_WRITE_ENCRYPT),
    BT_GATT_CHARACTERISTIC(OUTPUT_UUID, BT_GATT_CHRC_NOTIFY, BT_GATT_PERM_NONE, NULL, NULL, NULL),
    BT_GATT_CCC(NULL, BT_GATT_PERM_READ_ENCRYPT | BT_GATT_PERM_WRITE_ENCRYPT));
#endif

#if IS_ENABLED(CONFIG_ZMK_SPLIT_ROLE_CENTRAL)
static void inspect_connection(struct bt_conn *conn, void *data) {
    struct bt_conn_info info;
    if (!bt_conn_get_info(conn, &info) && info.role == BT_CONN_ROLE_CENTRAL && info.state == BT_CONN_STATE_CONNECTED) {
        *(bool *)data = true;
    }
}
#endif

static void emit_state(bool serial) {
    int layer = -1, profile = -1, endpoint = -1;
    bool host = false;
#if IS_ENABLED(CONFIG_ZMK_SPLIT_ROLE_CENTRAL)
    split_connected = false;
    bt_conn_foreach(BT_CONN_TYPE_LE, inspect_connection, &split_connected);
    if (!split_connected) peer_battery = -1;
    layer = zmk_keymap_highest_layer_active();
    profile = zmk_ble_active_profile_index();
    host = zmk_ble_active_profile_is_connected();
    endpoint = zmk_endpoints_selected().transport;
#endif
    bool usb = zmk_usb_is_powered();
    bool hid = zmk_usb_is_hid_ready();
    uint8_t flags = (usb ? 1 : 0) | (hid ? 2 : 0) | (host ? 4 : 0) |
                    (split_connected ? 8 : 0) | (endpoint == 1 ? 16 : 0);
    packet[0] = 1; packet[1] = SIDE_ID;
    packet[2] = battery < 0 ? 255 : battery;
    packet[3] = peer_battery < 0 ? 255 : peer_battery;
    packet[4] = flags; packet[5] = layer < 0 ? 255 : layer;
    packet[6] = profile < 0 ? 255 : profile;
    for (int i = 0; i < 5; i++) packet[7 + i] = (pressed >> (8 * i)) & 255;
    for (int i = 0; i < 4; i++) packet[12 + i] = (TOTEM_BUILD_NUMBER >> (8 * i)) & 255;
    if (serial && usb) {
        printk("TOTEM_STATE {\"side\":\"" SIDE "\",\"battery\":%d,\"peer_battery\":%d,\"usb\":%d,\"usb_hid\":%d,\"ble\":%d,\"split\":%d,\"layer\":%d,\"profile\":%d,\"endpoint\":%d,\"pressed\":%llu,\"build\":\"" TOTEM_BUILD_ID "\"}\n",
            battery, peer_battery, usb, hid, host, split_connected, layer, profile, endpoint,
            (unsigned long long)pressed);
    }
#if IS_ENABLED(CONFIG_ZMK_SPLIT_ROLE_CENTRAL)
    bt_gatt_notify(NULL, &totem_service.attrs[2], packet, sizeof(packet));
#endif
}

static void tick(struct k_work *work);
K_WORK_DELAYABLE_DEFINE(state_work, tick);
static void tick(struct k_work *work) {
    emit_state(true);
    k_work_reschedule(&state_work, K_SECONDS(1));
}

static int event_handler(const zmk_event_t *eh) {
    const struct zmk_battery_state_changed *b = as_zmk_battery_state_changed(eh);
    if (b) battery = b->state_of_charge;
    const struct zmk_position_state_changed *p = as_zmk_position_state_changed(eh);
    if (p && p->position < 38) {
        if (p->state) pressed |= (UINT64_C(1) << p->position);
        else pressed &= ~(UINT64_C(1) << p->position);
        if (zmk_usb_is_powered()) printk("TOTEM_KEY {\"side\":\"" SIDE "\",\"position\":%u,\"pressed\":%d}\n", p->position, p->state);
        emit_state(true);
    }
    const struct zmk_split_peripheral_status_changed *s = as_zmk_split_peripheral_status_changed(eh);
    if (s) {
        split_connected = s->connected;
        if (!s->connected) peer_battery = -1;
    }
#if IS_ENABLED(CONFIG_ZMK_SPLIT_ROLE_CENTRAL) && IS_ENABLED(CONFIG_ZMK_SPLIT_BLE_CENTRAL_BATTERY_LEVEL_FETCHING)
    const struct zmk_peripheral_battery_state_changed *pb = as_zmk_peripheral_battery_state_changed(eh);
    if (pb) peer_battery = pb->state_of_charge;
#endif
#if IS_ENABLED(CONFIG_ZMK_SPLIT_ROLE_CENTRAL)
    const struct zmk_layer_state_changed *layer = as_zmk_layer_state_changed(eh);
    if (layer) emit_state(true);
    const struct zmk_keycode_state_changed *key = as_zmk_keycode_state_changed(eh);
    if (key) {
        if (key->usage_page == 7 && key->keycode >= 224 && key->keycode <= 231) {
            uint8_t bit = 1U << (key->keycode - 224);
            if (key->state) held_modifiers |= bit;
            else held_modifiers &= ~bit;
        }
        uint8_t mods = held_modifiers | key->implicit_modifiers | key->explicit_modifiers;
        if (zmk_usb_is_powered()) printk("TOTEM_OUTPUT {\"side\":\"left\",\"output\":{\"page\":%u,\"code\":%u,\"mods\":%u,\"pressed\":%d}}\n", key->usage_page, key->keycode, mods, key->state);
        uint8_t out[8] = {1, key->usage_page & 255, key->usage_page >> 8, key->keycode & 255, key->keycode >> 8, mods, key->state, 0};
        bt_gatt_notify(NULL, &totem_service.attrs[5], out, sizeof(out));
    }
#endif
    return ZMK_EV_EVENT_BUBBLE;
}
ZMK_LISTENER(totem_local, event_handler);
ZMK_SUBSCRIPTION(totem_local, zmk_battery_state_changed);
ZMK_SUBSCRIPTION(totem_local, zmk_position_state_changed);
ZMK_SUBSCRIPTION(totem_local, zmk_split_peripheral_status_changed);
#if IS_ENABLED(CONFIG_ZMK_SPLIT_ROLE_CENTRAL)
ZMK_SUBSCRIPTION(totem_local, zmk_layer_state_changed);
ZMK_SUBSCRIPTION(totem_local, zmk_keycode_state_changed);
#endif
#if IS_ENABLED(CONFIG_ZMK_SPLIT_ROLE_CENTRAL) && IS_ENABLED(CONFIG_ZMK_SPLIT_BLE_CENTRAL_BATTERY_LEVEL_FETCHING)
ZMK_SUBSCRIPTION(totem_local, zmk_peripheral_battery_state_changed);
#endif
static int telemetry_init(void) {
    k_work_reschedule(&state_work, K_SECONDS(3));
    return 0;
}
SYS_INIT(telemetry_init, APPLICATION, 99);
