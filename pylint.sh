#/usr/bin/env bash

echo "Executing linter"
output=$(python3 -m pylint --errors-only app/app.py --disable E0401)
status=0
if [ -n "$output" ]; then
    status=1
    echo "Linting failed"
else
    status=0
    echo "Linting success"
fi 
if [ $status -eq 1 ]; then
    exit $status
fi 
echo "Executing bandit"
output=$(python3 -m bandit -r app/. -lll -q)
if [ -n "$output" ]; then
    status=1
    echo "Bandit failed"
else
    echo "Bandit success"
    status=0
fi 
exit $status