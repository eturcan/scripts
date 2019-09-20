import re


def detokenize(string):
    string = re.sub(r" `` ", ' "', string)
    string = re.sub(r" '' ", '" ', string)
    string = re.sub(r" ''", '" ', string)
    string = re.sub(r" ,", ',', string)
    string = re.sub(r" \.", '.', string)
    string = re.sub(r" n't", "n't", string)
    string = re.sub(r" 's", "'s", string)
    string = re.sub(r" % ", "% ", string)
    string = re.sub(r" \?", "?", string)
    string = re.sub(r" \!", "!", string)
    string = re.sub(r"-LRB- ", "(", string)
    string = re.sub(r" -RRB-", ")", string)
    string = re.sub(r"([A-Za-z]) :", r"\1:", string)
    return string


def make_match_header(query, stem=False):
    line = "{} match found: {}{}".format(
            "Close" if stem else "Exact",
            " ".join([x.stem if stem else x.word
                      for x in query.content.tokens]),
            " (check sense: {})".format(
                " ".join([x.word 
                          for x in query.semantic_constraint.tokens])) \
            if query.semantic_constraint else "")
    wc = len(line.split())
    if stem:
        return '<h1 class="close_header">{}</h1>\n'.format(line), wc
    else:
        return '<h1 class="exact_header">{}</h1>\n'.format(line), wc

def make_word_match_header(query, found_words):
    line = "Found query terms: {}{}".format(
        ", ".join(found_words),
        " (check sense: {})".format(
            " ".join([x.word for x in query.semantic_constraint.tokens])) \
            if query.semantic_constraint else "")
    wc = len(line.split())
    return '<h1 class="exact_header">{}</h1>\n'.format(line), wc

def make_relevant_header(query):
    qcontent = " ".join([x.word for x in query.content.tokens])
    if query.semantic_constraint:
        qsense = " (check sense: {})".format(
            " ".join([x.word for x in query.semantic_constraint.tokens]))
    else:
        qsense = ""
    line = "Most relevant snippets: {}{}".format(qcontent, qsense)
    wc = len(line.split())
    return '<h1 class="relevant_header">{}</h1>\n'.format(line), wc
