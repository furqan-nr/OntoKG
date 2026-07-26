#!/usr/bin/env python3
"""DEPRECATED. The earlier item-level analysis here pseudoreplicated the 8 nested ratings per
participant (p ~ 1e-22) and is superseded. This shim runs the canonical *participant-level* analysis
(expert_study/analyze_expert_study.py) so any invocation reproduces the Section 7.6 numbers."""
import os, sys, runpy
here = os.path.dirname(os.path.abspath(__file__)); parent = os.path.dirname(here)
os.chdir(parent); sys.argv = ["analyze_expert_study.py", "Form responses (17).xlsx"]
runpy.run_path("analyze_expert_study.py", run_name="__main__")
