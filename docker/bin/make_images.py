#!/usr/bin/env python

import os
import argparse
import pathlib
import json
import imgkit
from multiprocessing import Pool



# from summarkup/generate_images
def generate_images(inp):
    markup_dir, output_dir, css, markup_file = inp
    query_id, doc_id, component, _ = markup_file.split(".")

    with open(os.path.join(markup_dir,query_id, markup_file), "r") as markup_fp:
        data = json.load(markup_fp)
        
    markup = data["markup"]
    
    css_data = " <style>\n{}\n </style>".format(css)
    
    html = (
        '<html>\n'
        '  <head>\n'
        '{style}\n'
        '    <meta charset="UTF-8" />\n'
        '  </head>'
        '  <body>\n'
        '{summary}\n'
        '  </body>\n'
        '</html>'
    ).format(style=css_data, summary=markup)
    
    options = {
        'encoding': 'UTF-8', 
        'quiet': "", 
        'xvfb': "",
        'crop-h': 768,
        'crop-w':1024
    }
    imgkit.from_string(html, os.path.join(output_dir,query_id,"{}.png".format(markup_file[:-5])), options=options)
    #print(markup_file[:-5])

def main():
    parser = argparse.ArgumentParser("Generating images using markups.")
    parser.add_argument("--markup_dir",type=str, default="/outputs/markup")
    parser.add_argument("--output_dir",type=str, default="/outputs/images")
    parser.add_argument("--css_file", type=str, default="scripts/configs/summary_style.v2.css")
    parser.add_argument("--num_procs", type=int, default=16)

    args = parser.parse_args()
    
    css = pathlib.Path(args.css_file).read_text()
    
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
    
    files=[]
    
    for query_dir in os.listdir(args.markup_dir):
        if not os.path.exists(os.path.join(args.output_dir,query_dir)):
            os.makedirs(os.path.join(args.output_dir,query_dir))
        for file in os.listdir(os.path.join(args.markup_dir,query_dir)):
            files.append((args.markup_dir, args.output_dir, css, file))
    
    with Pool(args.num_procs) as pool:
        pool.map(generate_images, files)


if __name__ == "__main__":
    main()
