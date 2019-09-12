import argparse
from pathlib import Path
import json
import re
import textwrap


def main():
    parser = argparse.ArgumentParser("Display markup summary")
    parser.add_argument("paths", type=Path, nargs="+", help="markup to display")
    args = parser.parse_args()

    for path in args.paths:
        print(path)
        data = json.loads(path.read_text())
        markup = data["markup"]
        from colorama import Fore, Back, Style 

        markup = re.sub("<h1>(.*?)</h1>", 
            Fore.MAGENTA + Style.BRIGHT + r'\1' + Style.RESET_ALL + "\n",
            markup) 
        markup = re.sub('<span class="relevant exact">(.*?)</span>', 
            Fore.GREEN + Style.BRIGHT + r'\1' + Style.RESET_ALL,
            markup)
        markup = re.sub('<span class="relevant">(.*?)</span>', 
            Fore.GREEN + r'\1' + Style.RESET_ALL,
            markup)

        print()
        print(re.sub(r"<p>(.*?)</p>", lambda x: textwrap.fill(x[1].strip(), initial_indent="  ", subsequent_indent="  ") + "\n", markup))
        print()

if __name__ == "__main__":
    main() 
