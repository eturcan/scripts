import argparse
from pathlib import Path
import re
from subprocess import check_output, Popen
import subprocess
from scripts_sum.lang import get_iso
import json




cargs = {
    "2B-ANALYSIS": {
        "lang": "2B",
        "part": "ANALYSIS",
        "index": "2B/IARPA_MATERIAL_OP1-2B/ANALYSIS/index.txt",
        "text": "2B/IARPA_MATERIAL_OP1-2B/ANALYSIS/text/translation",
        "audio": "2B/IARPA_MATERIAL_OP1-2B/ANALYSIS/audio/translation",
    },
#    "2S-ANALYSIS": {
#        "lang": "2S",
#        "part": "ANALYSIS",
#        "index": "2S/IARPA_MATERIAL_OP1-2S/ANALYSIS/index.txt",
#        "text": "2S/IARPA_MATERIAL_OP1-2S/ANALYSIS/text/translation",
#        "audio": "2S/IARPA_MATERIAL_OP1-2S/ANALYSIS/audio/translation",
#    },
}



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("nist", type=Path)
    parser.add_argument("refdir", type=Path)
    parser.add_argument("en_port")
    parser.add_argument("fgn_port")
    parser.add_argument("jar", type=Path)
    args = parser.parse_args()


    lang_server = None
    try:
        en_server = Popen(["java", "-jar", str(args.jar), args.en_port, "EN",],
                           cwd=str(args.jar.parent))
        
        import time
        time.sleep(2)


        for name, config in cargs.items():
            lang = get_iso(config["lang"]).upper()
            lang_server = Popen(
                ["java", "-jar", str(args.jar), args.fgn_port, lang],
                cwd=str(args.jar.parent))
            time.sleep(2)
            make_ref_corpus(args.nist, args.refdir, config,
                            args.en_port, args.fgn_port, args.jar)

            lang_server.kill()
            lang_server = None

    finally:
        en_server.kill()
        if lang_server is not None:
            lang_server.kill()

def make_ref_corpus(root_dir, ref_dir, config, en_port, fgn_port, jar):


    lang = get_iso(config["lang"]).upper()
    src_text_dir = root_dir / config["text"]
    src_audio_dir = root_dir / config["audio"]

    tgt_src_text_dir = ref_dir / config["lang"] / "text" / "src"
    tgt_src_morph_text_dir = (
        ref_dir / config["lang"] / "text" / "src_morphology"
    )
    tgt_trans_text_dir = ref_dir / config["lang"] / "text" / "translation"
    tgt_trans_morph_text_dir = (
        ref_dir / config["lang"] / "text" / "translation_morphology"
    )

    wav_dir = ref_dir / config["lang"] / "audio" / "src"
    tgt_src_dir = ref_dir / config["lang"] / "audio" / "transcript"
    tgt_src_morph_dir = (
        ref_dir / config["lang"] / "audio" / "transcript_morphology"
    )
    tgt_asr_dir = ref_dir / config["lang"] / "audio" / "asr"
    tgt_asr_trans_dir = ref_dir / config["lang"] / "audio" / "translation"
    tgt_asr_trans_morph_dir = (
        ref_dir / config["lang"] / "audio" / "translation_morphology"
    )
    make_text_data(src_text_dir, tgt_src_text_dir, tgt_src_morph_text_dir,
                   tgt_trans_text_dir, tgt_trans_morph_text_dir, en_port, 
                   fgn_port, jar, lang)
                    
    make_audio_data(src_audio_dir, wav_dir, tgt_src_dir, tgt_src_morph_dir, 
                    tgt_asr_dir,
                    tgt_asr_trans_dir, 
                    tgt_asr_trans_morph_dir,
                    en_port, fgn_port, jar, lang)

    index_path = ref_dir / config["lang"] / "index.txt"
    index_path.write_text((root_dir / config["index"]).read_text())
 
def make_text_data(orig_dir, src_dir, src_morph_dir, trans_dir, 
                   trans_morph_dir, en_port, fgn_port, jar, lang):
    
    src_dir.mkdir(exist_ok=True, parents=True)
    src_morph_dir.mkdir(exist_ok=True, parents=True)
    trans_dir.mkdir(exist_ok=True, parents=True)
    trans_morph_dir.mkdir(exist_ok=True, parents=True)

    for path in orig_dir.glob("MATERIAL*"):
        print(path)
        doc_id = path.name.split(".")[0]

        src_path = src_dir / "{}.txt".format(doc_id)
        src_morph_path = src_morph_dir / "{}.txt".format(doc_id)
        tgt_path = trans_dir / "{}.txt".format(doc_id)
        tgt_morph_path = trans_morph_dir / "{}.txt".format(doc_id)
        with path.open("r") as fp:
            with src_path.open("w") as s_fp, tgt_path.open("w") as t_fp: 
                src_lines = []
                tgt_lines = []
                for line in fp:

                    _, src_txt, tgt_txt = line.strip().split("\t")
                    tgt_lines.append(tgt_txt)
                    src_lines.append(src_txt) 
                print("\n".join(src_lines), file=s_fp, end='')
                print("\n".join(tgt_lines), file=t_fp, end='')

        src_morph_args = ["java", "-jar", 
            jar,
            fgn_port, lang, str(src_path), str(src_morph_path)]

        check_output(src_morph_args)

#        wc_a = check_output(["wc", "-l", str(src_path)])\
#            .decode("utf8").split()[0]
#        wc_b = check_output(["wc", "-l", str(src_morph_path)])\
#            .decode("utf8").split()[0]
#        if wc_a != wc_b:
#            print("Bad lines!")
#            print(src_path)
#            print(wc_a)
#            print(src_morph_path)
#            print(wc_b)
#            print()
 
        tgt_morph_args = ["java", "-jar", 
            jar,
            en_port, "EN", str(tgt_path), str(tgt_morph_path)]

        check_output(tgt_morph_args)

#        wc_a = check_output(["wc", "-l", str(tgt_path)])\
#            .decode("utf8").split()[0]
#        wc_b = check_output(["wc", "-l", str(tgt_morph_path)])\
#            .decode("utf8").split()[0]
#        if wc_a != wc_b:
#            print("Bad lines!")
#            print(tgt_path)
#            print(wc_a)
#            print(tgt_morph_path)
#            print(wc_b)
#            print()

def make_audio_data(orig_dir, wav_dir, src_dir, src_morph_dir, asr_dir, trans_dir, 
                    trans_morph_dir, en_port, fgn_port, jar, lang):

    wav_dir.mkdir(exist_ok=True, parents=True)
    src_dir.mkdir(exist_ok=True, parents=True)
    src_morph_dir.mkdir(exist_ok=True, parents=True)
    asr_dir.mkdir(exist_ok=True, parents=True)
    trans_dir.mkdir(exist_ok=True, parents=True)
    trans_morph_dir.mkdir(exist_ok=True, parents=True)

    for path in orig_dir.glob("MATERIAL*"):
        print(path)
        doc_id = path.name.split(".")[0]
         
        wav_path = wav_dir / "{}.wav".format(doc_id)
        wav_path.touch()
        src_path = src_dir / "{}.txt".format(doc_id)
        src_morph_path = src_morph_dir / "{}.txt".format(doc_id)
        tgt_path = trans_dir / "{}.txt".format(doc_id)
        asr_utt_path = asr_dir / "{}.utt".format(doc_id)
        asr_ctm_path = asr_dir / "{}.ctm".format(doc_id)
        tgt_morph_path = trans_morph_dir / "{}.txt".format(doc_id)
        with path.open("r") as fp:
            utt_lines = []
            transcript_lines = []
            ctm_lines = []
            translation_lines = []

            for line in fp:
                _, time, src_txt, tgt_txt = line.strip().split("\t")
                src_txt = src_txt.replace("<no-speech>", "")\
                    .replace("(())", "")
                src_txt = re.sub(r"<.*?>", "", src_txt)
                src_txt = src_txt.replace("_", "")
                src_txt = src_txt.strip()
                
                tgt_txt = tgt_txt.replace("<no-speech>", "")\
                    .replace("(())", "").strip()
                tgt_txt = re.sub(r"<.*?>", "", tgt_txt)
                tgt_txt = tgt_txt.replace("_", "")
                tgt_txt = tgt_txt.strip()

                if src_txt == '' and tgt_txt == '':
                    continue
                if src_txt == '.' and tgt_txt == '.':
                    continue
                if src_txt == '?' and tgt_txt == '?':
                    continue
                if "," not in time:
                    times = time[1:-1].split("-")
                    speaker = "1"
                else:
                    times = time.split(", ")[1][1:-1].split("-")
                    speaker = "A" if "Inline" in time else "B"

                utt_lines.append(
                    [doc_id, speaker] + times + [src_txt])

#                    print(tgt_txt, file=t_fp)
#                    print(src_txt, file=s_fp)
                transcript_lines.append(src_txt)
                translation_lines.append(tgt_txt)
            #with tgt_path.open("w") as t_fp, src_path.open("w") as s_fp, \
           #         asr_utt_path.open("w") as utt_fp, \
           #         asr_ctm_path.open("w") as ctm_fp:

            with src_path.open("w") as s_fp:
                print("\n".join(transcript_lines), file=s_fp, end='')        
            with tgt_path.open("w") as fp:
                print("\n".join(translation_lines), file=fp, end='')

            src_morph_args = ["java", "-jar",
                jar,
                fgn_port, lang, str(src_path), str(src_morph_path)]
            check_output(src_morph_args)
#?            wc_a = check_output(["wc", "-l", str(src_path)])\
#?                .decode("utf8").split()[0]
#?            wc_b = check_output(["wc", "-l", str(src_morph_path)])\
#?                .decode("utf8").split()[0]
#?            if wc_a != wc_b:
#?                print("Bad lines!")
#?                print(tgt_path)
#?                print(wc_a)
#?                print(tgt_morph_path)
#?                print(wc_b)
#?                print()

            
           
            with src_morph_path.open("r") as fp:
                for line, utt in zip(fp, utt_lines):

                    tokens = []
                    for x in json.loads(line):
                        for y in x:
                            tokens.append(y["word"])
                    utt[-1] = " ".join(tokens)
                    start_time = float(utt[2])
                    dur = (float(utt[3]) - float(utt[2])) / (.001 + len(tokens))
                    for token in tokens:
                        ctm_lines.append(
                            [utt[0], utt[1], start_time, dur, token])
                        start_time += dur

            utt_lines = ["{}\t{}\t{}\t{}\t{}".format(*utt) 
                         for utt in utt_lines]
            with asr_utt_path.open("w") as fp:
                print("\n".join(utt_lines), file=fp, end='')
            tgt_morph_args = ["java", "-jar", 
                jar,
                en_port, "EN", str(tgt_path), str(tgt_morph_path)]

            check_output(tgt_morph_args)

#            wc_a = check_output(["wc", "-l", str(tgt_path)])\
#                .decode("utf8").split()[0]
#            wc_b = check_output(["wc", "-l", str(tgt_morph_path)])\
#                .decode("utf8").split()[0]
#            if wc_a != wc_b:
#                print("Bad lines!")
#                print(tgt_path)
#                print(wc_a)
#                print(tgt_morph_path)
#                print(wc_b)
#                print()
            
            ctm_lines = ["{}\t{}\t{}\t{}\t{}\t1.0".format(*x)
                         for x in ctm_lines]
            
            with asr_ctm_path.open("w") as fp:
                print("\n".join(ctm_lines), file=fp, end='')

if __name__ == "__main__":
    main()
