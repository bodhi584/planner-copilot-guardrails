#!/usr/bin/env bash
# Usage: bash run.sh <M1|M2|M3> <norm|over20>   -> runs headless in runs/<model>_<portfolio>/
set -e
cd "$(dirname "$0")"
declare -A CFG=([M1]=M1_weekly_backlog.cfg [M2]=M2_reference_for_M3.cfg [M3]=M3_weekly_backlog.cfg)
M=${1:-M3}; P=${2:-norm}; D=runs/${M}_${P}
mkdir -p "$D"; cp "model/${CFG[$M]}" "$D/m.cfg"; cp model/portf_*_clean.tsv "$D/"
sed -i "s/portf_[a-z0-9]*_clean\.tsv/portf_${P}_clean.tsv/" "$D/m.cfg"
J=$(pwd)/jaamsim
(cd "$D" && java -Djava.awt.headless=true -cp "$J/classes:$J/src/main/resources:$J/jar/jogl-all.jar:$J/jar/gluegen-rt.jar" com.jaamsim.ui.GUIFrame m.cfg -b -h)
echo "Done. Report: $D/m.rep  · Order results: $D/m-OrderResults.log"
