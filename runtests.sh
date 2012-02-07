#!/bin/bash

THIS_DIR=`dirname $0`
THIS_DIR=`cd $THIS_DIR && pwd`
INDIR=$THIS_DIR/tests/in
OUTDIR=$THIS_DIR/tests/out 
MASTERS=$THIS_DIR/tests/masters
mkdir -p $OUTDIR
rm -f $OUTDIR/*.pdf
FAILED=
TESTS=
export PYTHONPATH=$THIS_DIR:$THIS_DIR/tests/utils/


function usage()
{
    echo "runtests.sh [options] [tests]

if no tests are specified then all tests/*.py are run

options:
 --help                   this scren
 --generate-masters       generates master pdfs
 --verify-masters         verifies consistency of master pdfs
 --check-against-masters  compares generated pdfs with master pdfs
"
    exit 2
}

function verify_masters()
{
    RETURN_VALUE=0
    for pdf in $MASTERS/*.pdf; do
        echo "verifying: `basename $pdf`" > /proc/self/fd/2
        # workaround pdftk bug: http://bugs.debian.org/cgi-bin/bugreport.cgi?bug=454140
        #if [[ ! "$pdf" =~ ^.*setownerpassword\.pdf$ ]]; then
        pdftk $pdf dump_data output - owner_pw ownerpwd  > /dev/null || { echo "FAILED[pdftk]: $pdf"; RETURN_VALUE=1; }
        #fi
            
        #if [[ ! "$pdf" =~ ^.*password\.pdf$ ]]; then
            gs '-ZD/' -dBATCH -dNODISPLAY $pdf > /dev/null || { echo "FAILED[gs]: $pdf"; RETURN_VALUE=1; }
        #fi
    done
    echo $RETURN_VALUE
}


while true; do
    case "$1" in
        -h|--help)
            usage
            ;;
        --generate-masters)
            OUTDIR=$MASTERS
            shift
            ;;
        --verify-masters)
            exit `verify_masters`
            ;;
        --check-against-masters)
            CHECK_AGAINST_MASTERS=1
            shift
            ;;
        "")
            break
            ;;
        *)
            if [ ${1:0:1} == "-" ]; then
                echo "unknown argument $1"
                exit 1
            else
                TESTS="$TESTS $1"
                shift
            fi
            ;;
    esac
done




if [ -z "$TESTS" ]; then
    TESTS="tests/*.py"
fi

echo -- running as $API_USERNAME:$API_TOKEN@$API_HOSTNAME, output to $OUTDIR

for test in $TESTS; do
    echo $test
    python $test $INDIR $OUTDIR || FAILED="$FAILED $test(err:$?)"
    if [ -n "$CHECK_AGAINST_MASTERS" ]; then
        fname=`basename $test`
        stem=${fname%.*}
        for pdf in $OUTDIR/$stem*.pdf; do
            echo " checking: `basename $pdf`"
            master="$MASTERS/`basename $pdf`"
            python tests/utils/compare_pdf.py $pdf $master || FAILED="$FAILED $test(verification)"
        done
    fi
done

if [ -n "$FAILED" ]; then
    echo "-----------------------------------------------------------------"
    echo "                     FAILED tests"
    echo "-----------------------------------------------------------------"
    for f in $FAILED; do
        echo $f
    done
    exit 1
fi
