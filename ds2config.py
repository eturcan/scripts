import argparse 
from pathlib import Path
import re
from pprint import pprint
from scripts_sum.lang import get_material
import json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()

    configs = []
    for path in args.paths:
        for x in proc_ds(path.read_text()):
            configs.append(x)
    print(json.dumps(configs, indent="    "))


def proc_ds(config):

    config = config[config.index("[corpus_"):]
    #print(config[:25])
    
    corpora = {}

    subconfigs = re.split(r"\[corpus_\d+\]\n", config, flags=re.DOTALL)[1:]
    for sc in subconfigs:
        name = sc[:sc.index("\n")].split("=")[1]
        sc = sc[sc.index("\n") + 1:]
        lang = sc[:sc.index("\n")].split("=")[1]
        lang = get_material(lang)
        sc = sc[sc.index("\n") + 1:]
        
        mode = sc[:sc.index("\n")].split("=")[1]
        sc = sc[sc.index("\n") + 1:]
        corpus_prefix = Path(name)

        morphs = {
            morph[2]: Path(morph[0])
            for morph in re.findall(r"Morpohological_Analysis_location=(.*?)\n+Morpohological_(?:Analyzer|Analysis)_version=(.*?)\n+Morpohological_(?:Analyzer|Analysis)_source=(.*?)\n", sc)
        }
            
        src = re.search(
            r"source_location=(.*?)\n", sc).groups()[0]
        if mode == "text":
            sent_seg = re.search(
                r"SentSplitter_location=(.*?)\n", sc).groups()[0]
            src_morph = morphs[sent_seg]
        
        else:        
            asr = re.search(
                r"ASR_location=(.*?)\nASR_version=material", sc).groups()[0]

            asr_morph = morphs[asr]

        translations = []
        for mt in re.findall(r"MT_location=(.*?)\n+MT_version=(.*?)\n+MT_source=(.*?)\n", sc):
            if mt[2] == (sent_seg if mode == "text" else asr):
                if mt[1].startswith("scriptsmt"):
                    mtname = "edi-nmt"
                elif mt[1].startswith("umd-nmt"):
                    mtname = "umd-nmt"
                elif mt[1].startswith("umd-smt"):
                    mtname = "umd-smt"
                else:
                    raise Exception("Bad mt name")
                mtpath = corpus_prefix / Path(mt[0])
                mtmorphpath = corpus_prefix / morphs[mt[0]]
                translations.append(
                    {"name": mtname, "path": str(mtpath), "morph": str(mtmorphpath)})
            
            if mode == "text":
                corpus = {
                    "source": str(corpus_prefix / Path(src)),
                    "sentence_segmentation": str(corpus_prefix / Path(sent_seg)),
                    "source_morphology": str(corpus_prefix / Path(src_morph)),
                    "translations": translations,
                }
            else:
                corpus = {
                    "source": str(corpus_prefix / Path(src)),
                    "asr": str(corpus_prefix / Path(asr)),
                    "asr_morphology": str(corpus_prefix / Path(asr_morph)),
                    "translations": translations,
                }
        langpart = lang + "-" + Path(name).name
        index = Path(name) / "index.txt"
        if langpart not in corpora:
            corpora[langpart] = {
                "lang": lang,
                "name": langpart,
                "index": str(index),
            }
        corpora[langpart][mode] = corpus

    return list(corpora.values())

if __name__ == "__main__":
    main()
