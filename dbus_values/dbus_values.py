#!/usr/bin/env python3

import dbus
import sys
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


def check_in_out(proxy):
    for a0 in [0, 128, 255]:
        for a1 in [True, False]:
            for a2 in [-32768, -1, 1, 32767]:
                for a3 in [0, 2**15, 2**16-1]:
                    for a4 in [-2147483648, -1, 1, 2147483647]:
                        for a5 in [0, 0x11223344, 2**32-1]:
                            for a6 in [-9223372036854775808, -1, 0,
                                       9223372036854775807]:
                                for a7 in [0, 0x1122334455667788, 2**64-1]:
                                    for a8 in [-1.7976931348623157e+308,
                                               -1.1, 0.0,
                                               2.2250738585072014e-308,
                                               1.7976931348623157e+308]:
                                        result = proxy.AllTheThings(
                                            dbus.Byte(a0),
                                            dbus.Boolean(a1),
                                            dbus.Int16(a2),
                                            dbus.UInt16(a3),
                                            dbus.Int32(a4),
                                            dbus.UInt32(a5),
                                            dbus.Int64(a6),
                                            dbus.UInt64(a7),
                                            dbus.Double(a8))

                                        assert result[0] == a0
                                        assert result[1] == a1
                                        assert result[2] == a2
                                        assert result[3] == a3
                                        assert result[4] == a4
                                        assert result[5] == a5
                                        assert result[6] == a6
                                        assert result[7] == a7
                                        assert result[8] == a8


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
                remote_obj = bus.get_object("com.blah.sizecheck", object_path)
                iface = dbus.Interface(remote_obj, interface)
                check_in_out(iface)


if __name__ == '__main__':
    check_values("com.blah.sizecheck", "/com/blah/sizecheck")
    sys.exit(0)
