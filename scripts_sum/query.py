import re
from .token import Token
from .utterance import Utterance
from .morph_client import get_morphology

class QueryComponent:

    @staticmethod
    def parse(query_string, query_id, component_num, num_components,
              morph_path, morph_port):
        query_content = re.sub(r"EXAMPLE_OF\((.*?)\)", r"\1", query_string) 
        query_content = re.sub(r'\[(hyp|evf|syn):(.*?)\]', r'', query_content)
        query_content = query_content.replace("<", "").replace(">", "") \
            .replace('"', '').replace("+","").strip()
        content_morph = get_morphology(query_content, morph_port,
                                       "EN", morph_path)
        query_content_tokens = Token.tokens_from_morphology(content_morph)
        query_content_utt = Utterance(query_content, query_content_tokens)
        qc = QueryComponent(query_string, query_id, component_num,
                            num_components, query_content_utt)
        if qc.semantic_constraint:
            sc = qc.semantic_constraint
            sc_morph = get_morphology(sc.text, morph_port, "EN", morph_path)
            sc_tokens = Token.tokens_from_morphology(sc_morph)
            sc_utt = Utterance(sc.text, sc_tokens)
            qc.semantic_constraint._utterance = sc_utt

        return qc

    def __init__(self, query_string, query_id, component_num, num_components,
                 query_content):
        self._query_string = query_string
        self._query_id = query_id
        self._component_num = component_num
        self._num_components = num_components
        self._semcons = SemanticConstraint.parse(query_string)
        self._morphcons = MorphologicalConstraint.parse(query_string,
                                                        query_content)
        self._conceptual = "+" in query_string
        self._phrasal = '"' in query_string
        self._query_content = query_content
        self._example_of = "EXAMPLE_OF" in query_string
        
    def embed(self, embed_model, content_words=True, constraint_words=False):

        embs = []
        if content_words:
            for token in self.content.tokens: 
                token = token.word.lower()
                if token in embed_model:
                    embs.append(embed_model[token])
        if constraint_words and self.semantic_constraint:
            for token in self.semantic_constraint.tokens:
                token = token.word.lower()
                if token in embed_model:
                    embs.append(embed_model[token])

        if len(embs) > 0:
            return sum(embs) / len(embs)
        else:
            raise Exception("No query embeddings.")

    @property
    def string(self):
        return self._query_string

    @property
    def id(self):
        return self._query_id

    @property
    def num(self):
        return self._component_num

    @property
    def num_components(self):
        return self._num_components

    @property
    def semantic_constraint(self):
        return self._semcons

    @property
    def morphological_constraint(self):
        return self._morphcons
    
    @property
    def conceptual(self):
        return self._conceptual

    @property
    def content(self):
        return self._query_content

    @property
    def phrasal(self):
        return self._phrasal

    @property
    def example_of(self):
        return self._example_of

    @property
    def classification(self):
        if self.morphological_constraint:
            return "morphological_lexical"

        if not self.phrasal and not self.conceptual:
            if not self.semantic_constraint:
                return "unconstrained_simple_lexical"
            else:
                return "constrained_simple_lexical"

        if self.phrasal and not self.conceptual:
            if not self.semantic_constraint:
                return "unconstrained_simple_phrase"
            else:
                return "constrained_simple_phrase"

        return "generic"
       


    def __str__(self):
        return "{} {}/{}: {}".format(self.id, self.num, self.num_components,
                                     self.string) 

    def __repr__(self):
        buf = [
             "QueryComponent {",
             "  No. {} / {}".format(self.num, self.num_components),
             "  String: {}".format(self.string),
             "  Content: {}".format(self.content.text),
             "  Semantic Constraint: {}".format(self.semantic_constraint),
             "  Morph. Constraint: {}".format(self.morphological_constraint),
             "  Is Conceptual: {}".format(self.conceptual),
             "  Is Phrasal: {}".format(self.phrasal),
             "  Classification: {}".format(self.classification),
             "}",
        ]
        return "\n".join(buf)

    def all_token_iter(self):
        for token in self.content.tokens:
            yield token
        if self.semantic_constraint:
            for token in self.semantic_constraint.tokens:
                yield token

class SemanticConstraint:

    @staticmethod
    def parse(string):

        m = re.search(r"\[(hyp|evf|syn):(.*?)\]", string)
        if not m:
            return None
        
        cons_type = m.groups()[0]
        cons_string = m.groups()[1]
        cons_tokens = Token.tokens_from_string(cons_string)
        utt = Utterance(cons_string, cons_tokens)
        return SemanticConstraint(cons_type, utt)

    def __init__(self, type, utterance):
        self._type = type
        self._utterance = utterance

    @property
    def type(self):
        return self._type

    @property
    def text(self):
        return self._utterance.text

    @property
    def utterance(self):
        return self._utterance

    @property
    def tokens(self):
        return self.utterance.tokens
   
    def __str__(self):
        return "[{}] {}".format(self.type, self.utterance.text)

class MorphologicalConstraint:

    @staticmethod
    def parse(string, content):
        
        m = re.search(r"<(.*?)>", string)
        if not m:
            return None
        
        cons_string = m.groups()[0]
        const_tokens = cons_string.split(" ")
        TOKS = []
        for const_token in const_tokens:
            
            for token in content.tokens:
                if token.word == const_token: 
                    TOKS.append(token)
                    break
        if any([t.pos == "VB" for t in TOKS]):
            const_morph = [t for t in TOKS if t.pos == "VB"][-1]
        else:
            const_morph = TOKS[0]
      
        return MorphologicalConstraint(const_morph)

    def __init__(self, morph):
        self._morph = morph
     
    @property
    def morph(self):
        return self._morph
   
    def __str__(self):
        return "[word={} pos={} tense={} number={}]".format(
            self.morph.word, self.morph.pos, self.morph.tense, 
            self.morph.number)
