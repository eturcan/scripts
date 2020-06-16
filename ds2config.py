import argparse 
from pathlib import Path
import re
from pprint import pprint
from scripts_sum.lang import get_material
import json
import warnings


def main():
    parser = argparse.ArgumentParser(
        ("Generate a summarization server config file from one or more data "
         "structure files."))
#    parser.add_argument("--no-audio-seg", action="store_true",
#        help=("disable use of use the audio segmenter "
#              "and use acoustic segmentation."))
    parser.add_argument("--use-mt", nargs="+", default=None,
                        choices=["umd-smt", "umd-nmt", "edi-nmt"])
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()

    configs = []
    for path in args.paths:
        for x in proc_ds(path.read_text(), #no_audio_seg=args.no_audio_seg,
                         use_mt=args.use_mt):
            configs.append(x)
    print(json.dumps(configs, indent="    "))


def get_subconfig_meta(sc):
    name = sc[:sc.index("\n")].split("=")[1]
    sc = sc[sc.index("\n") + 1:]
    lang = sc[:sc.index("\n")].split("=")[1]
    lang = get_material(lang)
    sc = sc[sc.index("\n") + 1:]
    
    mode = sc[:sc.index("\n")].split("=")[1]
    sc = sc[sc.index("\n") + 1:]
    corpus_prefix = Path(name)
    return {
        "name": name, "lang": lang, "mode": mode, 
        "corpus_prefix": corpus_prefix
    }

def get_text_config(meta, sc, use_mt):

    morphs = {
        morph[2]: Path(morph[0])
        for morph in re.findall(r"Morpohological_Analysis_location=(.*?)\n+Morpohological_(?:Analyzer|Analysis)_version=(.*?)\n+Morpohological_(?:Analyzer|Analysis)_source=(.*?)\n", sc)
    }
    src = re.search(r"source_location=(.*?)\n", sc).groups()[0]
    sent_seg = re.search(r"SentSplitter_location=(.*?)\n", sc).groups()[0]
    src_morph = morphs[sent_seg]

    translations = []
    for mt in re.findall(
            r"MT_location=(.*?)\n+MT_version=(.*?)\n+MT_source=(.*?)\n", sc):
        if mt[2] == sent_seg:
            if mt[1].startswith("scriptsmt"):
                mtname = "edi-nmt"
            elif mt[1].startswith("umd-nmt"):
                mtname = "umd-nmt"
            elif mt[1].startswith("umd-smt"):
                mtname = "umd-smt"
            else:
                #raise Exception("Bad mt name")
                warnings.warn("MT NAME NOT RECOGNIZED: {} -- SKIPPING".format(mt[1]))
                continue

            if mtname in use_mt:
                mtpath = meta["corpus_prefix"] / mt[0]

                mtmorphpath = meta["corpus_prefix"] / morphs[mt[0]]
                translations.append(
                    {"name": mtname, "path": str(mtpath), 
                     "morph": str(mtmorphpath)})

    corpus = {
        "source": str(meta["corpus_prefix"] / src),
        "sentence_segmentation": str(meta["corpus_prefix"] / sent_seg),
        "source_morphology": str(meta["corpus_prefix"] / src_morph),
        "translations": translations,
    }

    return corpus

def get_audio_config(meta, sc, use_mt):

    morphs = {
        morph[2]: Path(morph[0])
        for morph in re.findall(r"Morpohological_Analysis_location=(.*?)\n+Morpohological_(?:Analyzer|Analysis)_version=(.*?)\n+Morpohological_(?:Analyzer|Analysis)_source=(.*?)\n", sc)
    }
 
    src = re.search(r"source_location=(.*?)\n", sc).groups()[0]
    asr = re.search(
        r"ASR_location=(.*?)\nASR_version=material", sc).groups()[0]
    asr_morph = morphs[asr]

    translations = []
    for mt in re.findall(r"MT_location=(.*?)\n+MT_version=(.*?)\n+MT_source=(.*?)\n", sc):
        if mt[2] == asr:
            if mt[1].startswith("scriptsmt"):
                mtname = "edi-nmt"
            elif mt[1].startswith("umd-nmt"):
                mtname = "umd-nmt"
            elif mt[1].startswith("umd-smt"):
                mtname = "umd-smt"
            else:
                #raise Exception("Bad mt name")
                warnings.warn("MT NAME NOT RECOGNIZED: {} -- SKIPPING".format(mt[1]))
                continue

            if mtname in use_mt:
                mtpath = meta["corpus_prefix"] / mt[0]
                mtmorphpath = meta["corpus_prefix"] / morphs[mt[0]]
                translations.append(
                    {"name": mtname, "path": str(mtpath), 
                     "morph": str(mtmorphpath)})

    corpus = {
        "asr": str(meta["corpus_prefix"] / asr),
        "asr_morphology": str(meta["corpus_prefix"] / asr_morph),
        "translations": translations,
    }

    seg_m = re.search(r"SentSplitter_location=(.*?)\n", sc)
    if seg_m:
        asr_seg = seg_m.groups()[0]
        asr_seg_morph = morphs[asr_seg]
        seg_translations = []
        for mt in re.findall(r"MT_location=(.*?)\n+MT_version=(.*?)\n+MT_source=(.*?)\n", sc):
            if mt[2] == asr_seg:
                if mt[1].startswith("scriptsmt"):
                    mtname = "edi-nmt"
                elif mt[1].startswith("umd-nmt"):
                    mtname = "umd-nmt"
                elif mt[1].startswith("umd-smt"):
                    mtname = "umd-smt"
                else:
                    raise Exception("Bad mt name")

                if mtname in use_mt:
                    mtpath = meta["corpus_prefix"] / mt[0]
                    mtmorphpath = meta["corpus_prefix"] / morphs[mt[0]]
                    seg_translations.append(
                        {"name": mtname, "path": str(mtpath), 
                         "morph": str(mtmorphpath)})

        corpus2 = {
            "asr": str(meta["corpus_prefix"] / asr_seg),
            "asr_morphology": str(meta["corpus_prefix"] / asr_seg_morph),
            "translations": seg_translations
        }

        return {"source": str(meta["corpus_prefix"] / src),
                "TB": corpus, "NB": corpus, "CS": corpus2}

    return {"source": str(meta["corpus_prefix"] / src),
            "TB": corpus, "NB": corpus, "CS": corpus}

def proc_ds(config, use_mt=None):

    if use_mt is None:
        use_mt = ["umd-smt", "umd-nmt", "edi-nmt"]

    config = config[config.index("[corpus_"):]
    
    corpora = {}

    subconfigs = re.split(r"\[corpus_\d+\]\n", config, flags=re.DOTALL)[1:]
    for sc in subconfigs:
        meta = get_subconfig_meta(sc)
        if meta["mode"] == "text":
            corpus = get_text_config(meta, sc, use_mt)
        else:
            corpus = get_audio_config(meta, sc, use_mt)

        langpart = meta["lang"] + "-" + Path(meta["name"]).name
        index = Path(meta["name"]) / "index.txt"
        if langpart not in corpora:
            corpora[langpart] = {
                "lang": meta["lang"],
                "name": langpart,
                "index": str(index),
            }
        if meta["mode"] == "audio":
            corpora[langpart]["audio_metadata"] = str(
                meta["corpus_prefix"] / "audio" / "metadata" / "metadata.tsv"
            )
        corpora[langpart][meta["mode"]] = corpus

    return list(corpora.values())

if __name__ == "__main__":
    main()
