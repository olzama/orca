#!/bin/bash
# Build ACE 0.9.34 with the Orca patch (per-item lexical restriction, --per-item-disable) into
# third_party/ace-orca/ace. Reproducible on any x86-64 Linux with gcc, g++, make, curl, bzip2:
#   - downloads ACE 0.9.34, REPP 0.2.2 (both Woodley Packard, sweaglesw.org) and Boost 1.71.0,
#     and checks them against the SHA-256 sums below (or reuses copies in third_party/downloads);
#   - builds Boost.Regex (no ICU) and REPP as static libraries, so the binary needs no Boost or
#     REPP at run time (like the official ACE binary);
#   - builds ACE without [incr tsdb()] support by default (--tsdb-stdout output works without it);
#     pass --with-tsdb to link libitsdb/libpvm3 from /usr/local (kesha has them);
#   - compares the result with an official ACE binary on a few sentences if one is given
#     (ACE_REFERENCE=/path/to/ace, default kesha's copy) and the grammar image exists.
# Usage: tools/build_ace_orca.sh [--with-tsdb] [--jobs N]
set -euo pipefail
ORCA="$(cd "$(dirname "$0")/.." && pwd)"
DL="$ORCA/third_party/downloads"
B="$ORCA/third_party/ace-orca-build"
OUT="$ORCA/third_party/ace-orca"
PATCH="$ORCA/third_party/ace-0.9.34-orca/per-item-disable.patch"
JOBS=2; TSDB=0
while [ $# -gt 0 ]; do case "$1" in --with-tsdb) TSDB=1;; --jobs) JOBS="$2"; shift;; *) echo "unknown option $1"; exit 2;; esac; shift; done

fetch() {   # fetch NAME URL SHA256 DIR
  local f="$4/$1"
  mkdir -p "$4"
  if [ ! -f "$f" ]; then curl -fL --retry 3 -o "$f.part" "$2" && mv "$f.part" "$f"; fi
  echo "$3  $f" | sha256sum -c - >/dev/null || { echo "checksum mismatch: $f"; exit 1; }
}
fetch ace-0.9.34.tar.gz http://sweaglesw.org/linguistics/ace/download/ace-0.9.34.tar.gz \
  65ab649096e3e6432b379170836943c8838ef2086e9cf5df87ce696de54574ae "$DL/ace"
fetch repp-0.2.2.tar.gz http://sweaglesw.org/linguistics/repp-0.2.2.tar.gz \
  1b805ac7bc3a338f61e41f3cc651e9711e64f3ac86da606c262cee014055b721 "$DL/repp"
fetch boost_1_71_0.tar.bz2 https://archives.boost.io/release/1.71.0/source/boost_1_71_0.tar.bz2 \
  d73a8da01e8bf8c7eda40b4c84915071a8c8a0df4a6734537ddde4a8580524ee "$DL/boost-1.71.0"

rm -rf "$B"; mkdir -p "$B/local/lib" "$B/local/include"
cd "$B"

# Boost.Regex 1.71.0, static, without ICU
tar xjf "$DL/boost-1.71.0/boost_1_71_0.tar.bz2" boost_1_71_0/boost boost_1_71_0/libs/regex/src
BOOST="$B/boost_1_71_0"
mkdir -p boost-obj
for s in "$BOOST"/libs/regex/src/*.cpp; do
  g++ -O2 -fPIC -I "$BOOST" -DBOOST_REGEX_NO_LIB -c "$s" -o "boost-obj/$(basename "${s%.cpp}").o" &
  while [ "$(jobs -r | wc -l)" -ge "$JOBS" ]; do sleep 0.2; done
done; wait
ar rcs "$B/local/lib/libboost_regex.a" boost-obj/*.o

# REPP 0.2.2, static
tar xzf "$DL/repp/repp-0.2.2.tar.gz"
( cd repp-0.2.2 && CPPFLAGS="-I$BOOST" LDFLAGS="-L$B/local/lib" LIBS="-lstdc++" ./configure --prefix="$B/local" --disable-shared --enable-static >/dev/null \
  && make -j"$JOBS" >/dev/null && make install >/dev/null )

# ACE 0.9.34 + the Orca patch
tar xzf "$DL/ace/ace-0.9.34.tar.gz"
( cd ace-0.9.34 && patch -p1 < "$PATCH" >/dev/null )
cd ace-0.9.34
if [ "$TSDB" = 1 ]; then
  DCF="-isystem /usr/local/include -DTSDB"
  DLIBS="-L/usr/local/lib -Wl,-Bstatic -litsdb -lpvm3 -Wl,-Bdynamic -ltirpc"
else
  DCF=""; DLIBS=""
fi
# -fcommon: the code relies on common symbols (default before GCC 10);
# no _FORTIFY_SOURCE: Ubuntu's default hardening aborts on string handling the official build tolerates.
make -j"$JOBS" ace \
  CPU="-fcommon -U_FORTIFY_SOURCE -D_FORTIFY_SOURCE=0 -isystem $BOOST -isystem $B/local/include" \
  DELPHIN_CFLAGS="$DCF" DELPHIN_LIBS="$DLIBS" \
  REPP_LIBS="-L$B/local/lib -Wl,-Bstatic -lrepp -Wl,-Bdynamic" \
  BOOST_REGEX_LIBS="$B/local/lib/libboost_regex.a -lstdc++" > "$B/ace-build.log" 2>&1 \
  || { tail -20 "$B/ace-build.log"; exit 1; }
mkdir -p "$OUT"; cp ace "$OUT/ace"
echo "built $OUT/ace ($(./ace -V 2>&1 | head -1))"

# Smoke test: same output as an official ACE 0.9.34 binary, and the directive works
REF="${ACE_REFERENCE:-/home/olga/delphin/tools/ACE/ace-0.9.34/ace}"
DAT="$ORCA/data/ace/erg-2025.dat"
if [ -x "$REF" ] && [ -f "$DAT" ]; then
  S=$'The dog barked.\nI saw the man with the telescope.\nNevertheless more than half of the population of the Baltic states are able to hold a conversation in Russian.'
  a=$(printf '%s\n' "$S" | "$REF" -g "$DAT" -n 5 2>/dev/null | md5sum)
  b=$(printf '%s\n' "$S" | "$OUT/ace" -g "$DAT" -n 5 2>/dev/null | md5sum)
  [ "$a" = "$b" ] && echo "smoke test: same output as $REF" || { echo "smoke test FAILED: output differs from $REF"; exit 1; }
  c=$(printf '#DISABLE xyz\nThe dog barked.\n#DISABLE\n' | "$OUT/ace" -g "$DAT" -1 --per-item-disable 2>/dev/null | grep -c '^SENT:')
  [ "$c" = 1 ] && echo "smoke test: --per-item-disable directives work" || { echo "smoke test FAILED: directives"; exit 1; }
else
  echo "smoke test skipped (no reference ACE at $REF or no grammar image at $DAT)"
fi
