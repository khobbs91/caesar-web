#!/bin/sh
export USE_TEST_DB=1
echo "please wait..."
echo "browse to http://localhost:8000 to see this routing"
(echo "from randomrouting import testscript" && cat) | python manage.py shell