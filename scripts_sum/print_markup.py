import argparse
from colorama import Fore, Back, Style 
from pathlib import Path
import json
import re
import textwrap

def set_header_color(match):
    if match.groups()[0] == "exact_header":
        return Fore.GREEN + Style.BRIGHT + match.groups()[1] + Style.RESET_ALL + "\n"
    else:
        return Fore.YELLOW + Style.BRIGHT + match.groups()[1] + Style.RESET_ALL + "\n"

def main():
    parser = argparse.ArgumentParser("Display markup summary")
    parser.add_argument("paths", type=Path, nargs="+", help="markup to display")
    parser.add_argument("--instr", action="store_true")
    args = parser.parse_args()

    for path in args.paths:
        print(path)
        
        data = json.loads(path.read_text())
        print(data["query_string"])

        markup = data["markup"]

        markup = re.sub('<h1 class="(.*?)">(.*?)</h1>', set_header_color, markup)
           
        markup = re.sub('<span class="rel_exact_match">(.*?)</span>', 
            Fore.GREEN + Style.BRIGHT + r'\1' + Style.RESET_ALL,
            markup)
        markup = re.sub('<span class="rel_close_match">(.*?)</span>', 
            Fore.YELLOW + Style.BRIGHT + r'\1' + Style.RESET_ALL,
            markup)
        markup = re.sub('<span class="rel_exact">(.*?)</span>', 
            Fore.GREEN + r'\1' + Style.RESET_ALL,
            markup)
        markup = re.sub('<span class="rel_close">(.*?)</span>', 
            Fore.YELLOW + r'\1' + Style.RESET_ALL,
            markup)

        markup = re.sub('<span class="relevant">(.*?)</span>', 
            Fore.GREEN + r'\1' + Style.RESET_ALL,
            markup)

        print()
        print(re.sub(r"<p>(.*?)</p>", lambda x: textwrap.fill(x[1].strip(), initial_indent="  ", subsequent_indent="  ") + "\n", markup))
        print()
        if args.instr:

            instr = re.sub('<b><font .*?>(.*?)</font></b>', 
                Fore.GREEN + Style.BRIGHT + r'\1' + Style.RESET_ALL, 
                data["instructions"])
            print(instr)
            print()
            print()

if __name__ == "__main__":
    main() 
