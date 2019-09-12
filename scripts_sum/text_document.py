import json
import re
from .token import Token
from .utterance import Utterance
from .annotated_document import AnnotatedDocument
from . import cleaning as cleaning




NON_BREAKING = set(
    [",", ";", "-RRB-", ".", "?", "''", "'m", "!", "...", "'s", "n't",
     "'ll", "'all", "'re", "'d", "'ve"])

TWOSIDED = set(["--", ":", "-", "/" ])

SPACE_CONSUMING = set(["``", "`", "(", "$"])


class TextDocument(AnnotatedDocument):
    @staticmethod 
    def new(source_path, segmentation_path, source_morphology_path, 
            translation_paths, translation_morphology_paths, doc_id=None,
            lang=None, relevance_score=None):

        src_text = source_path.read_text()
        sent_segment_lines = segmentation_path.read_text().split("\n")
        src_morph_lines = source_morphology_path.read_text().split("\n")
        all_translation_lines = {
            name: path.read_text().split("\n")
            for name, path in translation_paths.items()
        }
        all_translation_morph_lines = {
            name: path.read_text().split("\n")
            for name, path in translation_morphology_paths.items()
        }

        final_sent_segments = []
        final_src_morph = []
        final_translations = {name: list()
                              for name in all_translation_lines.keys()}
        final_translation_morphs = {
            name: list()
            for name in all_translation_morph_lines.keys()
        }
        for i in range(len(sent_segment_lines)):
            src_morph = json.loads(src_morph_lines[i])
            sent_seg = sent_segment_lines[i]
            if len(src_morph) == 0:
                if sent_seg.strip() != "":
                    raise RuntimeError(
                        "Bad morph/segmentation alignment: {}".format(
                            result["id"]))
                continue
            final_sent_segments.append(sent_seg)
            final_src_morph.append(src_morph)
            for name, trans in all_translation_lines.items():
                final_translations[name].append(trans[i])
            for name, trans in all_translation_morph_lines.items():
                final_translation_morphs[name].append(json.loads(trans[i]))

        num_utt = len(final_sent_segments)
        utterances = []   
 
        for i in range(num_utt):
            src_seg = final_sent_segments[i]
            m = re.search(re.escape(src_seg).replace(r"\ ", r"\s+"), src_text)
            if m is None:
                raise RuntimeError(
                    "No match for doc {} source sentence [[[{}]]]".format(
                        result["id"], src_seg))
            start = m.start()
            stop = m.end() - 1
            src_tokens = Token.tokens_from_morphology(final_src_morph[i])
            src_utt = Utterance(final_sent_segments[i], src_tokens,
                                offsets=(start, stop))
            
            src_trans = {}
            for name, translation in final_translations.items():
                if len(final_translation_morphs[name][i]) == 0:
                    tr_tokens = []
                else:
                    tr_tokens = Token.tokens_from_morphology(
                        final_translation_morphs[name][i])
                tr_text = translation[i]
                tr_utt = Utterance(tr_text, tr_tokens)
              
                src_trans[name] = tr_utt
            utterances.append({"source": src_utt, "translations": src_trans})
        doc = TextDocument(doc_id, "text", lang, source_path, 
                           relevance_score, utterances)
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

                start = utt["source"].offsets[0] + m.start()
                end = utt["source"].offsets[0] + m.end() - 1

                self._token_annotations[str((start, end))] = info
