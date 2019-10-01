import re


def parse_query(query_string):
    if "," in query_string:
        c1, c2 = query_string.split(",")
        return parse_query(c1) + parse_query(c2)
    
    if "[syn" in query_string:
        sc_type = "syn"
    elif "[hyp" in query_string:
        sc_type = "hyp"
    elif "[evf" in query_string:
        sc_type = "evf"
    else:
        sc_type = None

    if sc_type is not None:
        sc_content = re.search(r'\[(?:syn|hyp|evf):(.*?)\]', query_string)\
            .groups()[0]
    else:       
        sc_content = None

    query_string = re.sub(r"\[.*?\]", "", query_string)
    if "+" in query_string:
        query_type = "conceptual"
        query_string = re.sub(r"\+", "", query_string)
    elif "EXAMPLE_OF" in query_string:
        query_type = "example_of"
        query_string = re.sub(r"EXAMPLE_OF\((.*?)\)", r"\1", query_string)
    else:
        query_type = "lexical"

    if '"' in query_string:
        multiword = True
        query_string = re.sub(r'"', r'', query_string)
    else:
        multiword = False

    if '<' in query_string:
        mc = re.search(r'<(.*?)>', query_string)\
            .groups()[0]
        query_string = re.sub(r'<|>', r'', query_string)
    else:
        mc = None

    result = [
        {
            "semantic_constraint_type": sc_type,
            "semantic_constraint": sc_content,
            "query_type": query_type,
            "query": query_string,
            "multiword": multiword,
            "morphological_constraint": mc,
        }
    ]

    return result
