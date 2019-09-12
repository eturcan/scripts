import logging
import uuid
import hashlib
import datetime
import json
from .query_processor import process_query
from .results_utils import relevant_results_iter

from . import evidence


def resolve_dataset_mode(doc_id, datasets):
    """
    Determine which dataset and modality a doc_id belongs to.
    doc_id: MATERIAL doc id 
    datasets: List of pathlib.Path objects of available dataset directories
    returns dataset: pathlib.Path, mode: str 
    """

    dataset = None
    mode = None

    # Look at each candidate dataset and check if doc id is text or audio.
    for cand_dataset in datasets:
        text_path = cand_dataset / "text" / "src" / "{}.txt".format(doc_id)
        if text_path.exists():
            dataset = cand_dataset
            mode = "text"
            break

        audio_path = cand_dataset / "audio" / "src" / "{}.wav".format(doc_id)
        if audio_path.exists():
            dataset = cand_dataset
            mode = "speech"
            break

    logging.debug("Found doc id {} in {}/{}".format(doc_id, dataset, mode))
    if dataset is None:
        raise Exception("Could not find a dataset/mode for {}".format(doc_id))

    return dataset, mode


def get_query_source_data(query_id, system_context):

    source_data = {}    
    for m in ["text", "speech"]:
        from pathlib import Path
        dir = Path(system_context["summarization"]["clir_source_evidence"][m])
        
        if str(dir)[0] == "/" and dir.exists(): 
            # Sometimes we just want to pass in a path to Elena's evidence.
            pass
        else:
            dir = system_context["data_dir"] / dir
        path = dir / "{}_summ".format(query_id)
        source_data[m] = json.loads(path.read_text())
       
    return source_data

def collect_clir_query_results_evidence(request_data, system_context):
    logging.info(
        "Collecting evidence for clir results for query id: {}".format(
            request_data.get("query_id", "???")))

    print(request_data)


    return
    query_data = process_query(request_data["query_id"], system_context)
        

    clir_match_info = get_query_source_data(query_data[0].id, system_context)


    for result in relevant_results_iter(request_data["query_id"],
                                        system_context):
        for query_comp in query_data:
            collect_clir_query_result_evidence(result, query_comp,
                                               system_context, clir_match_info)
             



    for result in relevant_results_iter(request_data["query_id"],
                                        system_context):
        write_source_evidence(result, query_data, system_context)


def collect_clir_query_result_evidence(doc, query_comp, system_context,
                                       clir_match_info):
    doc.reset_annotation()
    logging.info("Collecting evidence for query {} -- document {}".format(
        query_comp, doc.id))

    evidence_json_path = (
        system_context["summary_evidence_dir"] / 
        "{}.{}".format(query_comp.id, query_comp.num) / 
        "{}.json".format(doc.id)
    )
    evidence.get_translation_embedding_similarity(query_comp, doc, 
        system_context["summarization"]["embeddings"]["en"])
    evidence.get_clir_source_evidence(query_comp, doc, clir_match_info)


    evidence_json_path.parent.mkdir(exist_ok=True, parents=True)
    logging.info("writing evidence for {} comp {} doc {} to {}".format(
        query_comp.id, query_comp.num, doc.id, evidence_json_path))
    with evidence_json_path.open("w") as fp:
        print(doc.annotation_json(), file=fp)

def write_source_evidence(doc, query_data, system_context):
    src_ev = {
        "team_id": "SCRIPTS",
        "sys_label": "PSQ_SUM",
        "uuid": str(uuid.uuid1()),
        "document_md5": hashlib.md5(doc.source_path.read_bytes()).hexdigest(),
        "query_id": query_data[0].id,
        "document_id": doc.id,
        "document_mode": doc.mode,
        "run_name": "posthoc." + doc.source_lang["iso"],
        "run_date_time": datetime.datetime.utcnow().isoformat("T") + "Z",
        "document_score": doc.relevance_score,
        "offset_list": [],
    }

    for query_comp in query_data:
        annotation_path = (
            system_context["summary_evidence_dir"] / 
            "{}.{}".format(query_comp.id, query_comp.num) / 
            "{}.json".format(doc.id)
        )
        if not annotation_path.exists():
            raise Exception("Missing evidence annotation file: {}".format(
                annotation_path))
        evidence = json.loads(annotation_path.read_text())
        for offsets, clir_src in evidence["clir_source_annotations"].items():
            offsets = eval(offsets)
            
            src_ev["offset_list"].append({
                "start_offset": offsets[0],
                "end_offset": offsets[1],
                "score": 4 - clir_src["importance"],
                "query_component": query_comp.string,
            })
            assert query_comp.string == clir_src["query_string"]

        anns = evidence["annotations"]
        print(anns.keys())        
        if doc.mode == "text":
            utt_rankings = [
                anns['glove6B300d_en_tr(umd-nmt-v4.3_sent-split-v3.0)'], 
                anns['glove6B300d_en_tr(umd-smt-v2.6_sent-split-v3.0)'], 
                anns['glove6B300d_en_tr(scriptsmt-systems-v8_sent-split-v3.0)'], 

                anns['glove42B300d_en_tr(umd-nmt-v4.3_sent-split-v3.0)'], 
                anns['glove42B300d_en_tr(umd-smt-v2.6_sent-split-v3.0)'], 
                anns['glove42B300d_en_tr(scriptsmt-systems-v8_sent-split-v3.0)'], 
            ]
#                anns['glove6B300d_en_tr(umd-nmt-v4.3_sent-split-v3.0)'],
#                anns['glove6B300d_en_tr(umd-smt-v2.6_sent-split-v3.0)'],
#                anns['glove6B300d_en_tr(scriptsmt-systems-v7.2_sent-split-v3.0)'],
#                anns['glove42B300d_en_tr(umd-nmt-v4.3_sent-split-v3.0)'],
#                anns['glove42B300d_en_tr(umd-smt-v2.6_sent-split-v3.0)'],
#                anns['glove42B300d_en_tr(scriptsmt-systems-v7.2_sent-split-v3.0)'],
#
#            ]
        else:
            utt_rankings = [
                anns['glove6B300d_en_tr(umd-nmt-v4.3_material-asr-bg-v0.2)'], 
                anns['glove6B300d_en_tr(umd-smt-v2.6_material-asr-bg-v0.2)'], 
                anns['glove6B300d_en_tr(scriptsmt-systems-v8_material-asr-bg-v0.2)'],

                anns['glove42B300d_en_tr(umd-nmt-v4.3_material-asr-bg-v0.2)'], 
                anns['glove42B300d_en_tr(umd-smt-v2.6_material-asr-bg-v0.2)'], 
                anns['glove42B300d_en_tr(scriptsmt-systems-v8_material-asr-bg-v0.2)'],
            ]
#
#                anns['glove6B300d_en_tr(umd-nmt-v4.3_material-asr-lt-v1.2)'],
#                anns['glove6B300d_en_tr(umd-smt-v2.6_material-asr-lt-v1.2)'],
#                anns['glove6B300d_en_tr(scriptsmt-systems-v7.2_material-asr-lt-v1.2)'],
#                anns['glove42B300d_en_tr(umd-nmt-v4.3_material-asr-lt-v1.2)'],
#                anns['glove42B300d_en_tr(umd-smt-v2.6_material-asr-lt-v1.2)'],
#                anns['glove42B300d_en_tr(scriptsmt-systems-v7.2_material-asr-lt-v1.2)'],
#            ]

   
##        print(query_comp.string)

        utt_rankings = [ur for ur in utt_rankings if ur[1] is not None]
        if len(utt_rankings) == 0:
            logging.warn("No utterance rankings!")
        else:
            for importance, idx in enumerate(
                    merge_utterance_rankings(utt_rankings)[:3], 1):
                start = doc.utterances[idx]["source"].offsets[0]
                end = doc.utterances[idx]["source"].offsets[1]
                src_ev["offset_list"].append({
                    "start_offset": start,
                    "end_offset": end,
                    "score": 2, #4 - importance,
                    "query_component": query_comp.string,
                })

    src_ann_path = (
        system_context["source_evidence_dir"] / query_comp.id / 
        "SCRIPTS.source_language_evidence.{}.{}.src.json".format(
            query_comp.id, doc.id)
    )
    src_ann_path.parent.mkdir(exist_ok=True, parents=True)

    logging.info("writing source annotation for {} doc {} to {}".format(
        query_data[0].id, doc.id, src_ann_path))
    src_ann_path.write_text(json.dumps(src_ev))

def merge_utterance_rankings(anns):
    max_points = len(anns[0][1])
    points = {i: 0 for i in range(max_points)}

    for ann in anns:
        for i, rank in enumerate(ann[1]):
            points[i] += (max_points - rank["rank"])

    ranked_sentences = sorted(points, key=lambda x: points[x], reverse=True)
    return ranked_sentences
