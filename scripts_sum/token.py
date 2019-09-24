from nltk import word_tokenize

def merge_ints(morph_tokens):
    new_tokens = [] 
    itr = enumerate(morph_tokens)

    for i, token in itr:
        if token.word == "<" and i + 2 < len(morph_tokens):
            if morph_tokens[i + 1].word in ["int", "num"] \
                    and morph_tokens[i + 2].word == ">":
                new_tokens.append(
                    Token('<' + morph_tokens[i + 1].word + '>', 
                          pos='OTHER', tense='NA', 
                          number='NA', stem='<int>', suffix='', prefix=''))
                next(itr)
                next(itr)
        else:
            new_tokens.append(token)
    return new_tokens

class Token:

    @staticmethod
    def tokens_from_string(string):
        return [Token(word) for word in word_tokenize(string)]

    @staticmethod
    def tokens_from_morphology(morph):
        tokens = []
        for M in morph:
            for m in M:
                token = Token(m["word"], prefix=m["prefixes"], stem=m["stem"],
                              suffix=m["suffixes"], pos=m["pos"], tense=m["tense"],
                              number=m["number"])
                tokens.append(token)
        return merge_ints(tokens)

    def __init__(self, word, prefix=None, stem=None, suffix=None, pos=None,
                 tense=None, number=None):
        self._word = word
        self._prefix = prefix
        self._stem = stem
        self._suffix = suffix
        self._pos = pos
        self._tense = tense
        self._number = number
        self._utterance = None
        self._offsets = None
          
    @property
    def word(self):
        return self._word

    @property
    def prefix(self):
        return self._prefix

    @property
    def stem(self):
        return self._stem

    @property
    def suffix(self):
        return self._suffix

    @property
    def pos(self):
        return self._pos

    @property
    def tense(self):
        return self._tense

    @property
    def number(self):
        return self._number

    def __str__(self):
        return self.word

    def set_utterance(self, utt):
        self._utterance = utt

    @property
    def utterance(self):
        return self._utterance

    @property
    def offsets(self):
        return self._offsets

    @offsets.setter
    def offsets(self, val):
        self._offsets = tuple(val)
