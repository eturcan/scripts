import logging


def parse_text_mt_name(name):
    system, sent_split = name.split("_")
    ssplit_ver = sent_split.split("v")[-1]
    ssplit_name = sent_split.rsplit("-", 1)[0]
    system_name, system_ver = system.rsplit("-v", 1)
    if system_name == "scriptsmt-systems":
        site = "edi"
        type = "nmt"
    elif system_name == "umd-smt":
        site = "umd"
        type = "smt"
    elif system_name == "umd-nmt":
        site = "umd"
        type = "nmt"
    else:
        site = "unk"
        type = "unk"

    mt_info = {
        "name": system_name,
        "site": site,
        "type": type,
        "ver": system_ver,
        "sentence_segmentation": {
            "ver": ssplit_ver,
            "name": ssplit_name,
        },
    }
    return mt_info

def resolve_text_translation(result):
    mt_store = (result["dataset"] / result["mode"] / "mt_store")
    translation_dirs = [mt for mt in mt_store.glob("*") if mt.is_dir()]
    possible_translations = [mt_dir / "{}.txt".format(result["id"]) 
                             for mt_dir in translation_dirs]
    translations = {}
    for path in possible_translations:
        if not path.exists():
            logging.warn("Missing translation file: {}".format(path))
        else:
            mt_info = parse_text_mt_name(path.parent.name)
            mt_info["path"] = path
            translations[path.parent.name] = mt_info
    
    result["translations"] = translations

def parse_text_ma_name(name):
    system, sent_split = name.split("_")
    ssplit_ver = sent_split.split("v")[-1]
    ssplit_name = sent_split.rsplit("-", 1)[0]
    system_name, system_ver = system.rsplit("-v", 1)
    ma_info = {
        "name": system_name,
        "ver": system_ver,
        "sentence_segmentation": {
            "ver": ssplit_ver,
            "name": ssplit_name,
        },
    }
    return ma_info

def resolve_text_source_morphology(result):
    ma_store = result["dataset"] / result["mode"] / "morphology_store"
    ma_dirs = [ma for ma in ma_store.glob("*") if ma.is_dir()]
    possible_mas = [ma_dir / "{}.txt".format(result["id"]) 
                    for ma_dir in ma_dirs
                    if len(ma_dir.name.split("_")) == 2]
    mas = {}
    for path in possible_mas:
        if not path.exists():
            logging.warn("Missing source morphology file: {}".format(path))
        else:
            ma_info = parse_text_ma_name(path.parent.name)
            ma_info["path"] = path
            mas[path.parent.name] = ma_info
    
    result["source_morphology"] = mas

def parse_text_translation_ma_name(name):
    system, mt_system, sent_split = name.split("_")
    ssplit_ver = sent_split.split("v")[-1]
    ssplit_name = sent_split.rsplit("-", 1)[0]
    system_name, system_ver = system.rsplit("-v", 1)
    mt_name, mt_ver = mt_system.rsplit("-v", 1)
    if mt_name == "scriptsmt-systems":
        site = "edi"
        type = "nmt"
    elif mt_name == "umd-smt":
        site = "umd"
        type = "smt"
    elif mt_name == "umd-nmt":
        site = "umd"
        type = "nmt"
    else:
        site = "unk"
        type = "unk"
   
    ma_info = {
        "name": system_name,
        "ver": system_ver,
        "sentence_segmentation": {
            "ver": ssplit_ver,
            "name": ssplit_name,
        },
        "translation": {
            "name": mt_name,
            "site": site,
            "type": type,
            "ver": mt_ver,
        }
    }
    return ma_info



def resolve_text_translation_morphology(result):
    ma_store = result["dataset"] / result["mode"] / "morphology_store"
    ma_dirs = [ma for ma in ma_store.glob("*") if ma.is_dir()]
    possible_mas = [ma_dir / "{}.txt".format(result["id"]) 
                    for ma_dir in ma_dirs
                    if len(ma_dir.name.split("_")) == 3]
    mas = {}
    for path in possible_mas:
        if not path.exists():
            logging.warn("Missing source morphology file: {}".format(path))
        else:
            ma_info = parse_text_translation_ma_name(path.parent.name)
            ma_info["path"] = path
            mas[path.parent.name] = ma_info
    
    result["translation_morphology"] = mas



def resolve_text_source(result):
    source_path = result["dataset"] / result["mode"] / "src" / "{}.txt".format(
        result["id"])
    if not source_path.exists():
        raise Exception("Source path {} does not exist.".format(source_path))
    result["source"] = source_path

def parse_text_ss_name(name):
    system_name, system_ver = name.rsplit("-v", 1)
    return {"name": system_name, "ver": system_ver}

def resolve_text_source_sentence_segmentation(result):
    ss_store = result["dataset"] / result["mode"] / "sentSplitter_store"
    ss_dirs = [ss for ss in ss_store.glob("*") if ss.is_dir()]
    possible_ss = [ss_dir / "{}.txt".format(result["id"]) 
                    for ss_dir in ss_dirs]
    ss = {}
    for path in possible_ss:
        if not path.exists():
            logging.warn(
                "Missing source sentence segmentation file: {}".format(path))
        else:
            ss_info = parse_text_ss_name(path.parent.name)
            ss_info["path"] = path
            ss[path.parent.name] = ss_info
    
    result["source_sentence_segmentation"] = ss


def collect_text_annotations(result):
    resolve_text_source(result)
    resolve_text_source_sentence_segmentation(result)
    resolve_text_translation(result)
    resolve_text_source_morphology(result)
    resolve_text_translation_morphology(result)
