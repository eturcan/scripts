import argparse
from pathlib import Path
import json
from datetime import datetime
import re
from jsonschema import validate
from uuid import uuid4


def main():
    parser = argparse.ArgumentParser("Package summaries for submission.")
    parser.add_argument("clir_results_dir", type=Path, 
                        help="path to clir results directory")
    parser.add_argument("summary_results_dir", type=Path,  
                        help="path to summarization results directory")
    parser.add_argument("output_directory", type=Path, 
                        help="path to write package")
    parser.add_argument("systemlabel", type=str, help="name of system")
    parser.add_argument("runname", type=str, help="name of run")
    args = parser.parse_args()
    
    schema = json.loads(
        Path("scripts/scripts_sum/summarySchema_v1.3.1.json").read_text())

    for results_path in args.clir_results_dir.glob("query*"):
        
        src_dir = args.summary_results_dir
        tgt_dir = args.output_directory / results_path.stem
        make_query_dir(results_path, tgt_dir, args.summary_results_dir,
                       args.systemlabel, args.runname, schema)        

def make_query_dir(results_path, tgt_dir, summary_results_dir, system_label,
                   run_name, schema):

    query_id = results_path.stem
    tgt_dir.mkdir(exist_ok=True, parents=True)
    manifest = tgt_dir / "{}.tsv".format(query_id)
    with results_path.open("r") as in_fp, manifest.open("w") as out_fp:
        for line in in_fp:
            doc_id, summarize, score = line.strip().split("\t")

            if summarize == "N":
                print("{}\tN\t{}".format(doc_id, score), file=out_fp)
                continue

            meta_fn = "SCRIPTS.{}.{}.json".format(query_id, doc_id)
            meta_path = tgt_dir / meta_fn
            meta = {
                "team_id": "SCRIPTS",
                "query_id": query_id, 
                "document_id": doc_id,
                "uuid": str(uuid4()),
                "sys_label": system_label,
                "run_name": run_name,
                "run_date_time": datetime.utcnow().isoformat("T") + "Z",
                "document_score": float(score),
                "summary_content": [

                ],
            }

            markup_dir = summary_results_dir / "markup" / query_id
            for component_path in sorted(markup_dir.glob(
                    "{}.{}.c*.json".format(query_id, doc_id))):

                src_img_path = (
                    summary_results_dir / "images" / 
                    "{}.png".format(component_path.stem)
                )
                tgt_img_path = tgt_dir / "{}.png".format(component_path.stem)

                qc = read_component_content(component_path)
                qc["query_component_image_filename"] = tgt_img_path.name
                meta["summary_content"].append(qc)
                tgt_img_path.write_bytes(src_img_path.read_bytes())

            validate(instance=meta, schema=schema)
            meta_path.write_text(json.dumps(meta))
            print("{}\tY\t{}\t{}".format(doc_id, score, meta_fn),
                  file=out_fp)

def read_component_content(json_path):
    data = json.loads(json_path.read_text())
    markup = data["markup"]
    markup = re.sub(r"<span.*?>(.*?)</span>", r"\1", markup)
    markup = re.sub(r"<.*?>(.*?)<.*?>", r"\1", markup)

    content = [re.sub(r"\s+", " ", line.strip())
               for line in markup.split("\n")]

    return {
        "query_component": data["query_string"], 
        "eng_content_list": content,
    }


if __name__ == "__main__":
    main()
