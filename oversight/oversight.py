#!/usr/bin/python3

"""
Prototype signal verification for lvmdbusd.
"""

import sys
import traceback

import dbus
import dbus.mainloop.glib
from gi.repository import GLib

OBJECT_MANAGER = "org.freedesktop.DBus.ObjectManager"
BUS_NAME = "com.redhat.lvmdbus1"
SRV_PATH = "/com/redhat/lvmdbus1"


def properties_changed(*args, **kwargs):
    # Is there a better way to do this without requiring registering a
    # signal handler for every object?
    if kwargs["object_path"].startswith(SRV_PATH):
        print("\n\nPROPERY CHANGED\n\n")

        interface = args[0]
        changed = args[1]
        invalidated = args[2]

        print("Object %s" % kwargs["object_path"])
        print("Interface %s" % interface)

        for k, v in changed.items():
            print("Property= %s, new value= %s" % (k, str(v)))

        print("Invalidated = %s\n" % str(invalidated))


def object_manager_add(object_path, payload):
    print("Added object %s" % object_path)
    for k, v in payload.items():
        print("interface= %s" % k)
        for name, value in v.items():
            print("%s= %s" % (name, str(value)))


def object_manager_remove(object_path, payload):
    what = " ,".join(payload)
    print("Object %s: interfaces removed: %s" % (object_path, what))


if __name__ == '__main__':
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()
    try:
        # Register for main signals
        dobj = bus.get_object(BUS_NAME, SRV_PATH)
        dobj.connect_to_signal(dbus_interface=OBJECT_MANAGER,
                               signal_name="InterfacesAdded",
                               handler_function=object_manager_add)

        dobj.connect_to_signal(dbus_interface=OBJECT_MANAGER,
                               signal_name="InterfacesRemoved",
                               handler_function=object_manager_remove)

        bus.add_signal_receiver(properties_changed,
                                signal_name="PropertiesChanged",
                                path_keyword="object_path")

        # TODO fetch initial objects

        loop = GLib.MainLoop()
        loop.run()

    except BaseException:
        traceback.print_exc()
        sys.exit(1)
