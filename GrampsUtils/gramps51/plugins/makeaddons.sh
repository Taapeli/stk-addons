#!/bin/bash
rm -r languages
rm -r ../addons
mkdir -p ../addons/gramps51/download
for dir in *
do
    if [ -d "$dir" ] 
    then
        tar -czf "../addons/gramps51/download/$dir.addon.tgz" "$dir"
    fi
done

mkdir -p ../addons/gramps51/listings
export GRAMPSPATH=/home/kari/Downloads/gramps-maintenance-gramps51

mkdir -p languages/po
touch  languages/po/en-local.po
touch  languages/po/fi-local.po
touch  languages/po/sv-local.po

for dir in *
do
    python3 ../../make.py gramps51 listing "$dir"
done

rm -r ../download
rm -r ../listings

mv ../addons/gramps51/download ..
mv ../addons/gramps51/listings ..
rm -r ../addons
rm -r languages

