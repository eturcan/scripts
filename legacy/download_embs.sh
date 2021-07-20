#!/bin/bash

FASTEXT_URL="https://dl.fbaipublicfiles.com/fasttext/vectors-crawl"

if [[ $1 == '' ]]; then

    echo "usage: download_embs PATH/TO/SAVE/EMBEDDINGS"
    exit 1    
fi

if [[ ! -d $1 ]]; then
    mkdir -p $1
fi

langs="lt bg sw so tl"

for lang in $langs; do

    if [[ ! -d "$1/$lang" ]]; then
        mkdir "$1/$lang"
    fi
    echo $lang

    vec_file="$1/$lang/cc.$lang.300.vec.txt"
    norm_vec_file="$1/$lang/cc.$lang.300.vec.normalized.txt"

    if [[ ! -f $vec_file ]]; then
        echo "tada!"
        wget -O - $FASTEXT_URL/cc.$lang.300.vec.gz \
            | gunzip -c > $vec_file
    fi 

    if [[ ! -f $norm_vec_file ]]; then
        normalize_embeddings $lang $vec_file $norm_vec_file        
    fi

done
