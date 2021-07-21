lang=$1

wget https://dl.fbaipublicfiles.com/fasttext/vectors-crawl/cc.${lang}.300.vec.gz .

gzip -d cc.$lang.300.vec.gz
head -n +2 cc.$lang.300.vec > cc.$lang.300.vec.txt

mkdir -p $lang

# generate pickled Embedding object into ./$lang folder
python pkl.py $lang
