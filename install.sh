#!/bin/bash

test -d pyve || {
    python3 -m venv pyve || {
        echo -e "\n\nError installing the python3 virtual environment\n"
        echo -e "Either with\n    yum install python34-virtualenv.noarch"
        echo -e "or with \n    apt-get install python3-virtualenv"
        exit 2
    }
}

. pyve/bin/activate
pip install --upgrade pip

pip install -r devel-requirements.txt
#export PATH=`pwd`/pyve/bin:PATH
