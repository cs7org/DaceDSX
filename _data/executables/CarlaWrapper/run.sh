#!/bin/bash
# $1: scenario id
# $2: simulator id

SCENARIOID=$1
SIMID=$2

SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do # resolve $SOURCE until the file is no longer a symlink
  DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"
  SOURCE="$(readlink "$SOURCE")"
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE" # if $SOURCE was a relative symlink, we need to resolve it relative to the path where the symlink file was located
done
DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"
#echo "came from $PWD"
cd $DIR
echo "now in $PWD"

#BIN="/usr/lib/jvm/jre1.8.0_271/bin/java -jar target/matsimWrapper-jar-with-dependencies.jar"
BIN="../../../CarlaWrapper/CarlaWrapper.py"

python3 $BIN $SCENARIOID $SIMID 2>&1 | tee logs/${SCENARIOID}_$SIMID.runlog

if [ $? -eq 0 ]
then
  echo "Success: $PWD/run.sh finished" >> logs/${SCENARIOID}_$SIMID.runlog
  exit 0
else
  echo "Failure: ExitCode: $?" >> logs/${SCENARIOID}_$SIMID.runlog
  exit 1
fi

exit;