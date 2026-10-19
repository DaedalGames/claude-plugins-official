#!/usr/bin/env python3
"""Print, per runner image, how each tested tree's suite differs from main's."""
import os
import sys
import xml.etree.ElementTree as ET


def read_suite(folder):
    path = os.path.join(folder, "junit.xml")
    if not os.path.exists(path):
        return None
    outcomes = {}
    for case in ET.parse(path).getroot().iter("testcase"):
        name = "%s::%s" % (case.get("classname", ""), case.get("name", ""))
        if case.find("failure") is not None or case.find("error") is not None:
            outcomes[name] = "failed"
        elif case.find("skipped") is not None:
            outcomes[name] = "skipped"
        else:
            outcomes[name] = "passed"
    return outcomes


def read_text(folder, name):
    try:
        with open(os.path.join(folder, name)) as handle:
            return handle.read().strip()
    except OSError:
        return "?"


def main(root):
    trees = {}
    for entry in sorted(os.listdir(root)):
        if not entry.startswith("results-"):
            continue
        image, _, ref = entry[len("results-"):].rpartition("-")
        trees.setdefault(image, {})[ref] = os.path.join(root, entry)
    for image, refs in trees.items():
        base = read_suite(refs["main"]) if "main" in refs else None
        print("\n## %s\n" % image)
        print("| Tree | Commit | Passed | Failed | Skipped | Launch exit | Fails here, not on main |")
        print("|---|---|---|---|---|---|---|")
        details = []
        for ref in sorted(refs, key=lambda r: (r != "main", r)):
            suite = read_suite(refs[ref])
            sha = read_text(refs[ref], "sha")[:8]
            launch = read_text(refs[ref], "launch.exit")
            if suite is None:
                print("| %s | %s | no result | | | %s | |" % (ref, sha, launch))
                continue
            failed = sorted(n for n, o in suite.items() if o == "failed")
            counts = [sum(1 for o in suite.values() if o == kind) for kind in ("passed", "failed", "skipped")]
            if ref == "main" or base is None:
                added = []
                cell = "baseline" if ref == "main" else "no baseline"
            else:
                added = [n for n in failed if base.get(n) != "failed"]
                cell = str(len(added))
            print("| %s | %s | %d | %d | %d | %s | %s |" % (ref, sha, counts[0], counts[1], counts[2], launch, cell))
            if ref == "main":
                details.append(("main (baseline failures)", failed))
            elif added:
                marked = ["%s%s" % (n, "" if n in base else " (new test)") for n in added]
                details.append((ref, marked))
        for title, names in details:
            print("\n**%s**\n" % title)
            for name in names:
                print("- `%s`" % name)


if __name__ == "__main__":
    main(sys.argv[1])
