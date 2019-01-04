#!/usr/bin/env python3

import dbus
import sys
import pprint
from dbus.mainloop.glib import DBusGMainLoop

# Validate data values.
#
# Hardcoded property values in service based on property name
EXPECTED_VAL = {
    "some_string": "ABCDEFGHIJKLMNOPQRSTUVWXYZ_0123456789",
    "some_u8": 0x1F,
    "some_u16": 0x0102,
    "some_u32": 0x01020304,
    "some_u64": 0x0102030405060708,
    "some_i16": -32768,
    "some_i32": -2147483648,
    "some_i64": -9223372036854775808,
    "some_true_bool": True,
    "some_false_bool": False,
    "some_f64": 1.7976931348623157e+308
}


def properties(p):
    for k, v in p.items():
        if k in EXPECTED_VAL:
            if EXPECTED_VAL[k] != v:
                print("Value Error for key: '%s', expected: %s actual: %s" %
                      (k, EXPECTED_VAL[k], str(v)))
        else:
            print("Missing type, Key:%s = Value:%s" % (str(k), str(v)))


def check_values(name_space, object_path):
    bus = dbus.SessionBus(mainloop=DBusGMainLoop())
    manager = dbus.Interface(bus.get_object(name_space, object_path),
                             "org.freedesktop.DBus.ObjectManager")

    objects = manager.GetManagedObjects(timeout=1000)

    for object_path, val in objects.items():
        for interface, props in val.items():
            if interface == "com.blah.sizecheck.Values":
                print("interface: %s" % interface)
                properties(props)


if __name__ == '__main__':
    check_values("com.blah.sizecheck", "/com/blah/sizecheck")
    sys.exit(0)
