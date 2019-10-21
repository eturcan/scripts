import json
import re
from .token import Token
from .utterance import Utterance
from .annotated_document import AnnotatedDocument
from . import cleaning as cleaning
from collections import defaultdict


class SpeechDocument(AnnotatedDocument):
    @staticmethod
    def new(source_path, asr_paths, asr_morphology_path, translation_paths,
            translation_morphology_paths, doc_id=None, lang=None, 
            relevance_score=None):

        asr_path = asr_paths["utterances"]
        asr_tokens_path = asr_paths["tokens"]
        asr_tokens = defaultdict(list)
        for line in asr_tokens_path.read_text().strip().split("\n"):
            if "\t" in line:
                spkr, start, dur, tok, conf = line.split("\t")[1:]
            else:
                spkr, start, dur, tok, conf = line.split()[1:]
            for st in tok.replace("_", " _ ").split(" "):
                asr_tokens[spkr].append({
                    "offsets": (float(start), float(start) + float(dur)),
                    "token": st,
                    "confidence": float(conf)
                })

        asr_lines = asr_path.read_text().strip().split("\n")
        asr_morph_lines = asr_morphology_path.read_text().strip().split("\n")
        all_translation_lines = {
            name: path.read_text().strip().split("\n")
            for name, path in translation_paths.items()
        }
        all_translation_morph_lines = {
            name: path.read_text().split("\n")
            for name, path in translation_morphology_paths.items()
        }

        final_asr_lines = []
        final_asr_morph = []
        final_translations = {name: list()
                              for name in all_translation_lines.keys()}
        final_translation_morphs = {
            name: list()
            for name in all_translation_morph_lines.keys()
        }
        for i in range(len(asr_lines)):
            asr_line = asr_lines[i]
            asr_morph = json.loads(asr_morph_lines[i])
            if len(asr_morph) == 0:
                continue
            final_asr_lines.append(asr_line)
            final_asr_morph.append(asr_morph)
            for name, trans in all_translation_lines.items():
                final_translations[name].append(trans[i])
            for name, trans in all_translation_morph_lines.items():
                final_translation_morphs[name].append(json.loads(trans[i]))

        token_info_pos = defaultdict(int)
        num_utt = len(final_asr_lines)
        utterances = []
        for i in range(num_utt):
            
            if "\t" in final_asr_lines[i]:
                _, spkr, start, stop, src_text = final_asr_lines[i].split("\t")
            else:
                _, spkr, start, stop, src_text = final_asr_lines[i].split(" ", 4)

            src_tokens = Token.tokens_from_morphology(final_asr_morph[i]) 

            # THIS IS FRAGILE AND WILL BREAK! 
            if src_tokens[-1].word == ".":
                src_tokens = src_tokens[:-1]

            src_utt = Utterance(src_text, src_tokens, speaker=spkr,
                                offsets=(float(start), float(stop)))
            
            for T, token in enumerate(src_tokens, 1):
                idx = token_info_pos[spkr]
                if token.word.lower() != asr_tokens[spkr][idx]["token"].lower():
                    
                    print("ERROR!")
                    print(asr_tokens_path)
                    print(asr_path)
                    print("utt line {}: {}".format(i, " ".join([t.word for t in src_tokens])))
                    print("ctm expects token {} to be: {}".format(T,
                        asr_tokens[spkr][idx]["token"]))
                    print("utt expects token {} to be: {}".format(
                        T, token.word))
                    print()                   
 
                    raise RuntimeError("Bad ctm-utt alignment")
                token.offsets = asr_tokens[spkr][idx]["offsets"]
                token_info_pos[spkr] += 1
                 
            
            src_trans = {}
            for name, translation in final_translations.items():
                if len(final_translation_morphs[name][i]) == 0:
                    tr_tokens = []
                else:
                    tr_tokens = Token.tokens_from_morphology(
                        final_translation_morphs[name][i])
                tr_text = translation[i]
                tr_utt = Utterance(tr_text, tr_tokens, speaker=spkr,
                                   offsets=(start, stop))
              
                src_trans[name] = tr_utt

            utterances.append({"source": src_utt, "translations": src_trans})
        doc = SpeechDocument(doc_id, "speech", lang, source_path,
                             relevance_score, utterances)

        return doc


    @staticmethod 
    def from_result(result, asr_config, asr_morph_config, 
                    translations):
       
        asr_path = None
        for info in result["asr"].values():
            if info["ver"] == asr_config["ver"]:
                asr_path = info["utterance_path"]
                break
        asr_token_path = info["token_path"]
        asr_tokens = defaultdict(list)
        for line in asr_token_path.read_text().strip().split("\n"):
            spkr, start, dur, tok, conf = line.split()[1:]
            for st in tok.replace("_", " _ ").split(" "):
                asr_tokens[spkr].append({
                    "offsets": (float(start), float(start) + float(dur)),
                    "token": st,
                    "confidence": float(conf)
                })

        if asr_path is None:
            raise RuntimeError("No asr with version {}".format(
                asr_config["ver"]))

        asr_morph_path = None
        for info in result["asr_morphology"].values():
            if info["asr"]["ver"] != \
                    asr_config["ver"]:
                continue
            if info["ver"] == asr_morph_config["ver"]:
                asr_morph_path = info["path"]
                continue

        if asr_morph_path is None:
            raise RuntimeError(("No asr morphology with version {} on " \
                             "asr version {}").format(
                asr_morph_config["ver"], asr_config["ver"]))

        all_translations = {}
        all_translation_morphs = {}
        for translation in translations:
            translation_name = None
            translation_path = None
            translation_morph_path = None
            for name, info in result["asr_translations"].items():
                if info["asr"]["ver"] != \
                        asr_config["ver"]:
                    continue
                if info["site"] == translation["site"] and \
                        info["type"] == translation["type"] and \
                        info["ver"] == translation["ver"]:
                    translation_name = name
                    translation_path = info["path"]
                    break  
            if translation_path is None:
                raise RuntimeError(
                    "No translation version {} on asr {}".format(
                        translation["ver"], asr_config["ver"]))
            for m_name, m_info in result["asr_translation_morphology"].items():
                if m_info["translation"]["ver"] == info["ver"] and \
                        m_info["translation"]["site"] == info["site"] and \
                        m_info["translation"]["type"] == info["type"]:
                    translation_morph_path = m_info["path"]

            if translation_morph_path is None:
                raise RuntimeError(
                    ("No translation morph for mt version {} on " \
                     "sent seg {}").format(
                        translation["ver"], asr_config["ver"]))


            all_translations[translation_name] = translation_path           
            all_translation_morphs[translation_name] = translation_morph_path

        asr_lines = asr_path.read_text().strip().split("\n")
        asr_morph_lines = asr_morph_path.read_text().strip().split("\n")
        all_translation_lines = {
            name: path.read_text().strip().split("\n")
            for name, path in all_translations.items()
        }
        all_translation_morph_lines = {
            name: path.read_text().split("\n")
            for name, path in all_translation_morphs.items()
        }

        final_asr_lines = []
        final_asr_morph = []
        final_translations = {name: list()
                              for name in all_translation_lines.keys()}
        final_translation_morphs = {
            name: list()
            for name in all_translation_morph_lines.keys()
        }
        for i in range(len(asr_lines)):
            asr_line = asr_lines[i]
            asr_morph = json.loads(asr_morph_lines[i])
            if len(asr_morph) == 0:
                continue
            final_asr_lines.append(asr_line)
            final_asr_morph.append(asr_morph)
            for name, trans in all_translation_lines.items():
                final_translations[name].append(trans[i])
            for name, trans in all_translation_morph_lines.items():
                final_translation_morphs[name].append(json.loads(trans[i]))

        token_info_pos = defaultdict(int)
        num_utt = len(final_asr_lines)
        utterances = []
        for i in range(num_utt):
            _, spkr, start, stop, src_text = final_asr_lines[i].split("\t")  
            src_tokens = Token.tokens_from_morphology(final_asr_morph[i]) 
            src_utt = Utterance(src_text, src_tokens, speaker=spkr,
                                offsets=(float(start), float(stop)))
            for token in src_tokens:
                idx = token_info_pos[spkr]
                if token.word != asr_tokens[spkr][idx]["token"]:
                    raise RuntimeError("Bad ctm-utt alignment")
                token.offsets = asr_tokens[spkr][idx]["offsets"]
                token_info_pos[spkr] += 1
                 
            
            src_trans = {}
            for name, translation in final_translations.items():
                if len(final_translation_morphs[name][i]) == 0:
                    tr_tokens = []
                else:
                    tr_tokens = Token.tokens_from_morphology(
                        final_translation_morphs[name][i])
                tr_text = translation[i]
                tr_utt = Utterance(tr_text, tr_tokens, speaker=spkr,
                                   offsets=(start, stop))
              
                src_trans[name] = tr_utt

            utterances.append({"source": src_utt, "translations": src_trans})
        doc = SpeechDocument(result["id"], "speech", result["lang"],
                             result["source"],
                             result["relevance_score"], utterances)

        return doc

    def annotate_source_term(self, term, info, normalize=True):
        for utt in self:
            
            text = utt["source"].text

            for token in utt["source"].tokens:
                if normalize:
                    word = cleaning.normalize(self.source_lang["iso"], 
                                              token.word,
                                              False, False, False)            
                else:
                    word = token.word

                if word != term:
                    continue
                
                m = re.search(re.escape(token.word), text)
                text = (
                    text[:m.start()] + " " * (m.end() - m.start()) 
                    + text[m.end():]
                )   

                #start = utt["source"].offsets[0] #+ m.start()
                #end = utt["source"].offsets[1] #+ m.end() - 1

                self._token_annotations[str(token.offsets)] = info
