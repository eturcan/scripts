#! /usr/bin/env python3

import argparse
import logging
from pathlib import Path
import json
import scripts_sum
    


def find_and_read_clir_config(results_dir, data_dir, model_dir):

    # Convert any string paths to pathlib.Path objects.
    if isinstance(results_dir, str):
        results_dir = Path(results_dir)
    if isinstance(data_dir, str):
        data_dir = Path(data_dir)

    json_paths = list(results_dir.glob("*.json"))

    if len(json_paths) == 0:
        raise Exception("No clir config json found in {}".format(results_dir))

    json_path = json_paths[0]

    if len(json_paths) > 1:
        logging.warn("Found multiple clir config json files in clir " \
                     "results directory. Using {}".format(json_path))
    logging.info("Reading clir config from {}".format(json_path))

    raw_clir_config = json.loads(json_path.read_text())

    datasets = [data_dir / c
                for c in raw_clir_config["data_collection"]["collections"]]

    iso_lang = raw_clir_config["summarizer"]["language"]
    material_lang = iso2material_lang(iso_lang)

    search_config = {
        "datasets": datasets,
        "language": {"iso": iso_lang, "material": material_lang}
    }

    summary_config = raw_clir_config["summarizer"]["new_summary_config"]
    load_embeddings(model_dir, summary_config["embeddings"])

    return summary_config, search_config

def iso2material_lang(iso):
    from warnings import warn
    warn("iso2material_lang only supports lt and bg.")
    if iso == "lt":
        return "2B"
    elif iso == "bg":
        return "2S"
    else:
        raise Exception("Bad language code {}".format(iso))
 
def load_embeddings(data_dir, embedding_config):
    for lang, lang_configs in embedding_config.items():
        for name, path_suffix in lang_configs.items():
            emb_path = data_dir / path_suffix
            logging.debug("Loading {} embeddings {} from {}".format(
                lang, name, emb_path))
            embeddings = scripts_sum.Embeddings.from_path(emb_path)
            lang_configs[name] = {
                "path": emb_path,
                "model": embeddings
            }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--logging", type=str, default="debug")
    parser.add_argument("--resources-config", type=Path)
    parser.add_argument("--data-dir", type=Path, required=True)
#    parser.add_argument("--query-processor", type=Path, required=True)
#    parser.add_argument("--morph-path", type=Path, required=True)
#    parser.add_argument("--morph-port", type=int, required=True)
#    parser.add_argument("--clir-results-dir", type=Path, required=True)
#    parser.add_argument("--work-dir", type=Path, required=True)
#    parser.add_argument("--model-dir", type=Path, required=True)
#    parser.add_argument("--output-dir", type=Path, required=True)
#

    args = parser.parse_args()

    logging.getLogger().setLevel(logging.__dict__[args.logging.upper()])
#    summary_config, search_config = find_and_read_clir_config(args.work_dir,
#                                                              args.data_dir,
#                                                              args.model_dir)
#     


    server = scripts_sum.Server(
        args.port, 
        data_dir=args.data_dir,
#        query_processor_path=args.query_processor,
#        morph_path=args.morph_path,
#        morph_port=args.morph_port,
#        clir_results_dir=args.clir_results_dir,
#        summarizaton_config=summary_config,
#        search_config=search_config,
#        work_dir=args.work_dir,
#        summary_evidence_dir=args.output_dir / "summary_evidence",
#        source_evidence_dir=args.output_dir / "source_evidence",
    )
    print("Server running on {}".format(args.port))
    server.start()

if __name__ == "__main__":
    main()
