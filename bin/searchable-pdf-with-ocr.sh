#!/bin/sh

# Linux PDF,OCR: http://blog.konradvoelkel.de/2013/03/scan-to-pdfa/
# REQUIRES: tesseract ghostscript

y="`pwd`/$1"
echo Will create a searchable PDF for $y

x=`basename "$y"`
name=${x%.*}

mkdir "$name"
cd "$name"

# splitting to individual pages
gs -dSAFER -dBATCH -dNOPAUSE -sDEVICE=jpeg -r300 -dTextAlphaBits=4 -o out_%04d.jpg -f "$y"

# process each page
for f in $( ls *.jpg ); do
  # extract text
  tesseract -l eng -psm 3 $f ${f%.*} hocr

  # remove the "<?xml" line, it disturbed hocr2df
  grep -v "<?xml" ${f%.*}.html > ${f%.*}.noxml
  #rm ${f%.*}.html

  # create a searchable page
  hocr2pdf -i $f -s -o ${f%.*}.pdf < ${f%.*}.noxml
  #rm ${f%.*}.noxml
  #rm $f
done

# combine all pages back to a single file
# from http://www.ehow.com/how_6874571_merge-pdf-files-ghostscript.html
gs -dCompatibilityLevel=1.4 -dNOPAUSE -dQUIET -dBATCH -dNOPAUSE -q -sDEVICE=pdfwrite -sOutputFile=../${name}_searchable.pdf *.pdf

cd ..
#rm -rf $name
