# ptagtool.py

This is a tool designed for speedy tagging of images with points.  It
was originally written for tagging face images. We needed the first
point to be on the face image's left eye, the second point to be on
the right eye and the third point on the mouth.  In order to let the
user know which point was first second or third, we used different
colors for the cross shown at each tagged (clicked) point - the first
point is red, the second green, the third cyan.

The program saves the points that are clicked on, for each image, in a
filename with the same name as the image filename, but with a `.pts`
extension.  The points in that file appear in the order that they were
clicked on.

This program uses keyboard shortcuts to make tagging of multiple
images quick.  Run the script with no arguments for usage
instructions.

## Prerequisites & Installation

* This script was tested with Python 3.7.3

* First, install these system-wide python libraries:
```
    sudo apt-get install python3-pil.imagetk
    sudo apt-get install python3-tk
```
* Then cd to the project directory (assuming repository is cloned
  locally on your machine and type 
```
    ./scripts/set_up_virtualenv
```

* The above step activates the virtual environment for you, but if you
  are returning to this directory later and have not activated your virtual
  environment,  you will need to activate it via (after cd'ing to the 
  project's root folder) 
```
    . env/bin/activate
```

## Usage

Provide a directory that contains some image files as input, running
the script from the command line, e.g: 

```
    ./ptagtool.py ~/Pictures
```
