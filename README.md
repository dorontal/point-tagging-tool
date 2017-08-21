# ptagtool.py

This is a tool designed for speedy tagging of images with points.
It was originally written for tagging face images. We needed the first
point to be on the face image's left eye, the second point to be on
the right eye and the third point on the mouth.  In order to let the
user know which point was first second or third, we used different
colors for the cross shown at each tagged (clicked) point - the first
point is red, the second green, the third cyan.

The program saves the points that are clicked on, for each image,
in a filename with the same name as the image filename, but with a
`.pts` extension.  The points in that file appear in the order
that they were clicked on.

This program uses keyboard shortcuts to make tagging of multiple
images quick.  Run the script with no arguments for usage
instructions.

## System requirements

* This script was tested with Python 2.7.12 on Linux 4.4.

* You will need to install some python libraries that are not always
included in a default python installation:
  * `python-imaging`
  * `python-pil`
  * `python-pil.imagetk`
  * `python-gtk2`

## Usage

Provide a directory that contains some image files as input, running
the script from the command line, e.g: 

    # ./ptagtool.py ~/Pictures
