import numpy as np
import re
import string

punc = set(string.punctuation)
translations = ["edi-nmt", "umd-nmt", "umd-smt"]

class LexicalV1:

    def __call__(self, doc, budget=100):
        query = doc.annotations["QUERY"]
        #query = list(doc.annotations.values())[0]["meta"]["query"]

        exact_matches = []

        for i, utt in enumerate(doc):
            ann = {
                k: doc.annotations[k]["annotation"][i]
                for k in doc.annotations.keys() 
                if k != "QUERY"
            }
            
            best_trans = self.find_best_translation(ann)
            score = doc.annotations[best_trans + ".exact_match"]["annotation"][i]["sentence"]["sum"]
            if score > 0:
                exact_matches.append((i, score, best_trans))
            #best_trans = self.find_best_translation(
        #        {k: v["annotation"][i] for k, v in doc.annotations.items()})


        if len(exact_matches) > 0:
            markup = "<h1>Exact match found: {}</h1>\n".format(query.string)
            
            for i, score, best_trans in exact_matches:
                utt = doc.utterances[i]["translations"][best_trans]
                token_scores = np.array(doc.annotations[best_trans + ".exact_match"]["annotation"][i]["word"]["matches"]).ravel()
                line = ""
                for t, token in enumerate(utt.tokens): 
                    if token_scores[t] > 0:
                        line += ' <span class="relevant exact">{}</span>'.format(token.word)
                    else:
                        line += " " + token.word
                        
                markup += "<p>" + line.strip() + "</p>\n"
                #markup += "<p>" + " ".join([t.word for t in utt.tokens]) + "</p>\n"
        markup = re.sub(r" `` ", ' "', markup)
        markup = re.sub(r" '' ", '" ', markup)
        markup = re.sub(r" ''", '" ', markup)
        markup = re.sub(r" ,", ',', markup)
        markup = re.sub(r" \.", '.', markup)
        markup = re.sub(r" n't", "n't", markup)
        markup = re.sub(r" 's", "'s", markup)
        markup = re.sub(r" % ", "% ", markup)
        markup = re.sub(r" \?", "?", markup)
        markup = re.sub(r" \!", "!", markup)
        markup = re.sub(r"-LRB- ", "(", markup)
        markup = re.sub(r" -RRB-", ")", markup)

        markup = markup.strip()


        return markup


    def find_best_translation(self, annotations):
        scores = {}
        for trans in translations:
            exact_matches = annotations[trans + ".exact_match"]["sentence"]["sum"] 
#            soft_matches = annotations[trans + ".glove42Bsim.content_semcons"]["sentence"]["max"]
            scores[trans] = exact_matches 
        return sorted(scores, key=lambda x: scores[x], reverse=True)[0]

