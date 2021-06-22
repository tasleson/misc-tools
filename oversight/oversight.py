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

objects = None

pending_objects = []
pending_add = []
pending_rm = []
pending_update = []


def dump():
    global objects

    if objects:
        for obj, info in objects.items():
            print("object %s\n" % obj)
            for intf, values in info.items():

                print("Interface %s" % intf)
                for prop, val in values.items():
                    print("\t%s: %s" % (prop, str(val)))


def _do_prop_update(object_path, interface, changed, invalidated):
    global objects

    for prop, new_value in changed.items():
        print("%s[%s][%s] = %s" % (object_path, interface, prop, str(new_value)))
        objects[object_path][interface][prop] = new_value

    print("\n")


def properties_changed(*args, **kwargs):

    global objects
    global pending_update

    # Is there a better way to do this without requiring registering a
    # signal handler for every object?
    if kwargs["object_path"].startswith(SRV_PATH):

        object_path = kwargs["object_path"]
        interface = args[0]
        changed = args[1]
        invalidated = args[2]

        if objects:

            # Handle all the pending, then this one
            for pp in pending_update:
                _do_prop_update(*pp)

            _do_prop_update(object_path, interface, changed, invalidated)
        else:
            pending_update.append((object_path, interface, changed, invalidated))


def _do_obj_add(object_path, interface_property_dict):
    global objects
    objects[object_path] = interface_property_dict


def object_manager_add(object_path, payload):
    global objects
    global pending_add

    if objects:

        for adding in pending_add:
            _do_obj_add(adding[0], adding[1])

        _do_obj_add(object_path, payload)
    else:
        pending_add.append((object_path, payload))


def _do_obj_del(object_path, interfaces_removed):
    global objects

    if object_path in objects:
        for intf in interfaces_removed:
            del objects[object_path][intf]

        if not objects[object_path]:
            del objects[object_path]


def object_manager_remove(object_path, payload):

    global objects
    global pending_rm

    if objects:
        for p in pending_rm:
            _do_obj_del(p[0], p[1])

        _do_obj_del(object_path, payload)
    else:
        pending_rm.append((object_path, payload))


def get_objects(the_bus):
    global objects
    rc = dict()
    obj_mgr = the_bus.get_object(BUS_NAME, SRV_PATH, introspect=False)
    obj_int = dbus.Interface(obj_mgr, OBJECT_MANAGER)
    objects = obj_int.GetManagedObjects()

    for object_path, obj_value in objects.items():
        rc[object_path] = obj_value

    objects = rc


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
        get_objects(bus)

        loop = GLib.MainLoop()
        loop.run()
    except KeyboardInterrupt:
        dump()
    except BaseException:
        traceback.print_exc()
        sys.exit(1)
