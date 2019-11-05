#!/usr/bin/env python3
import tempfile
import plumbum
from plumbum.cmd import losetup, mkfs, mount, umount
import os
import parted
from multiprocessing import Process, Value
import signal
import time

# Nothing here is thread safe, but will be process safe!

run = Value('b', True)


class BlockDevice(object):

    def __init__(self, size_mib):
        # Lets create a sparse file with the user size, and set it up with a
        # loop back
        self.dir = tempfile.mkdtemp('_storage_churn')
        self.fn = self.dir + '/block_device'

        with open(self.fn, 'ab') as bd:
            bd.truncate(size_mib * (1024 * 1024))

        self.device = str.strip(losetup('-f', '--show', self.fn))

    def destroy(self):
        # unloop the device and delete the file and directory!
        losetup('-d', self.device)
        os.remove(self.fn)
        os.rmdir(self.dir)

    def path(self):
        return self.device

    def __str__(self):
        return self.device


class Partition(object):
    def __init__(self, block_device_obj):
        device = parted.getDevice(block_device_obj.path())
        disk = parted.freshDisk(device, 'msdos')

        geometry = parted.Geometry(device=device, start=1,
                                   length=device.getLength() - 1)

        filesystem = parted.FileSystem(type='ext4', geometry=geometry)

        partition = parted.Partition(disk=disk, type=parted.PARTITION_NORMAL,
                                     fs=filesystem, geometry=geometry)

        disk.addPartition(partition=partition,
                          constraint=device.optimalAlignedConstraint)
        disk.commit()
        self.partition_path = partition.path

    def destroy(self):
        pass

    def path(self):
        return self.partition_path

    def __str__(self):
        return self.partition_path


class Filesystem(object):

    def __init__(self, device_or_partition_path):
        self.path = device_or_partition_path
        # Make the FS and mount it!
        mkfs('-t', 'ext4', self.path)

        # Make a temporary directory
        self.dir = tempfile.mkdtemp('_storage_churn_mount')
        mount(self.path, self.dir)

    def destroy(self):
        # Unmount

        for _ in range(0, 10):
            try:
                umount(self.dir)
                os.rmdir(self.dir)
                break
            except plumbum.commands.processes.ProcessExecutionError:
                time.sleep(0.1)

    def path(self):
        return self.dir

    def __str__(self):
        return self.dir


class ConstructionSequence(object):

    def __init__(self):
        self.stack = []

    def build_up(self, f):
        self.stack.append(f)

    def tear_down(self):
        while len(self.stack):
            self.stack.pop().destroy()


def init_worker():
    signal.signal(signal.SIGINT, signal.SIG_IGN)


def simple_worker():
    init_worker()

    cs = ConstructionSequence()
    while run.value:
        b = BlockDevice(100)
        cs.build_up(b)
        # print(b)
        part = Partition(b)
        cs.build_up(part)
        # print(p)

        fs = Filesystem(part)
        cs.build_up(fs)
        # print(fs)
        cs.tear_down()


def handler(signum, frame):
    global run
    run.value = False
    print('Waiting for a clean shutdown...')


if __name__ == '__main__':

    pl = []
    signal.signal(signal.SIGINT, handler)

    for i in range(0, 10):
        p = Process(target=simple_worker)
        p.start()
        pl.append(p)

    for p in pl:
        p.join()
