#!/usr/bin/python3

import cv2
import numpy as np
import subprocess
import time
import os
import sys


def find_non_black(img_data):
	# We should only have 2 colors, black and something else as we did 2 color quantization
	# which includes the mask, which is black.
	y_max, x_max = img_data.shape[0:2]
	for y in range(y_max):
		for x in range(x_max):
			b, g, r = img_data[y, x]
			if b != 0 or g != 0 or r != 0:
				return (b, g, r)
	return None


def acquire_image(device, mask_img):
	image_name = time.strftime("%Y%m%d-%H%M%S") + ".jpg"
	cmd = ["fswebcam",  "-d", device, "-r",  "1920x1080",  "--jpeg", "100",  "-S", "40", image_name]
	subprocess.run(cmd, check=True, capture_output=True)
	org = cv2.imread(image_name)
	mask = cv2.imread(mask_img)
	return (cv2.bitwise_and(org, mask), image_name)


def quantization(img, n_colors=2):
	# https://docs.opencv.org/4.x/d1/d5c/tutorial_py_kmeans_opencv.html
	pixels = np.float32(img.reshape(-1, 3))
	criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)

	ret, label, center = cv2.kmeans(pixels, n_colors, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
	center = np.uint8(center)
	f = label.flatten()
	res = center[f]
	return res.reshape((img.shape))


def led_state(sample):
	# This is very fragile and prone to error.  This would need lots of work to
	# be reliable with varying levels/colors of ambient light.

	# blue, green, red, +- range, name
	standby = (102, 178, 195, 35, "standby")
	on = (226, 208, 127, 20, "on")
	off = (18, 26, 22, 40, "off")
	states = [standby, on, off]

	for s in states:
		state_chk = s[4]
		r = s[3]
		found = True

		for i in range(3):
			low = max(0, s[i] - r)
			hi = s[i] + r
			if sample[i] not in range(low, hi):
				found = False
				break

		if found:
			return state_chk
	return None


if __name__ == "__main__":

	while True:
		(aoi, fn) = acquire_image("/dev/video2", "mask.png")
		# cv2.imshow("Area of interest", aoi)
		q = quantization(aoi)
		color = find_non_black(q)

		# If we found the state delete the acquired photo, else dump name and exit
		state = led_state(color)
		if state is not None:
			os.remove(fn)
			print(f"{color} = {state}")
		else:
			print(f"Unable to determine state {state} for {fn} {color}")
			sys.exit(2)

		#cv2.imshow('Quantization', q)
		#cv2.waitKey(0)
		#cv2.destroyAllWindows()
