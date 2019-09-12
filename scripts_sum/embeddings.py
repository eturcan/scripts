import numpy as np


class Embeddings:

    @staticmethod
    def from_path(path):
         with path.open("r") as fp:
             idx2tok = []
             vectors = []
             for line in fp:
                 items = line.split()
                 idx2tok.append(items[0])
                 vectors.append([float(x) for x in items[1:]])                 
             vectors = np.array(vectors)
         return Embeddings(idx2tok, vectors) 

    def __init__(self, idx2tok, embeddings):
        self._embeddings = embeddings
        self._idx2tok = idx2tok
        self._tok2idx = {tok: idx for idx, tok in enumerate(idx2tok)}
        self.null_emb = np.full((embeddings.shape[1],), 0.0)

    def __contains__(self, value):
        if isinstance(value, str):
            return value in self._tok2idx
        elif isinstance(value, int):
            return value in self._idx2tok
        else:
            raise Exception(
                "Bad value, expected int or str but got {}".format(
                    type(value)))

    def __getitem__(self, value):
        if isinstance(value, str):
            return self[self._tok2idx[value]]
        elif isinstance(value, int):
            return self._embeddings[value]
        else:
            raise Exception(
                "Bad value, expected int or str but got {}".format(
                    type(value)))

    def average_embedding(self, words):
        count = 0
        embs = []
        for word in words:
            if word in self:
                count += 1         
                embs.append(self[word])
        return np.mean(embs, axis=0, keepdims=True)

    def lookup_sequence(self, words):
        m = [self[w] if w in self else self.null_emb
             for w in words]
        if len(m) > 1:
            return np.stack(m)
        else:
            return m[0].reshape(1, -1)

    @property        
    def dims(self):
        return self._embeddings.shape[1]
