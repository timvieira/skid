#!/bin/bash

# Linux PDF,OCR: http://blog.konradvoelkel.de/2013/03/scan-to-pdfa/
# REQUIRES: tesseract ghostscript


function check {
  command -v $1 >/dev/null 2>&1 || { echo >&2 "Error: $1 required."; exit 1; }
}

check tesseract
check gs
check hocr2pdf

# requires one argument
[ "$#" -ne "1" ] && { echo "Specify a file."; exit 1; }

y="$1"
echo "Creating searchable PDF for $y"

x=`basename "$y"`
out="${x%.*}_searchable.pdf"
name="$y.ocr"

mkdir "$name"
cd "$name"

# splitting to individual pages
gs -dSAFER -dBATCH -dNOPAUSE -sDEVICE=jpeg -r300 -dTextAlphaBits=4 -o out_%04d.jpg -f "$y"

# process each page
for f in $( ls *.jpg ); do
  echo $f

  # extract text
  tesseract -l eng -psm 3 $f ${f%.*} hocr

  # remove the "<?xml" line, it disturbed hocr2pdf
  grep -v "<?xml" ${f%.*}.html > ${f%.*}.noxml
  #rm ${f%.*}.html

  # create a searchable page
  hocr2pdf -i $f -s -o ${f%.*}.pdf < ${f%.*}.noxml
  #rm ${f%.*}.noxml
  #rm $f
done

cd ..

# combine all pages back to a single file
# from http://www.ehow.com/how_6874571_merge-pdf-files-ghostscript.html
gs -dCompatibilityLevel=1.4 -dNOPAUSE -dQUIET -dBATCH -dNOPAUSE -q \
    -sDEVICE=pdfwrite \
    -sOutputFile=$out \
    $name/*.pdf

cd ..
#rm -rf $name
