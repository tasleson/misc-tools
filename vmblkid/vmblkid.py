#!/usr/bin/python3

import os
import sys
import fcntl
import string

# Code based on information from:
# https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git/tree/tools/hv/lsvmbus

VM_BUS_PATH = "/sys/bus/vmbus/devices"
SYN_SCSI_CNTRL = "{ba6163d9-04a1-4d29-b605-72e2ffb1dc7f}"


def get_vm_dev_attrs(device, attribute):
    items = []
    try:
        with open("%s/%s/%s" % (VM_BUS_PATH, device, attribute)) as f:
            for line in f.readlines():
                items.append(line.strip())
    except IOError:
        pass
    return items


def get_controllers():
    _controllers = []

    for i in os.listdir(VM_BUS_PATH):
        num_id = get_vm_dev_attrs(i, "id")[0]
        desc = get_vm_dev_attrs(i, "class_id")[0]
        if desc == SYN_SCSI_CNTRL:
            _controllers.append((int(num_id), os.path.split(i)[1]))

    # sort and return just the end path id
    _controllers.sort()
    return [e[1] for e in _controllers]


def get_hbtl(device):
    """
    Returns the Host, Bus, Target, Lun
    :param device:
    :return: (int, int, int, int)
    """
    buf = bytearray(8)
    try:
        with open(device, "r") as d:
            fcntl.ioctl(d.fileno(), 0x5382, buf, True)
        # ref. https://tldp.org/HOWTO/SCSI-Generic-HOWTO/scsi_g_idlun.html
        return buf[3], buf[2], buf[0], buf[1]

    except OSError as ose:
        return None


def corrected_host(cntrl_list, dev, not_found):
    dp = os.getenv("DEVPATH", os.readlink("/sys/block/%s" % os.path.split(dev)[1]))
    for idx, val in enumerate(cntrl_list):
        if val in dp:
            return idx
    return not_found


if __name__ == "__main__":

    if len(sys.argv) != 2:
        print("syntax: vmlblkid: <device>")
        sys.exit(2)

    if '/' in sys.argv[1]:
        device = sys.argv[1]
    else:
        device = "/dev/%s" % sys.argv[1]

    # Strip off partition number
    device = device.rstrip(string.digits)

    with open("/tmp/debug.txt", "a") as w:
        for k, v in os.environ.items():
            w.write("DEBUG: %s=%s\n" % (k, v))

    if not os.path.exists(VM_BUS_PATH):
        sys.exit(1)

    # Build list of storage controllers
    controllers = get_controllers()

    # Retrieve the HBTL from device, the "H" may not match from VM host to VM
    # guest, so we will correct it.
    hbtl = get_hbtl(device)
    correct_host = corrected_host(controllers, device, hbtl[0])
    vmblkid = "vm-%d:%d:%d:%d" % (correct_host, hbtl[1], hbtl[2], hbtl[3])
    print("VMBLKID=%s" % vmblkid)
    sys.exit(0)
