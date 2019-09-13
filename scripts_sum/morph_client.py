from subprocess import check_output
from pathlib import Path
import json
import os


def get_morphology(string, port, lang, path=None):
    if path is None:
        path = os.getenv("SCRIPTS_MORPH", None)
        if path is None:
            raise RuntimeError("path is None and SCRIPTS_MORPH not set.")

    raw_output = check_output(
            ["java", "-jar", path, str(port), lang.upper(), string])
    return json.loads(raw_output.decode("utf8"))
