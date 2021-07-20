import argparse
from pathlib import Path
from sumquery.client import Client


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("port", type=int)
    parser.add_argument("clir", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("queries", nargs='+')
    args = parser.parse_args()

    query_client = Client(args.port)

    for query in args.queries:

        nc = query_client.num_components(query)
              
        for line in Path(args.clir/ "{}.tsv".format(query)).read_text()\
                .strip().split("\n"):
            doc_id, clf, score = line.strip().split("\t")
            
            if clf == "N":
                continue
            ann_c1_path = args.output / "annotations" / query / "{}.{}.c1.pkl"\
                    .format(query, doc_id)
            markup_c1_path = args.output / "markup" / query / "{}.{}.c1.json"\
                    .format(query, doc_id)
            image_c1_path = args.output / "images" / query / "{}.{}.c1.png"\
                    .format(query, doc_id)
            if not ann_c1_path.exists() or not markup_c1_path.exists() \
                    or not image_c1_path.exists():
                print("{} {} {}".format(query, doc_id, score))
                continue

            if nc == 1:
                continue

            ann_c2_path = args.output / "annotations" / query / "{}.{}.c2.pkl"\
                    .format(query, doc_id)
            markup_c2_path = args.output / "markup" / query / "{}.{}.c2.json"\
                    .format(query, doc_id)
            image_c2_path = args.output / "images" / query / "{}.{}.c2.png"\
                    .format(query, doc_id)

            if not ann_c2_path.exists() or not markup_c2_path.exists() \
                    or not image_c2_path.exists():
                print("{} {} {}".format(query, doc_id, score))


if __name__ == "__main__":
    main()
