#!/bin/bash

# $1: scenario id
# $2: simulator id

#get SUMODIR and cd into
BIN="./SumoWrapper"
SCENARIOID=$1
SIMID=$2
BASEDIR="../SumoWrapper"
LOGDIR=$BASEDIR/logs/${SCENARIOID}/${SIMID}
LOGFILE=${LOGDIR}/run.sh.log

mkdir -p $LOGDIR
chmod 777 $LOGDIR

SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do # resolve $SOURCE until the file is no longer a symlink
  DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"
  SOURCE="$(readlink "$SOURCE")"
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE" # if $SOURCE was a relative symlink, we need to resolve it relative to the path where the symlink file was located
done
DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"
echo "came from $PWD"
echo "LOGDIR $LOGDIR"
cd $BASEDIR
echo "now in $PWD"

   #gnome-terminal -- bash -c "gdb --args $BIN $SCENARIOID $SUMOID; sleep 100"
   declare -x LD_LIBRARY_PATH="../CppBaseWrapper/build"

   #$BIN $SCENARIOID $SIMID 2>&1 | tee $LOGFILE
    gnome-terminal --tab -e "bash -ic  \" printf '\e]2;$SIMID\a'; $BIN $SCENARIOID $SIMID 2>&1 | tee $LOGFILE; sleep 100000\""
    if [ $? -eq 0 ]
    then
      echo "Success: $PWD/run.sh finished" | tee -a $LOGFILE
      exit 0
    else
      echo "Failure: ExitCode: $?" | tee -a $LOGFILE
      exit 1
    fi

    exit;




#gnome-terminal --tab -- "$BIN $1 $2 $3 $4 $5 $6 &> $1.runlog"
#--tab -e "bash -ic  \"/home/guetlein/svn/guetlein/pieces/readTopic.sh $1.provision.vehicle.position\" "
#--tab -e "bash -ic  \"sleep 1; $(DIR)TranslationUnits/Debug/MesoMicroTranslator $2 MesoMicroTranslator; read -n1\""

#gnome-terminal --tab -e "bash -ic  \"SumoFederateWrapper/src//SumoWrapper $((B+A)) $3 $1 $2 $6 2>&1 | tee  \"${5}_exec_log.txt\"; read -n1\""
