#!/bin/bash

# bash tut: http://linuxconfig.org/bash-scripting-tutorial
# Linux PDF,OCR: http://blog.konradvoelkel.de/2013/03/scan-to-pdfa/

function check {
  command -v $1 >/dev/null 2>&1 || { echo >&2 "Error: $1 required."; exit 1; }
}

check tesseract
check gs

# requires one argument
[ "$#" -ne "1" ] && { echo "Specify a file."; exit 1; }

#y="`pwd`/$1"
y="$1"
echo "Extract text from PDF $y using optical character recognition"

x=`basename "$y"`
#name=${x%.*}
name="$y.ocr"

mkdir "$name"
cd "$name"

# splitting to individual pages
gs -dSAFER -dBATCH -dNOPAUSE -sDEVICE=jpeg -r300 -dTextAlphaBits=4 -o out_%04d.jpg -f "$y"

# process each page
for f in $( ls *.jpg ); do
  # extract text
  tesseract -l eng -psm 3 $f ${f%.*}.txt
  rm $f
done

cd ..
#rm -rf $name
