#!/usr/bin/env python

import os
import glob
from multiprocessing import Pool

command = 'generate_image scripts/configs/summary_style.v2.css {} {}'
def generate_image(fname):
    img_path = fname.replace('markup', 'images').replace('json', 'png')
    if not os.path.exists(img_path):
        print(fname)
        os.system(command.format(fname, img_path))

files = glob.glob('/outputs/markup/query*/*.json')

with Pool(1) as pool:
    pool.map(generate_image, files)
