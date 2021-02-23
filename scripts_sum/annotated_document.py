import numpy as np
import json
import hashlib


class AnnotatedDocument:
    def __init__(self, id, mode, source_lang, source_path, relevance_score, 
                 utterances):
        self._id = id
        self._source_lang = source_lang
        self._mode = mode
        self._source_path = source_path
        self._relevance_score = relevance_score
        self._utterances = tuple(utterances)
        self._translations = tuple(self.utterances[0]["translations"])
        self._annotations = {}
        self._token_annotations = {}
        self._md5 = None
        self._utterance_inds = None
        
    @property
    def md5(self):
        if self._md5 is None:
            with self.source_path.open("rb") as fp:
                self._md5 = hashlib.md5(fp.read()).hexdigest()
        return self._md5        

    @property
    def id(self):
        return self._id

    @property
    def mode(self):
        return self._mode

    @property
    def source_path(self):
        return self._source_path

    @property
    def relevance_score(self):
        return self._relevance_score

    @property
    def utterances(self):
        return self._utterances

    @property
    def translations(self):
        return self._translations

    @property
    def source_lang(self):
        return self._source_lang

    @property
    def annotations(self):
        return self._annotations

    @property
    def utterance_inds(self):
        return self._utterance_inds

    def set_utterance_inds(self, inds):
        self._utterance_inds = inds

    def __iter__(self):
        for utt in self.utterances:
            yield utt

    def __str__(self):
        import textwrap
        buf = []
        src_tmp = "{:" + str(len(str(len(self.utterances)))) + "} src: {}"
        tr_tmp = "{:" + str(len(str(len(self.utterances)))) + "}  tr: {}"
        for i, utt in enumerate(self, 1):
            buf.append(textwrap.fill(
                src_tmp.format(i, utt["source"].text),
                subsequent_indent="        "))
            for tr_name in self.translations:
                buf.append(textwrap.fill(
                    tr_tmp.format(i, utt["translations"][tr_name].text),
                    subsequent_indent="        "))
       
        return "\n".join(buf)

    def translation_sentence_embeddings(self, translation, word_embeddings):
        utt_embs = []
        for utt_opts in self:
            utt = utt_opts["translations"][translation]
            utt_emb = []
            for token in utt.tokens:
                token = token.word.lower()
                if token in word_embeddings:
                    utt_emb.append(word_embeddings[token])
            if len(utt_emb) > 0:
                utt_emb = sum(utt_emb) / len(utt_emb)
            else:
                utt_emb = np.array([float("nan")] * word_embeddings.dims)
                #raise Exception("no words in sentence")
            utt_embs.append(utt_emb)
        utt_embs = np.vstack(utt_embs)
        return utt_embs
    
    def annotate_utterances(self, ann_name, data):
          
        #if data[1] is None:
        #    pass
        #elif len(data[1]) != len(self.utterances):
        #    raise Exception(
        #        "{} has inconsistent length, got {} but expected {}".format(
        #            ann_name, len(data[1]), len(self.utterances)))
        self._annotations[ann_name] = data
        
    def annotation_json(self):
        return json.dumps({
            "id": self.id,
            "mode": self.mode,
            "offsets": [utt["source"].offsets for utt in self],
            "annotations": self._annotations,
            "clir_source_annotations": self._token_annotations,
        })

        
    def reset_annotation(self):
         self._annotations = {}
         self._token_annotations = {}
