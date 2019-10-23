import argparse
from pathlib import Path
import json
from uuid import uuid4
import pickle
import numpy as np


def main():
    parser = argparse.ArgumentParser(
        "Produce source evidence json for query/doc pair.")
    parser.add_argument("--score", type=float)
    parser.add_argument("--sys-label")
    parser.add_argument("--run-name")
    parser.add_argument("--timestamp")
    parser.add_argument("--psq", choices=["true", "false"])
    parser.add_argument("--annotations", nargs="+", type=Path)
    parser.add_argument("--markup-files", nargs="+", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    offset_list = []

    if args.psq == "true":
        for path in args.annotations:

            psq_offsets = []
            doc = pickle.loads(path.read_bytes())
            for offsets in doc.annotations["psq"]["meta"]['offsets']:
                psq_offsets.append({
                    "start_offset": offsets[0][0],
                    "end_offset": offsets[0][1],
                    "query_component": doc.annotations["QUERY"].string,
                    "score": offsets[1]
                })
            psq_offsets.sort(key=lambda x: x["score"], reverse=True)
            for i, chunk in enumerate(np.array_split(psq_offsets, 3)):
                for c in chunk:
                    c["score"] = 3 - i
                    offset_list.append(c)

    for path in args.markup_files:
        mu_dat = json.loads(path.read_text())
        for i, (start_offset, end_offset) in enumerate(
                mu_dat["meta"]["source_offsets"]):

            o = {"start_offset": start_offset, "end_offset": end_offset,
                 "score": max(3 - i, 1), 
                 "query_component": mu_dat["query_string"]}
            offset_list.append(o) 
   

    result = {
        "team_id": "SCRIPTS",
        "sys_label": args.sys_label,
        "run_name": args.run_name,
        "uuid": str(uuid4()),
        "document_score": args.score,
        "document_md5": mu_dat["source_md5"],
        "query_id": mu_dat["query_id"],
        "document_id": mu_dat["document_id"],
        "document_mode": mu_dat["mode"],
        "run_date_time": args.timestamp,
        "offset_list": offset_list,
    }

    args.output.parent.mkdir(exist_ok=True, parents=True)
    args.output.write_text(json.dumps(result, indent="  "))

if __name__ == "__main__":
    main()
