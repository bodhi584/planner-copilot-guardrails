#!/usr/bin/env bash
# Builds JaamSim from source (headless) next to this file. Needs Java 17+ (Colab: apt-get install -y openjdk-17-jdk-headless).
set -e
cd "$(dirname "$0")"
command -v javac >/dev/null || { echo "Installing Java..."; apt-get -qq update && apt-get -qq install -y openjdk-17-jdk-headless >/dev/null; }
JAAMSIM_COMMIT=efe404c48e938a372be1dca56ac552976776b28a   # build used for the reproduction (13 Oct 2026)
if [ ! -d jaamsim ]; then
  git clone -q https://github.com/jaamsim/jaamsim
  (cd jaamsim && git checkout -q "$JAAMSIM_COMMIT")
fi
cd jaamsim
if [ ! -d classes ]; then
  find src/main/java -name '*.java' > srcs.txt
  javac -nowarn -encoding UTF-8 -d classes -cp jar/jogl-all.jar:jar/gluegen-rt.jar @srcs.txt
fi
echo "JaamSim built. Next: python reproduce.py   (or: bash run.sh M3 norm)"
