#!/usr/bin/python3

"""
Prototype signal verification for lvmdbusd or potentially other dbus services

Dbus signals when implemented correctly for a service allow a client the ability
to have current state updated when it occurs and be totally event driven.

Theory of operation:
* Register signal handlers, fetch current state by using GetManagedObjects and
  keep this as the reference db that should only be updated via signals
* After 3 seconds have elapsed since the last signal, retrieve entire state by
  calling GetManagedObjects and compare to in memory db.  Log any differences.

Note: Entire execution of code is event driven utilizing the GLib main context
      and timers.  Code is inherently single threaded with this approach.

To run the lvmdbus test suite, edit the unit test (TODO: Add option to unit test)

diff --git a/test/dbus/lvmdbustest.py b/test/dbus/lvmdbustest.py
index 6d692223f..5ea2b587b 100755
--- a/test/dbus/lvmdbustest.py
+++ b/test/dbus/lvmdbustest.py
@@ -248,6 +248,10 @@ class TestDbusService(unittest.TestCase):
        def tearDown(self):
                # If we get here it means we passed setUp, so lets remove anything
                # and everything that remains, besides the PVs themselves
+
+               # Allow the signal verification process to do some checks
+               time.sleep(4)
+
                self.objs, self.bus = get_objects()

                # The self.objs[PV_INT] list only contains those which we should be

To induce a delay before teardown, to allow this process the ability to handle
outstanding signals and do a comparison.

"""
import copy
import os
import sys
import time
import traceback

import dbus
import dbus.mainloop.glib
from gi.repository import GLib

OBJECT_MANAGER = "org.freedesktop.DBus.ObjectManager"
BUS_NAME = "com.redhat.lvmdbus1"
SRV_PATH = "/com/redhat/lvmdbus1"

inital_fetch_complete = False
objects = dict()

pending_objects = []
pending_add = []
pending_rm = []
pending_update = []

last_update = 0
dirty = False
last_log = time.time()
errors = 0


def log_error(msg):
    global errors
    global last_log
    errors += 1

    n = time.time()
    print("[%f][%f]: %s" % (n, n - last_log, msg))
    last_log = n


def log(msg):
    global last_log
    n = time.time()
    print("[%f][%f]: %s" % (n, n - last_log, msg))
    last_log = n


def dump_object(object_path, interfaces):
    log(" ")
    log("object %s" % object_path)
    for intf, values in sorted(interfaces.items(), key=lambda x: x[0]):
        log("Interface %s" % intf)
        for prop, val in sorted(values.items(), key=lambda x: x[0]):
            log("\t%s: %s" % (prop, str(val)))


def dump():
    global objects

    if inital_fetch_complete:
        log("**** Dumping signal db")
        for obj_path, info in objects.items():
            dump_object(obj_path, info)

    log("**** Dumping GetManagedObjects\n")
    sys_bus = dbus.SystemBus()
    c = _get_managed_objects(sys_bus)
    for obj_path, info in c.items():
        dump_object(obj_path, info)


def _do_prop_update(object_path, interface, changed, invalidated):
    global objects

    for prop, new_value in changed.items():
        log("%s[%s][%s] = %s" % (object_path, interface, prop, str(new_value)))
        objects[object_path][interface][prop] = new_value
    log("\n")


def properties_changed(*args, **kwargs):

    global objects
    global pending_update
    global last_update
    global dirty

    # Is there a better way to do this without requiring registering a
    # signal handler for every object?
    if kwargs["object_path"].startswith(SRV_PATH):
        last_update = time.time()
        dirty = True

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
    log("Object add: %s" % object_path)


def object_manager_add(object_path, payload):
    global objects
    global pending_add
    global last_update
    global dirty

    last_update = time.time()
    dirty = True

    if inital_fetch_complete:
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
            log("Object interface deleted %s:%s" % (object_path, intf))

        if not objects[object_path]:
            del objects[object_path]
            log("Object del: %s" % object_path)
    else:
        log_error("Got a remove for object we don't have! %s" % object_path)


def object_manager_remove(object_path, payload):

    global objects
    global pending_rm
    global last_update
    global dirty

    last_update = time.time()
    dirty = True

    if inital_fetch_complete:
        for p in pending_rm:
            _do_obj_del(p[0], p[1])

        _do_obj_del(object_path, payload)
    else:
        pending_rm.append((object_path, payload))


def _get_managed_objects(the_bus):
    rc = dict()
    obj_mgr = the_bus.get_object(BUS_NAME, SRV_PATH, introspect=False)
    obj_int = dbus.Interface(obj_mgr, OBJECT_MANAGER)
    obj_cur = obj_int.GetManagedObjects()

    for object_path, obj_value in obj_cur.items():
        rc[object_path] = obj_value

    return rc


def process_pid(name):
    for p in [pid for pid in os.listdir("/proc") if pid.isdigit()]:
        try:
            with open(os.path.join("/proc/", p, "cmdline"), "r") as cmd:
                cmd_line = cmd.readline()
        except OSError:
            continue

        if name in cmd_line:
            return int(p)
    return None


def kill_test():
    # lvmdbusd specific
    pid = process_pid("lvmdbustest.py")
    if pid:
        os.kill(pid, 9)

    dump()
    sys.exit(5)


def get_objects(the_bus):
    global objects
    global inital_fetch_complete
    objects = _get_managed_objects(the_bus)
    inital_fetch_complete = True


def check_idle():
    global last_update
    global dirty

    current = time.time()
    time_since_last_signal = current - last_update

    # It's difficult to determine that any given state is correct if things are
    # rapidly changing.  We will wait until we haven't gotten any signals for
    # a while and we will then compare what the object manager retrieves vs.
    # what we have gotten via signals.  They should match if all the signals
    # are being delivered as needed.
    if dirty and time_since_last_signal > 3.0 and objects is not None:
        start = time.time()
        log("Validating objects entry")

        last_update = current
        dirty = False

        try:
            sys_bus = dbus.SystemBus()
            c = _get_managed_objects(sys_bus)
            p = copy.deepcopy(objects)  # Make full copy of signal DB

            # Compare what we just retrieved to what we have gotten via signals
            for object_path, entry in c.items():
                if object_path not in p:
                    log_error("Missing object %s" % object_path)
                else:
                    for interface, prop_vals in entry.items():
                        if interface not in p[object_path]:
                            log_error(
                                "Missing interface %s for object %s"
                                % (interface, object_path)
                            )
                        else:
                            for prop, value in prop_vals.items():
                                if prop not in c[object_path][interface]:
                                    log_error(
                                        "Missing property %s for interface "
                                        "%s for object %s"
                                        % (prop, interface, object_path)
                                    )
                                else:
                                    e = p[object_path][interface][prop]
                                    # log("Comparing (%s): %s to %s" %
                                    #      (prop, str(value), str(e)))
                                    if value != e:
                                        log_error(
                                            "Property (%s) mismatch "
                                            "objectmgr %s !=  signal value: "
                                            "%s object: %s"
                                            % (prop, str(value), str(e), object_path)
                                        )
                                    else:
                                        del p[object_path][interface][prop]

                            # We shouldn't have any properties left
                            if p[object_path][interface]:
                                log_error(
                                    "The following properties were present "
                                    "in signals db which were not present in "
                                    "object manager for object: %s" % object_path
                                )
                                for k, v in p[object_path][interface].items():
                                    log("%s:%s" % (str(k), str(v)))

                            del p[object_path][interface]

                    # We shouldn't have any interfaces left
                    if p[object_path]:
                        log_error(
                            "The following interfaces were present in "
                            "signals db which were not present in object"
                            " manager for object %s" % object_path
                        )
                        for intf in p[object_path].keys():
                            log("interface %s for object %s" % (intf, object_path))
                    del p[object_path]

            # We shouldn't have any objects left
            if p:
                log_error(
                    "The following objects were present in signals db which "
                    "were not preset in object manager"
                )
                for objs in p.keys():
                    log_error("%s" % str(objs))
        except:
            traceback.print_exc()
            return False

        if errors > 0:
            log_error(
                "Validating objects exiting ON ERROR! duration = %f"
                % (time.time() - start)
            )

            # Delay the end of the test to see if whatever is incorrect resolves
            # itself.
            GLib.timeout_add(500, kill_test)
            return False
        else:
            log("Validating objects exit %f" % (time.time() - start))

    return True


if __name__ == "__main__":

    if len(sys.argv) > 1 and len(sys.argv) != 3:
        log("syntax: None or bus name path, eg. %s %s %s" % (sys.argv[0], BUS_NAME, SRV_PATH))
        sys.exit(1)
    elif len(sys.argv) == 3:
        BUS_NAME = sys.argv[1]
        SRV_PATH = sys.argv[2]

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()
    try:
        # Register for main signals
        dobj = bus.get_object(BUS_NAME, SRV_PATH)
        dobj.connect_to_signal(
            dbus_interface=OBJECT_MANAGER,
            signal_name="InterfacesAdded",
            handler_function=object_manager_add,
        )

        dobj.connect_to_signal(
            dbus_interface=OBJECT_MANAGER,
            signal_name="InterfacesRemoved",
            handler_function=object_manager_remove,
        )

        bus.add_signal_receiver(
            properties_changed,
            signal_name="PropertiesChanged",
            path_keyword="object_path",
        )

        # There is an inherent race condition between fetching all the objects
        # and having the signal handlers in place.  We will install signal
        # handlers and schedule the object retrieval to occur when the main
        # even loop is idle.  This way the main loop is up and processing
        # events before we retrieve the entire object state.
        GLib.idle_add(get_objects, bus)
        GLib.timeout_add(500, check_idle)

        loop = GLib.MainLoop()
        loop.run()
    except KeyboardInterrupt:
        dump()
        if errors > 0:
            sys.exit(5)
        sys.exit(0)
    except BaseException:
        traceback.print_exc()
        sys.exit(1)
