import logging
from .collect_text_annotations import collect_text_annotations
from .collect_speech_annotations import collect_speech_annotations
from ..text_document import TextDocument
from ..audio_document import SpeechDocument


def relevant_results_iter(query_id, context):
    r"""Iterate over clir results tsv and return document id and other 
        associated document metadata."""

    clir_results_path = context["clir_results_dir"] / "{}.tsv".format(query_id)

    with open(clir_results_path, "r") as fp:
        for line in fp:
            doc_id, decision, relevance_score = line.strip().split()
            if decision == "N": 
                continue
              
            dataset, mode = resolve_dataset_mode(
                doc_id, context["search"]["datasets"])

            result = {
                "id": doc_id,
                "relevance_score": float(relevance_score),
                "dataset": dataset,
                "mode": mode,
                "lang": context["search"]["language"],
            }
            
            if result["mode"] == "text":
                config = context["summarization"]["text"]
                collect_text_annotations(result)
                doc = TextDocument.from_result(
                    result,
                    config["sentence_segmentation"],
                    config["source_morphology"],
                    config["translations"])
            elif result["mode"] == "speech":            
                config = context["summarization"]["audio"]
                collect_speech_annotations(result)
                doc = SpeechDocument.from_result(
                    result,
                    config["asr"],
                    config["asr_morphology"],
                    config["asr_translations"],
                )

            else:
                raise Exception("result mode='{}' is not a valid mode.".format(
                    result["mode"]))
            yield doc

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
