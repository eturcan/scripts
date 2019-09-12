from .token import Token


class Utterance:

    def __init__(self, text, tokens, speaker=None, offsets=None):
        self._text = text
        self._tokens = tuple(tokens)
        self._speaker = speaker
        if offsets is not None:
            if isinstance(offsets, (list, tuple)) and len(offsets) == 2:
                self._offsets = tuple(offsets)
            else:
                raise ValueError("offsets must be an iterable of length 2.")
        else:
            self._offsets = None

        for t in self.tokens:
            t.set_utterance(self)         

    @property
    def tokens(self):
        return self._tokens

    @property
    def text(self):
        return self._text

    @property
    def speaker(self):
        return self._speaker

    @property
    def offsets(self):
        return self._offsets

    def __str__(self):
        import textwrap 
        token_string = " ".join([str(t) for t in self.tokens])
        buff = [
            "Utterance: {",
            textwrap.fill("   text:  {}".format(self.text), 
                          subsequent_indent="          "),
            textwrap.fill(" tokens: [{}]".format(token_string),
                          subsequent_indent="          "),
            "speaker: {}".format(self.speaker),
        ]
        if self.offsets:
            buff.append(" offset: ({}, {})".format(*self.offsets))
        buff.append("}")
        return "\n".join(buff) 
