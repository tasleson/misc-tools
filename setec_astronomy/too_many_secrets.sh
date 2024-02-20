#!/usr/bin/bash

# Automates mount/umount of an encrypted file which contains a crypt encrypted block device with
# filesystem.

# Syntax too_many_secrets.sh [mount <device file> <mount point>| umount <mount point>]

DM="setec_astronomy"

if [ "$1" = "mount" ]; then
	fn=$2
	mp=$3

	if [[ ! -a "$fn" ]]; then
		echo "File '$fn' does not exist!"
		exit 2
	fi

	if [[ ! -d "$mp" ]]; then
		echo "Directory '$mp' does not exist!"
		exit 2
	fi

	dev_f="$(losetup -f --show "$fn")"
	cryptsetup luksOpen "$dev_f" "$DM" || exit 1
	mount "/dev/mapper/$DM" "$mp" || exit 1
	exit 0
elif [ "$1" = "umount" ]; then
	mp=$2
	if [[ ! -a "$mp" ]]; then
		echo "Mount point does not exist $mp"
		exit 2
	fi

	umount "$mp" || exit 1
	cryptsetup luksClose "$DM" || exit 1
	losetup -D || exit 1
else
	echo "Incorrect option '$1', available [mount|umount]"
	echo "syntax: $0 [mount <device file> <mount point>| umount <mount point>]"
	exit 2
fi

exit 0
