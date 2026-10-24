"""Layer-file texts for the comment round-trip characterization (work-graph's convert.py)."""

# comments in every place the round-trip claims to handle: file header, before a section, before an item,
# trailing on an id line, before a key inside an item, trailing on a later key, and a '#' inside quotes (not a comment)
WITH_COMMENTS = """# header of the file
schema: workgraph/1
layer: repo
# the nodes
nodes:
  # first node
  - id: a   # trailing on the id line
    kind: file
    label: "A # inside quotes is not a comment"
  - id: b
    kind: file
    # note on b's label
    label: B
edges:
  # why a imports b
  - source: a
    relation: imports
    target: b   # trailing on target
"""

# the same document written with keys in a different order, so `dump_yaml` has to normalise it
UNORDERED = """schema: workgraph/1
layer: repo
nodes:
  - label: A
    kind: file
    id: a
  - kind: file
    id: b
edges:
  - target: b
    source: a
    relation: imports
extra_key: kept
"""

CASES = {"with_comments": WITH_COMMENTS, "unordered": UNORDERED}
