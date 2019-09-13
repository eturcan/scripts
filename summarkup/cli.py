import argparse
from pathlib import Path
import pickle
import json
import imgkit


def generate_markup():
    parser = argparse.ArgumentParser("Generate markup for annotated document.")
    parser.add_argument("markup_module", 
                        help="markup class that generates the actual markup")
    parser.add_argument("annotated_document", type=Path,
                        help="path to annotated doc pkl file")
    parser.add_argument("output_path", type=Path, help="path to write markup")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    module_str, class_str = args.markup_module.rsplit(".", 1)
    mod = __import__(module_str, fromlist=[class_str])
    cls = getattr(mod, class_str)
    markup_generator = cls()

    with args.annotated_document.open("rb") as fp:
        doc = pickle.load(fp)
    
    markup = markup_generator(doc)
    if not args.quiet:
        print(markup)
    output = json.dumps({
        "markup": markup,
        "document_id": doc.id,
        "query_string": doc.annotations["QUERY"].string,
        "query_id": doc.annotations["QUERY"].id,
        "component": doc.annotations["QUERY"].num,
        "total_components": doc.annotations["QUERY"].num_components,
    })
    args.output_path.parent.mkdir(exist_ok=True, parents=True)
    args.output_path.write_text(output)

def generate_image():
    parser = argparse.ArgumentParser("Generate image for annotated document.")
    parser.add_argument("css", type=Path, help="Path to summary css markup.")
    parser.add_argument("markup", type=Path, 
                        help="json file containing markup")
    parser.add_argument("img", type=Path, help="path to image file")
    args = parser.parse_args()

    data = json.loads(args.markup.read_text())
    markup = data["markup"]
    css_data = " <style>\n{}\n </style>".format(args.css.read_text())
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

    args.img.parent.mkdir(exist_ok=True, parents=True)
    options = {
        'encoding': 'UTF-8', 
        'crop-h': 300, 
        'quiet': "", 
        'xvfb': ""
    }
    imgkit.from_string(html, str(args.img), options=options)
