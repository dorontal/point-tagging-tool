#!/bin/bash

# Set up virtualenv w/Python3 & requirements.txt

if ! [ -x "$(command -v python3)" ]; then
    echo "Error: cannot find executable 'python3'. Install it first. Exiting..."
    exit 0
fi

if ! [ -x "$(command -v pip3)" ]; then
    echo "Error: cannot find executable 'pip3'. Install it first. Exiting..."
    exit 0
fi

MY_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )

# cd to project root directory
cd "$MY_DIR/.."

if [ ! -d "env" ]; then
    # NOTE: you'll need to do:
    # sudo apt install python3-venv, also need system python3 installed

    python3 -m venv env

    . env/bin/activate

    # wheel is required otherwise there's a dependency issue
    # (e.g. see stackoverflow.com/questions/34819221)
    pip3 install pillow

    # make a new one every time
    pip3 freeze > requirements.txt
fi
