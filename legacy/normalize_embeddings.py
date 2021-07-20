import argparse
from pathlib import Path
from scripts_sum.cleaning import normalize
from scripts_sum.text_normalizer import TextNormalizer


def main():
    parser = argparse.ArgumentParser("Normalize embeddings.")
    parser.add_argument("lang")
    parser.add_argument("embeddings", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--skip-header", action="store_true")
    args = parser.parse_args()

    tn = TextNormalizer(args.lang)
    found_words = set()
    args.output.parent.mkdir(exist_ok=True, parents=True)
    with args.embeddings.open("r") as in_fp, args.output.open("w") as out_fp:
        if args.skip_header:
            in_fp.readline()
        for line in in_fp:
            word, vec = line.split(" ", 1)
            word_norm = tn.normalize(word, False, False, False).strip()
            if word_norm == '':
                continue
            if word_norm not in found_words:
                found_words.add(word_norm)
                print("{} {}".format(word_norm, vec), end='', file=out_fp)

if __name__ == "__main__":
    main()
