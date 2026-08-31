#!/usr/bin/env bash
# Regenerate every artefact in this repo, from the repo root, in dependency order.
#
#     ./rebuild.sh          rebuild everything, then run the checks
#     ./rebuild.sh --check  rebuild, then fail if git is not clean
#
# The --check form is the useful one: nothing tracked here should differ from
# what its generator produces. If the tree comes back dirty, something committed
# has drifted from the code that makes it.
set -uo pipefail
cd "$(dirname "$0")"
fail=0

run() {  # run <dir> <script...>
  local dir=$1; shift
  printf '  %-26s %-30s ' "$dir" "$*"
  if ( cd "$dir" && python3 "$@" >/dev/null 2>&1 ); then echo ok
  else echo FAILED; fail=1; fi
}

echo "generators"
run acrylic-frame            make_plates.py
run acrylic-frame            bom.py
run acrylic-frame            make_plates.py          # BOM.csv rides in the zip
run acrylic-frame            adapter_lilygo.py
run acrylic-frame            render_all.py
run ka7-uno-can-board        ka7_mock.py
run lan9692-evb-case         lan9692_case.py
run lan9692-evb-case         lan9692_box.py
run lan9692-evb-case         lan9692_box.py --solid
run lilygo-t-eth-elite-case  fit_for_print.py
run tc397-appkit-case        tc397_appkit_case.py
run esp32-s31-coreboard-case esp32_s31_case.py
run .                        stack_preview.py
run viewer                   make_viewer.py          # last: embeds the models

echo
echo "checks"
printf '  %-58s ' "acrylic-frame/review.py"
( cd acrylic-frame && python3 review.py >/dev/null 2>&1 ) && echo ok || { echo FAILED; fail=1; }
printf '  %-58s ' "check_stls.py"
python3 check_stls.py >/dev/null 2>&1 && echo ok || { echo FAILED; fail=1; }
printf '  %-58s ' "relative links in every markdown file"
python3 - <<'PY' && echo ok || { echo FAILED; fail=1; }
import os, re, glob, sys
bad = 0
for md in glob.glob('*.md') + glob.glob('*/*.md'):
    for t in re.findall(r'\]\(([^)#][^)]*)\)', open(md).read()):
        t = t.split('#')[0]
        if not t or t.startswith(('http', 'mailto')):
            continue
        if not os.path.exists(os.path.normpath(
                os.path.join(os.path.dirname(md), t.split()[0]))):
            print(f'BROKEN {md} -> {t}')
            bad += 1
sys.exit(1 if bad else 0)
PY

if [ "${1:-}" = "--check" ]; then
  echo
  printf '  %-58s ' "git tree clean after a full rebuild"
  if [ -z "$(git status --porcelain)" ]; then echo ok
  else echo FAILED; git status --short | sed 's/^/      /'; fail=1; fi
fi

echo
[ $fail -eq 0 ] && echo "all good" || echo "something failed"
exit $fail
