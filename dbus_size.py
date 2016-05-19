#!/usr/bin/env python2

import dbus
import sys
import pprint
from dbus.mainloop.glib import DBusGMainLoop


# Try and calculate the amount of data a client has available from any
# dbus service that supports the object manager interface.  Not type complete,
# but works for the immediate need.
#
# Hopefully useful to see how memory savoy a dbus service is, eg. the amount
# of memory it consumes vs. the amount of data it presents.

pp = pprint.PrettyPrinter(indent=4, width=78)

summary = dict(string_num=0, string_size_total=0, booleans=0,
               object_path_num=0, object_path_size_total=0, byte_count=0,
               uint64_count=0, int64_count=0, uint32_count=0,
               int32_count=0, double_count=0,
               dictionary_key_num=0, dictionary_key_size_total=0,
               interface_num=0, interface_size_total=0, dbus_object_num=0)


def size_value(v):
    if isinstance(v, dbus.String):
        summary['string_num'] += 1
        summary['string_size_total'] += len(str(v))
    elif isinstance(v, dbus.Boolean):
        summary['booleans'] += 1
    elif isinstance(v, dbus.ObjectPath):
        summary['object_path_num'] += 1
        summary['object_path_size_total'] += len(str(v))
    elif isinstance(v, dbus.Array):
        for i in v:
            size_value(i)
    elif isinstance(v, dbus.Byte):
        summary['byte_count'] += 1
    elif isinstance(v, dbus.UInt64):
        summary['uint64_count'] += 1
    elif isinstance(v, dbus.Int64):
        summary['int64_count'] += 1
    elif isinstance(v, dbus.UInt32):
        summary['uint32_count'] += 1
    elif isinstance(v, dbus.Int32):
        summary['int32_count'] += 1
    elif isinstance(v, dbus.Double):
        summary['double_count'] += 1
    elif isinstance(v, dbus.Dictionary):
        for k, ev in v.items():
            summary['dictionary_key_num'] += 1
            summary['dictionary_key_size_total'] += len(k)
            size_value(ev)
    elif isinstance(v, dbus.Struct):
        # Treated like a tuple, iterate and sum
        for i in v:
            size_value(i)
    else:
        print("Unknown %s" % str(type(v)))


def properties(p):
    for k, v in p.items():
        size_value(v)
        # print ("Key:%s = Value:%s" % (k, v))


def size_summary():
    total_size_fixed_len = 0
    total_size_fixed_len += summary['booleans']
    total_size_fixed_len += summary['byte_count']
    total_size_fixed_len += (summary['uint64_count'] * 8)
    total_size_fixed_len += (summary['int64_count'] * 8)
    total_size_fixed_len += (summary['uint32_count'] * 4)
    total_size_fixed_len += (summary['int32_count'] * 4)
    total_size_fixed_len += (summary['double_count'] * 8)

    total_size_variable_len = 0
    total_size_variable_len += summary['string_size_total']
    total_size_variable_len += summary['interface_size_total']
    total_size_variable_len += summary['dictionary_key_size_total']
    total_size_variable_len += summary['object_path_size_total']

    print("We retrieved %d objects" % summary['dbus_object_num'])
    print('Size fixed len data = %d' % total_size_fixed_len)
    print('Size variable len data (strings) = %d' % total_size_variable_len)
    total = total_size_fixed_len + total_size_variable_len
    print('Total bytes %d' % total)
    print("Average bytes per object %d" %
          (float(total)/summary['dbus_object_num']))


def retrieve_object_size_data(name_space, object_path):
    bus = dbus.SystemBus(mainloop=DBusGMainLoop())

    manager = dbus.Interface(bus.get_object(name_space, object_path),
                             "org.freedesktop.DBus.ObjectManager")

    objects = manager.GetManagedObjects()

    for object_path, val in objects.items():
        summary['dbus_object_num'] += 1
        summary['object_path_num'] += 1
        summary['object_path_size_total'] += len(object_path)
        for interface, props in val.items():
            summary['interface_num'] += 1
            summary['interface_size_total'] += len(interface)
            properties(props)


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("syntax: <bus name> <object path>")
        sys.exit(1)

    retrieve_object_size_data(sys.argv[1], sys.argv[2])

    pp.pprint(summary)
    size_summary()
    sys.exit(0)
