#!/bin/bash

CPUS=$1

mkimg () {
  json_path=$1

  img_path=`echo $json_path | sed s/markup/images/ | sed s/json/png/`
  generate_image scripts/configs/summary_style.v2.css \
    $json_path $img_path
}

export -f mkimg

args=`ls /outputs/markup/query*/*.json`

echo "parallel -j$CPUS mkimg :::"
parallel -j$CPUS mkimg ::: $args


