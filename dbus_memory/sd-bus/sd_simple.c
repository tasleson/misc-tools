#include <stddef.h>
#include <stdlib.h>
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>

#include <systemd/sd-bus.h>

// gcc -Wall -O2 sd_simple.c -o sd_simple `pkg-config --cflags --libs libsystemd`

struct object {
    const char *name;
    const char *uuid;
    uint32_t some_count;

    uint64_t u64_0;
    uint64_t u64_1;
    uint64_t u64_2;
    uint64_t u64_3;
    uint64_t u64_4;
    uint64_t u64_5;

    uint8_t b_0;
    uint8_t b_1;
    uint8_t b_2;
    uint8_t b_3;
    uint8_t b_4;
    uint8_t b_5;

    const char *s_0;
    const char *s_1;
    const char *s_2;
    const char *s_3;
    const char *s_4;
    const char *s_5;
    const char *s_6;
    const char *s_7;
};

static int method_hello(sd_bus_message *m, void *userdata, sd_bus_error *ret_error) {
    char *y = NULL;
    int r = 0;

    r = sd_bus_message_read(m, "s", &y);
    if (r < 0) {
        fprintf(stderr, "Failed to parse parameters: %s\n", strerror(-r));
        return r;
    }

    return sd_bus_reply_method_return(m, "s", y);
}

static const sd_bus_vtable vtable[] = {
    SD_BUS_VTABLE_START(0),
    SD_BUS_PROPERTY("Name", "s", NULL, offsetof(struct object, name), SD_BUS_VTABLE_PROPERTY_CONST),
    SD_BUS_PROPERTY("Uuid", "s", NULL, offsetof(struct object, uuid), SD_BUS_VTABLE_PROPERTY_CONST),
    SD_BUS_PROPERTY("SomeCount", "u", NULL, offsetof(struct object, some_count), SD_BUS_VTABLE_PROPERTY_CONST),

    SD_BUS_PROPERTY("U64_0", "t", NULL, offsetof(struct object, u64_0), SD_BUS_VTABLE_PROPERTY_CONST),
    SD_BUS_PROPERTY("U64_1", "t", NULL, offsetof(struct object, u64_1), SD_BUS_VTABLE_PROPERTY_CONST),
    SD_BUS_PROPERTY("U64_2", "t", NULL, offsetof(struct object, u64_2), SD_BUS_VTABLE_PROPERTY_CONST),
    SD_BUS_PROPERTY("U64_3", "t", NULL, offsetof(struct object, u64_3), SD_BUS_VTABLE_PROPERTY_CONST),
    SD_BUS_PROPERTY("U64_4", "t", NULL, offsetof(struct object, u64_4), SD_BUS_VTABLE_PROPERTY_CONST),
    SD_BUS_PROPERTY("U64_5", "t", NULL, offsetof(struct object, u64_5), SD_BUS_VTABLE_PROPERTY_CONST),

    SD_BUS_PROPERTY("b_0", "b", NULL, offsetof(struct object, b_0), SD_BUS_VTABLE_PROPERTY_CONST),
    SD_BUS_PROPERTY("b_1", "b", NULL, offsetof(struct object, b_1), SD_BUS_VTABLE_PROPERTY_CONST),
    SD_BUS_PROPERTY("b_2", "b", NULL, offsetof(struct object, b_2), SD_BUS_VTABLE_PROPERTY_CONST),
    SD_BUS_PROPERTY("b_3", "b", NULL, offsetof(struct object, b_3), SD_BUS_VTABLE_PROPERTY_CONST),
    SD_BUS_PROPERTY("b_4", "b", NULL, offsetof(struct object, b_4), SD_BUS_VTABLE_PROPERTY_CONST),
    SD_BUS_PROPERTY("b_5", "b", NULL, offsetof(struct object, b_5), SD_BUS_VTABLE_PROPERTY_CONST),

    SD_BUS_PROPERTY("string_d_0", "s", NULL, offsetof(struct object, s_0), SD_BUS_VTABLE_PROPERTY_CONST),
    SD_BUS_PROPERTY("string_d_1", "s", NULL, offsetof(struct object, s_1), SD_BUS_VTABLE_PROPERTY_CONST),
    SD_BUS_PROPERTY("string_d_2", "s", NULL, offsetof(struct object, s_2), SD_BUS_VTABLE_PROPERTY_CONST),
    SD_BUS_PROPERTY("string_d_3", "s", NULL, offsetof(struct object, s_3), SD_BUS_VTABLE_PROPERTY_CONST),
    SD_BUS_PROPERTY("string_d_4", "s", NULL, offsetof(struct object, s_4), SD_BUS_VTABLE_PROPERTY_CONST),
    SD_BUS_PROPERTY("string_d_5", "s", NULL, offsetof(struct object, s_5), SD_BUS_VTABLE_PROPERTY_CONST),
    SD_BUS_PROPERTY("string_d_6", "s", NULL, offsetof(struct object, s_6), SD_BUS_VTABLE_PROPERTY_CONST),
    SD_BUS_PROPERTY("string_d_7", "s", NULL, offsetof(struct object, s_7), SD_BUS_VTABLE_PROPERTY_CONST),

    SD_BUS_METHOD("Hello", "s", "s", method_hello, SD_BUS_VTABLE_UNPRIVILEGED),
    SD_BUS_VTABLE_END
};

const char *m(const char *fmt, int n) {
    char tmpname[128];    
    snprintf(tmpname, sizeof(tmpname), fmt, n);
    return strdup(tmpname);
}

struct object * make_block(int num) { 
    struct object *o = malloc(sizeof(struct object));

    if (o) {
        o->name = m("lvol%d", num);
        o->uuid = "kQ1BLF-iBTn-FiHR-x8yI-DEqt-Kyd4-JfbadZ";
        o->some_count = 10 + num;
        o->u64_0 = 0;
        o->u64_1 = 1;
        o->u64_2 = 2;
        o->u64_3 = 3;
        o->u64_4 = 4;
        o->u64_5 = 5;
        o->b_0 = 1;
        o->b_1 = 1;
        o->b_2 = 1;
        o->b_3 = 1;
        o->b_4 = 1;
        o->b_5 = 1;

        o->s_0 = m("some bogus data here %d", 0);
        o->s_1 = m("some bogus data here %d", 1);
        o->s_2 = m("some bogus data here %d", 2);
        o->s_3 = m("some bogus data here %d", 3);
        o->s_4 = m("some bogus data here %d", 4);
        o->s_5 = m("some bogus data here %d", 5);
        o->s_6 = m("some bogus data here %d", 6);
        o->s_7 = m("some bogus data here %d", 7);

        return o;
    }
    return NULL;
}

int main() {
    sd_bus *bus = NULL;
    int r = 0;
    int i = 0;

    r = sd_bus_open_system(&bus);

    if (r < 0) {
        fprintf(stderr, "Failed to connect to system bus: %s\n", strerror(-r));
        goto out;
    }

    r = sd_bus_request_name(bus, "com.blah.storage", 0);
    if (r < 0) {
        fprintf(stderr, "Failed to acquire service name: %s\n", strerror(-r));
        goto out;
    }

    // Unable to get object manager to work for nested object paths unless we start @ /
    // but this maybe just my ignorance of what an object manager can indeed return and when
    r = sd_bus_add_object_manager(bus, NULL, "/");
    if (r < 0) {
        fprintf(stderr, "Failed to add object manager: %s\n", strerror(-r));
        goto out;
    }

    for (i = 0; i < 603; ++i ) {
        char object_path[128];

        snprintf(object_path, sizeof(object_path), "/com/blah/storage/block/%d", i);
        r = sd_bus_add_object_vtable(bus, NULL, object_path, 
            "com.blah.storage.BlockDevice", vtable, make_block(i));

        if (r < 0) {
            fprintf(stderr, "Failed: sd_bus_add_object_vtable: %s\n", strerror(-r));
            goto out;
        }
    }

    while (sd_bus_wait(bus, (uint64_t) -1) >= 0) {
        while (sd_bus_process(bus, NULL) > 0)
            continue;
    }

out:
    sd_bus_unref(bus);
    return r < 0 ? EXIT_FAILURE : EXIT_SUCCESS;
}

