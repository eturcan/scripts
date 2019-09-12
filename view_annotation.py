import argparse
import pickle
from pathlib import Path
import textwrap
import os


def main():

    parser = argparse.ArgumentParser("View an annotation on a document")
    parser.add_argument("annotation", type=Path, nargs="+", help="annotated .pkl file")
    parser.add_argument("trans", help="translation to view")
    parser.add_argument("annotator", help="name of annotator")
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--sent', nargs='+', default=None)
    group.add_argument('--word', default=None)
    parser.add_argument("--input", action="store_true")
    args = parser.parse_args()

    rows, columns = os.popen('stty size', 'r').read().split()
    columns = int(columns)

    for ann in args.annotation:
        with ann.open("rb") as fp:
            doc = pickle.load(fp)
        #doc = pickle.loads(args.annotation.read_bytes())
        annotation = doc.annotations[args.annotator]


        print(doc.mode, doc.id, annotation["meta"]["query"])
           

       
        if args.sent is not None:
            for i, utt in enumerate(doc):
                scores = [annotation["annotation"][i]["sentence"][x] 
                          for x in args.sent]
                score_string = "  ".join(["{:5.3f}".format(s) for s in scores]) 
                print(textwrap.fill(
                    score_string + "  " + utt["translations"][args.trans].text,
                    width=columns,
                    subsequent_indent=" " * (len(score_string) + 2)))
        else:
            for i, utt in enumerate(doc):
                tokens = utt["translations"][args.trans].tokens
                scores = annotation["annotation"][i]["word"][args.word] 
                buffers = [list() for s in scores[0]] + [list()]
                for s, t in zip(scores, tokens):
                    s = ["{:6f}".format(si) if si != 0 and si != float('-inf') else ' ' for si in s]
                    max_len = max([len(x) for x in s + [t.word]])
                    tmp = "{:" + str(max_len) + "s}"
                    for j in range(len(s)):
                        buffers[len(s) - j -1].append(tmp.format(s[j]))

                    buffers[-1].append(tmp.format(t.word))

                while buffers[-1]:

                    row_lines = ["" for x in scores[0]] 
                    line = ""
                    while buffers[-1]:
                        if len(line) + len(buffers[-1][0]) + 4 > columns:
                            break
                        for j, s in enumerate(buffers[:-1][::-1]):
                            row_lines[j] += " " + s.pop(0)
                        line += " " + buffers[-1].pop(0)
                    if not all([rl.strip() == '' for rl in row_lines]):  
                        for rl in row_lines[::-1]:
                            print(" " + rl)
                    print(" " + line)
                    print()
                       
                    
                 
                #for j, sj in s:
                #    buffers
                #score_string = "  ".join(["{:5.3f}".format(s) for s in scores]) 
                #print(textwrap.fill(
                #    score_string + "  " + utt["translations"][args.trans].text,
                #    width=columns,
                #    subsequent_indent=" " * (len(score_string) + 2)))

        print()
        if args.input:
            input()

if __name__ == "__main__":
    main()
