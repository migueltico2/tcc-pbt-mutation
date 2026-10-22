#!/usr/bin/env python3
"""Imprime o resumo de um mutations.xml do PIT: contagens por status, mutantes gerados e mutation score."""
import collections
import sys
import xml.etree.ElementTree as ET

r = ET.parse(sys.argv[1]).getroot()
c = collections.Counter(m.get("status") for m in r.iter("mutation"))
det = c["KILLED"] + c["TIMED_OUT"]
val = det + c["SURVIVED"] + c["NO_COVERAGE"]
rotulo = sys.argv[2] if len(sys.argv) > 2 else ""
print(f"[{rotulo}]", dict(c), f"gerados={sum(c.values())}", f"mutation_score={100 * det / val:.2f}%")
