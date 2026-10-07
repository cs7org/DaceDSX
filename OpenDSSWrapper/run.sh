#!/bin/bash
# $1: scenario id
# $2: simulator id

echo "BIN HIER" > out.txt
SCENARIOID=$1
SIMID=$2

BASEDIR="../OpenDSSWrapper"

SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do
  DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"
  SOURCE="$(readlink "$SOURCE")"
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
done
DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"
echo "came from $PWD"
cd $BASEDIR
echo "now in $PWD"

BIN="./OpenDSSWrapper.py"

VENV_PY=".venv/bin/python3"
if [ ! -x "$VENV_PY" ]; then VENV_PY="python3"; fi

gnome-terminal -- bash -c "$VENV_PY $BIN $SCENARIOID $SIMID 2>&1 | tee logs/${SCENARIOID}_${SIMID}.runlog; exec bash"

if [ $? -eq 0 ]
then
  echo "Success: $PWD/run.sh finished" >> logs/${SCENARIOID}_$SIMID.runlog
  exit 0
else
  echo "Failure: ExitCode: $?" >> logs/${SCENARIOID}_$SIMID.runlog
  exit 1
fi

exit;
