#!/usr/bin/env python3
"""Small regression checks for the JWS revision; no production outputs written."""
import importlib.util
import re
from pathlib import Path
from unittest.mock import patch

from rdflib import Graph

ROOT = Path(__file__).resolve().parents[1]


def main():
    spec = importlib.util.spec_from_file_location("jws_inference", ROOT / "infer_and_explain.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with patch.object(module, "validate", return_value=(False, None, "injected failure")), \
         patch.object(Graph, "serialize", side_effect=AssertionError("serialized invalid final graph")):
        try:
            module.build("psx")
        except ValueError as exc:
            assert "injected failure" in str(exc)
        else:
            raise AssertionError("final validation gate did not reject invalid graph")

    path = ROOT.parent / "jws_submission" / "main.tex"
    text = path.read_text(encoding="utf-8")
    # Include modular result sources in the same reference/citation checks.
    for include in re.findall(r"\\input\{([^}]+)\}", text):
        included_path = (path.parent / include).resolve()
        assert included_path.is_relative_to(path.parent.resolve()), 'input outside manuscript project'
        included_text = included_path.read_text(encoding='utf-8')
        assert not re.search(r"\\input\{", included_text), 'nested input requires explicit checking'
        text = text.replace('\\input{' + include + '}', included_text)
    labels = re.findall(r"\\label\{([^}]+)\}", text)
    refs = re.findall(r"\\(?:ref\*?|hyperref)\{([^}]+)\}", text)
    citations = {key.strip() for group in re.findall(r"\\cite\{([^}]+)\}", text) for key in group.split(",")}
    bibliography = set(re.findall(r"\\bibitem\{([^}]+)\}", text))
    assert len(labels) == len(set(labels)), "duplicate labels"
    assert set(refs) <= set(labels), "undefined references"
    assert citations <= bibliography, "undefined citations"
    for image in re.findall(r"\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}", text):
        assert (path.parent / image).exists(), f"missing image {image}"
    assert "\\journal{Journal of Web Semantics}" in text
    assert "authors executed every experiment" not in text
    assert "sound and complete by construction" not in text
    print("PASS: final validation rejects before serialization; manuscript references, citations, images and targeted consistency checks")


if __name__ == "__main__":
    main()
