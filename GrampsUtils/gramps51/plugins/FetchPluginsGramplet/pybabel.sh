# bug workaround; https://github.com/pypa/setuptools/issues/523
pip install setuptools==34.00

mkdir locale || echo "locale directory ok"
pybabel extract -F babel.cfg -k _l -o messages.pot .
if ! test -e locale/fi
then
   pybabel init --domain addon -i messages.pot -d locale -l fi
fi
if ! test -e locale/en 
then
   pybabel init --domain addon -i messages.pot -d locale -l en
fi
if ! test -e locale/sv
then
   pybabel init --domain addon -i messages.pot -d locale -l sv
fi
pybabel update --domain addon -i messages.pot --ignore-obsolete -d locale
