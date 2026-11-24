#!/usr/bin/env bash
# Update the public Orca demo on asterix from this working tree.
#
#   scripts/deploy_demo.sh           code and page (seconds); restarts the service only if Python or C code changed
#   scripts/deploy_demo.sh --data    also the grammar, the tagger model and the compiled ACE grammar (slow, rarely needed)
#
# The tagger copied by --data is the demo's (DEMO_TAGGER, default DeBERTa-v3 large); a tagger with another encoder
# also needs that encoder's files in ~/.cache/huggingface on asterix. The patched ACE (third_party/ace-orca/ace)
# is copied by hand after a rebuild.
#
# Needs `ssh asterix` to work (see ~/.ssh/config). Nothing here needs sudo.
set -euo pipefail
cd "$(dirname "$0")/.."
HOST=asterix
DEST=orca-demo
# The demo's tagger is set in the service unit on asterix (--tagger); it is not the parser's default.
TAGGER=${DEMO_TAGGER:-data/models/tagger-2025bothsurf-debertav3large}
NAME=${TAGGER##*/tagger-}; NAME=${NAME%-bert}
NOTE="analysis/mrs/dev-$NAME-rawtext.json"; [ -f "$NOTE" ] || NOTE=""

if [[ "${1:-}" == "--data" ]]; then
    rsync -aR --info=stats1 --exclude 'data/erg/2025/tsdb' --exclude 'data/erg/2025/openproof' --exclude 'data/erg/2025/.git' \
        data/erg/2025 data/ace/erg-2025.dat "$TAGGER/labels.json" "$TAGGER/model.pt" "$HOST:$DEST/" | tail -2
fi

# -i lists what changed; the page is read on every request, code needs a restart
CHANGED=$(rsync -aRi --exclude '__pycache__' --exclude '*.so' --exclude '*.pyc' --exclude 'HANDOFF.md' \
    orca scripts kelp/__init__.py kelp/docs.py docs/demo setup.py LICENSE $NOTE "$HOST:$DEST/" | grep -E '^[<>]f' || true)
if [[ -z "$CHANGED" && "${1:-}" != "--data" ]]; then echo "Nothing changed."; exit 0; fi
echo "$CHANGED" | sed 's/^[^ ]* /  updated: /'

RESTART=no
if echo "$CHANGED" | grep -qE '\.c$|setup\.py'; then
    ssh "$HOST" "cd $DEST && .venv/bin/python setup.py -q build_ext --inplace"; RESTART=yes
fi
# Python: restart only if the running server has loaded one of the changed files (it lists them at /api/loaded);
# a file it has not loaded yet is read fresh when first needed. No list (older server) means restart.
LOADED=$(ssh "$HOST" 'wget -qO- http://127.0.0.1:8017/api/loaded' 2>/dev/null | python3 -c 'import json, sys; print("\n".join(json.load(sys.stdin)))' 2>/dev/null || echo ALL)
for f in $(echo "$CHANGED" | awk '{print $2}' | grep -E '\.py$' || true); do
    if [[ "$LOADED" == ALL ]] || echo "$LOADED" | grep -qxF "$f"; then RESTART=yes; fi
done
if [[ "${1:-}" == "--data" ]]; then RESTART=yes; fi
if [[ $RESTART == yes ]]; then
    echo "Restarting the service (the models take about 40 s to load) ..."
    ssh "$HOST" 'export XDG_RUNTIME_DIR=/run/user/$(id -u); systemctl --user restart orca-demo
        for i in $(seq 40); do sleep 3; wget -qO- http://127.0.0.1:8017/api/info >/dev/null 2>&1 && break; done'
fi
ssh "$HOST" 'wget -qO- --header="Content-Type: application/json" --post-data="{\"sentence\": \"The dog barked.\"}" http://127.0.0.1:8017/api/parse' \
    | python3 -c 'import json, sys; r = json.load(sys.stdin); print("Demo answers:", r.get("outcome", r))'
