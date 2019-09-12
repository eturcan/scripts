import logging 

def resolve_audio_source(result):
    source_path = result["dataset"] / "audio" / "src" / "{}.wav".format(
        result["id"])
    if not source_path.exists():
        raise Exception("Source path {} does not exist.".format(source_path))
    result["source"] = source_path

def parse_audio_asr_name(name):
    system, system_ver = name.rsplit("-v", 1)
    system_name = system.rsplit("-", 1)[0]
    return {"name": system_name, "ver": system_ver}

def resolve_audio_asr(result):
    asr_store = result["dataset"] / "audio" / "asr_store"
    asr_dirs = [asr for asr in asr_store.glob("*") if asr.is_dir()]
    possible_asrs = [asr_dir / "{}.utt".format(result["id"]) 
                    for asr_dir in asr_dirs]
    asrs = {}
    for path in possible_asrs:
        ctm_path = path.parent / "{}.ctm".format(path.stem)
        if not path.exists():
            logging.warn(
                "Missing source asr file: {}".format(path))
        elif not ctm_path.exists():
            logging.warn(
                "Missing source asr file: {}".format(ctm_path))
        else:
            asr_info = parse_audio_asr_name(path.parent.name)
            asr_info["utterance_path"] = path
            asr_info["token_path"] = ctm_path
            asrs[path.parent.name] = asr_info
    
    result["asr"] = asrs

def parse_audio_ma_name(name):
    morph, asr = name.split("_")
    morph_name, morph_ver = morph.rsplit("-v", 1)
    asr_name, asr_ver = asr.rsplit("-v", 1)
    asr_name = asr_name.rsplit("-", 1)[0]
    return {
        "name": morph_name,
        "ver": morph_ver,
        "asr": {
            "name": asr_name,
            "ver": asr_ver,
        },
    }

def resolve_audio_asr_morphology(result):
    ma_store = result["dataset"] / "audio" / "morphology_store"
    ma_dirs = [ma for ma in ma_store.glob("*") if ma.is_dir()]
    possible_mas = [ma_dir / "{}.txt".format(result["id"]) 
                    for ma_dir in ma_dirs
                    if len(ma_dir.name.split("_")) == 2] 
                    #if not ma_dir.name.endswith("transcription_source")]
    mas = {}
    for path in possible_mas:
        if not path.exists():
            logging.warn("Missing source morphology file: {}".format(path))
        else:
            ma_info = parse_audio_ma_name(path.parent.name)
            ma_info["path"] = path
            mas[path.parent.name] = ma_info
    
    result["asr_morphology"] = mas

def parse_audio_mt_name(name):
    mt, asr = name.split("_")
    mt_name, mt_ver = mt.rsplit("-v", 1)
    asr_name, asr_ver = asr.rsplit("-v", 1)
    asr_name = asr_name.rsplit("-", 1)[0]

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

    return {
        "name": mt_name,
        "site": site,
        "type": type,
        "ver": mt_ver,
        "asr": {
            "name": asr_name,
            "ver": asr_ver,
        },
    }

def resolve_audio_asr_translation(result):
    mt_store = result["dataset"] / "audio" / "mt_store"
    translation_dirs = [mt for mt in mt_store.glob("*") if mt.is_dir()]
    possible_translations = [mt_dir / "{}.txt".format(result["id"]) 
                             for mt_dir in translation_dirs
                             if not mt_dir.name.endswith("transcription_source")]
    translations = {}
    for path in possible_translations:
        if not path.exists():
            logging.warn("Missing translation file: {}".format(path))
        else:
            mt_info = parse_audio_mt_name(path.parent.name)
            mt_info["path"] = path
            translations[path.parent.name] = mt_info
    
    result["asr_translations"] = translations


def parse_asr_translation_ma_name(name):
    ma, mt, asr = name.split("_")
    ma_name, ma_ver = ma.rsplit("-v", 1)
    mt_name, mt_ver = mt.rsplit("-v", 1)
    asr_name, asr_ver = asr.rsplit("-v", 1)
    asr_name = asr_name.rsplit("-", 1)[0]

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

    return {
        "name": ma_name,
        "ver": ma_ver,
        "asr": {
            "name": asr_name,
            "ver": asr_ver,
        },
        "translation": {
            "name": mt_name,
            "site": site,
            "type": type,
            "ver": mt_ver,
        },
    }

def resolve_audio_asr_translation_morphology(result):
    ma_store = result["dataset"] / "audio" / "morphology_store"
    ma_dirs = [ma for ma in ma_store.glob("*") if ma.is_dir()]
    possible_mas = [ma_dir / "{}.txt".format(result["id"]) 
                    for ma_dir in ma_dirs
                    if len(ma_dir.name.split("_")) == 3 
                    and not ma_dir.name.endswith("transcription_source")]
    mas = {}
    for path in possible_mas:
        if not path.exists():
            logging.warn("Missing source morphology file: {}".format(path))
        else:
            ma_info = parse_asr_translation_ma_name(path.parent.name)
            ma_info["path"] = path
            mas[path.parent.name] = ma_info
    
    result["asr_translation_morphology"] = mas

def collect_speech_annotations(result):
     resolve_audio_source(result)  
     resolve_audio_asr(result)
     resolve_audio_asr_morphology(result)
     resolve_audio_asr_translation(result)
     resolve_audio_asr_translation_morphology(result)
