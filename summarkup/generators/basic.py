import numpy as np
import re


class Basic:

    def __call__(self, doc, budget=100):
         scores = np.array([x.sum() for x in doc.annotations['exact_match']])
         indices = np.argsort(scores)[::-1]
         
         summary_indices = []
         size = 0
         for idx in indices:
             utt = doc.utterances[idx]
             size += len(utt["translations"]["edi-nmt"].tokens)
             summary_indices.append(idx)
             if size >= budget:
                 break

         summary_indices.sort()
         markdown_lines = []
         for idx in summary_indices:
             utt = doc.utterances[idx]["translations"]["edi-nmt"]
             tok_str = ""
             for t, token in enumerate(utt.tokens):
                 level = doc.annotations["exact_match"][idx][t].sum() 
                 if level > 0:
                     tok_str += ' <span class="relevant exact">{}</span>'.format(token.word)
                 elif token.word == "puree" or token.word == "cherries":
                     tok_str += ' <span class="relevant">{}</span>'.format(token.word)
                 else:
                     tok_str += " " + token.word
             markdown_lines.append("<p>" + tok_str.strip() + "</p>")
         output = "\n".join(markdown_lines)
         output = re.sub(r" `` ", ' "', output)
         output = re.sub(r" '' ", '" ', output)
         output = re.sub(r" , ", ', ', output)
         output = re.sub(r" \.", '.', output)
         return output
