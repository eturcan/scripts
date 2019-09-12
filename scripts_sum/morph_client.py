from subprocess import check_output
from pathlib import Path
import json

DEFAULT_PATH = Path(__file__).parent / "scripts-morph-v4.4.jar"

def get_morphology(string, port, lang, path=None):
    if path is None:
        path = DEFAULT_PATH
    raw_output = check_output(
            ["java", "-jar", path, str(port), lang.upper(), string])
    return json.loads(raw_output.decode("utf8"))
