#!/usr/bin/env python

# ptagtool.py - an image point tagging tool.  Saves tagged point coordinates
#               into text files with extension '.pts' and filename the same
#               as the image filename

# File: ptagtool.py
# Author: Doron Tal

import sys
import os, os.path
import PIL.Image
from Tkinter import *
from ImageTk import PhotoImage
from tkFont import Font
from math import sqrt

class Application(Frame):
    # this class inherits from Tkinter.parent
    def __init__(self, strPath, master=None):
        """Constructor"""
        # call parent class constructor
        Frame.__init__(self, master)

        self.strPath = strPath
        self.lImgFilenames = FindImgFiles(strPath)

        # necessary to make the application actually appear on the screen
        self.grid(sticky=N+S+E+W)

        # PIL image, for loading from file and for resizing
        self.imgPIL = None

        # Tk photoimage, for display
        self.imgTk = None

        # list of coords (2-element lists) of current selection's pts
        self.lPtsOrig = []

        # lPtsCanvas is 'lPtsOrig', in canvas coordinates
        self.lPtsCanvas = []

        # x- and y-coords of displayed image in canvas coordinate frame
        self.xOffsetImg = -1
        self.yOffsetImg = -1

        # font in listbox text
        self.lbFont = Font(family='Helvetica', size=10, weight='normal')

        # crosshair line size , as fraction of
        # min(displayed-imagewidth, displayed-image-height)
        self.CrossSizeFrac = 0.05

        # color for drawing first crosshair - the origin
        self.CrossColor1 = 'red'

        # color for drawing second crosshair - (together with the first
        # crosshair, these two points define a coordinate frame) -
        self.CrossColor2 = 'green'

        # color for drawing third and on crosshairs - all points other
        # than the first and second, have this color
        self.CrossColor3 = 'cyan'

        # the width, in pixels, of crosshairs
        self.CrossLineWidth = 2

        # length of crosshair (updated upon display)
        self.CrossHalfLength = -1

        # the scale of currently displayed image (updated upon display)
        self.scaleImg = 1.0

        # True if any of the .pts file points have been changed
        # for the currently selected image, False otherwise
        self.bChangedAny = False

        # create all widges and set their initial conditions
        self.createWidgets()

    def createWidgets(self):
        """Set up all application graphics"""
        # get the top level winddow
        top = self.winfo_toplevel()

        # set the title of the top level window
        top.title('Image Point Tagging Tool')

        # make row 0 of the top level window's grid stretchable
        top.rowconfigure(0, weight=1)

        # make column 0 of the top level window's grid stretchable
        top.columnconfigure(0, weight=1)

        # bind keys for entire app
        top.bind_all('<Up>', self.selectPrev)
        top.bind_all('<Down>', self.selectNext)

        # make row 0 of Application's widget's grid stretchable
        self.rowconfigure(0, weight=1)

        # make column 0 of Application's widget's grid stretchable
        self.columnconfigure(0, weight=1)

        self.canvas = Canvas(self, bg='gray')
        self.canvas.grid(row=0, column=0, rowspan=2, sticky=N+S+E+W)
        self.canvas.rowconfigure(0, weight=1)
        self.canvas.columnconfigure(0, weight=1)

        # bind resize events (need -4 here bec. event gives 4+(real_size))
        self.canvas.bind('<Configure>', lambda e, s=self:
                         s.canvasResizeCB(e.width-2, e.height-2))

        # bind canvas mouse clicks
        self.canvas.bind('<Button-1>', self.canvasButton1ClickCB)
        self.canvas.bind('<Button-3>', self.canvasButton3ClickCB)

        # create scrollbars
        self.sbHorizontal = Scrollbar(self, orient=HORIZONTAL, width=10)
        self.sbVertical = Scrollbar(self, orient=VERTICAL, width=10)

        self.sbHorizontal.grid(row=1, column=1, columnspan=2, sticky=E+W)
        self.sbVertical.grid(row=0, column=3, sticky=N+S)

        # create lb for showing labeled/not-labeled images
        self.lbPts = Listbox(self, width=1, takefocus=0, exportselection=0,
                             font=self.lbFont)

        self.lbPts.grid(row=0, column=1, sticky=N+S+E+W)

        # create lb for showing image filenames
        self.lbImgs = Listbox(self, width=30, selectmode=SINGLE,
                              xscrollcommand=self.sbHorizontal.set,
                              yscrollcommand=self.sbVertical.set,
                              exportselection=0, font=self.lbFont)
        self.lbImgs.grid(row=0, column=2, sticky=N+S+E+W)

        # bind scrollbar movement
        self.sbHorizontal['command'] = self.lbImgs.xview
        self.sbVertical['command'] = self.sbVerticalViewCB

        # bind left mouse click selection
        self.lbImgs.bind('<Button-1>', lambda e, s=self:
                         s.select(self.lbImgs.nearest(e.y)))
        self.lbPts.bind('<Button-1>', lambda e, s=self:
                        s.select(self.lbImgs.nearest(e.y)))

        # bind wheel scroll
        self.lbImgs.bind('<Button-4>', lambda e, s=self:
                         s.wheelCB(self.lbPts, 4))
        self.lbImgs.bind('<Button-5>', lambda e, s=self:
                         s.wheelCB(self.lbPts, 5))
        self.lbPts.bind('<Button-4>', lambda e, s=self:
                        s.wheelCB(self.lbImgs, 4))
        self.lbPts.bind('<Button-5>', lambda e, s=self:
                        s.wheelCB(self.lbImgs, 5))

        # nSkip is # of chars to skip in path string so that only the
        # part of the path that was not supplied is displayed
        nSkip = len(self.strPath)
        if self.strPath[nSkip-1] != '/': nSkip += 1

        # insert image filenames plus marks into lists and
        # select first image that does not have pts file
        i = 0
        iFirstImgWithoutPtsFile = -1
        for strImgFilename in self.lImgFilenames:
            self.lbImgs.insert(END, strImgFilename[nSkip:])
            if self.bHasPtsFile(i):
                self.lbPts.insert(END, '+')
            else:
                self.lbPts.insert(END, '')
                if iFirstImgWithoutPtsFile < 0:
                    iFirstImgWithoutPtsFile = i
            i += 1

        if iFirstImgWithoutPtsFile < 0:
            self.select(0)
        else:
            self.select(iFirstImgWithoutPtsFile)

    def sbVerticalViewCB(self, *args):
        """Vertical scrollbar motion callback"""
        apply(self.lbImgs.yview, args)
        apply(self.lbPts.yview, args)

    def wheelCB(self, lb, iButton, nUnits=5):
        """Mouse wheel move callback"""
        self.sbVertical.set
        if iButton == 5:
            lb.yview(SCROLL, nUnits, UNITS)
        if iButton == 4:
            lb.yview(SCROLL, -nUnits, UNITS)

    def canvasButton1ClickCB(self, event):
        """Button 1 click callback: adds a crosshair at click location"""
        if self.bCanvasCoordsInImg(event.x, event.y):
            pt = [(event.x-self.xOffsetImg)/self.scaleImg,
                  (event.y-self.yOffsetImg)/self.scaleImg]
            ptScaled = [float(event.x), float(event.y)]
            self.lPtsOrig.append(pt)
            self.lPtsCanvas.append(ptScaled)
            if len(self.lPtsOrig) == 1: self.MarkAsLabeled()
            self.canvasResizeCB(self.canvas['width'], self.canvas['height'])
            self.bChangedAny = True

    def canvasButton3ClickCB(self, event):
        """Button 3 click callback: deletes landmark near click location"""
        if not self.bCanvasCoordsInImg(event.x, event.y): return
        i = self.FindNearestPtWithinCrosshairs(event.x, event.y)
        if i >= 0:
            del(self.lPtsOrig[i])
            del(self.lPtsCanvas[i])
            if len(self.lPtsOrig) == 0: self.MarkAsUnlabeled()
            self.canvasResizeCB(self.canvas['width'], self.canvas['height'])
            self.bChangedAny = True

    def select(self, i):
        """Select the i'th image to work with - make current selection = i"""
        # uncomment the following line if you are only dealing with
        # faces that have three points labeled on them and you want to
        # automatically reorder a previously tagged database so that
        # the person's right eye is the first point, left eye is
        # second point and mouth is third point
        self.ReorderPoints()
        if self.bChangedAny: self.savePts()
        self.lbImgs.selection_clear(0, END)
        self.lbPts.selection_clear(0, END)
        self.lbImgs.selection_set(i)
        self.lbPts.selection_set(i)
        self.lbImgs.see(i)
        self.lbPts.see(i)
        self.imgPIL = PIL.Image.open(self.strImgFilename())
        self.lPtsOrig = self.readPtsFile()
        self.canvasResizeCB(self.canvas['width'], self.canvas['height'])

    def selectPrev(self, *args):
        """Select entry that comes before current selection"""
        i = self.iSelection()
        if i > 0: self.select(i-1)

    def selectNext(self, *args):
        """Select entry that comes after current selection"""
        i = self.iSelection()
        if i < len(self.lImgFilenames)-1: self.select(i+1)

    def canvasResizeCB(self, width, height):
        """Called when canvas is resized"""
        if width <= 0 or height <= 0: return
        # maximize image width or height depending on aspect ratios
        widthImg = self.imgPIL.size[0]
        heightImg = self.imgPIL.size[1]
        arImg = float(widthImg)/float(heightImg)

        self.canvas['width'] = width
        self.canvas['height'] = height
        widthCanvas = int(self.canvas['width'])
        heightCanvas = int(self.canvas['height'])
        arCanvas = float(widthCanvas)/float(heightCanvas)

        if arImg < arCanvas:
            widthImgNew = int(arImg*float(heightCanvas))
            heightImgNew = heightCanvas
        else:
            widthImgNew = widthCanvas
            heightImgNew = int(float(widthCanvas)/arImg)

        self.imgTk = PhotoImage(self.imgPIL.resize((widthImgNew, heightImgNew),
                                                   PIL.Image.BILINEAR))

        self.xOffsetImg = 0.5*(float(widthCanvas)-float(widthImgNew))
        self.yOffsetImg = 0.5*(float(heightCanvas)-float(heightImgNew))

        self.CrossHalfLength = 0.5*self.CrossSizeFrac*float(min(widthImgNew,
                                                                heightImgNew))

        self.canvas.delete('image')
        self.canvas.create_image(self.xOffsetImg, self.yOffsetImg, anchor=NW,
                                 image=self.imgTk, tags='image')

        scaleWidth = float(widthImgNew)/float(widthImg)
        scaleHeight = float(heightImgNew)/float(heightImg)
        self.scaleImg = 0.5*(scaleWidth+scaleHeight)
        self.lPtsCanvas = map(lambda(x): [x[0]*self.scaleImg+self.xOffsetImg,
                                          x[1]*self.scaleImg+self.yOffsetImg],
                              self.lPtsOrig)
        self.drawPts()

    def drawPts(self):
        """Draw a cross at each point in current entry's .pts file"""
        self.canvas.delete('line')

        # draw first crosshair
        if len(self.lPtsCanvas) > 0:
            firstPt = self.lPtsCanvas[0]
            self.drawCross(firstPt[0], firstPt[1], self.CrossColor1),

        # draw second crosshair
        if len(self.lPtsCanvas) > 1:
            secondPt = self.lPtsCanvas[1]
            self.drawCross(secondPt[0], secondPt[1], self.CrossColor2)

        # draw third crosshair
        if len(self.lPtsCanvas) > 2:
            map(lambda(Pt): self.drawCross(Pt[0], Pt[1], self.CrossColor3),
                self.lPtsCanvas[2:])

    def drawCross(self, x, y, fillColor):
        """Draw a cross at location (x, y) in the currently selected image"""
        xStart = x-self.CrossHalfLength
        yStart = y-self.CrossHalfLength

        xEnd = x+self.CrossHalfLength
        yEnd = y+self.CrossHalfLength

        minX = self.xOffsetImg
        minY = self.yOffsetImg

        maxX = self.xOffsetImg+self.imgTk.width()-1
        maxY = self.yOffsetImg+self.imgTk.height()-1

        if xStart < minX: xStart = minX
        if yStart < minY: yStart = minY

        if xEnd > maxX: xEnd = maxX
        if yEnd > maxY: yEnd = maxY

        self.canvas.create_line(x, yStart, x, yEnd, fill=fillColor,
                                width=self.CrossLineWidth, tags='line')
        self.canvas.create_line(xStart, y, xEnd, y, fill=fillColor,
                                width=self.CrossLineWidth, tags='line')

    def iSelection(self):
        """Returns index of current selection"""
        return(int(self.lbImgs.curselection()[0]))

    def bCanvasCoordsInImg(self, x, y):
        """Returns whether canvas coord (x, y) is inside the displayed image"""
        return(x >= self.xOffsetImg and
               y >= self.yOffsetImg and
               x < self.xOffsetImg+self.imgTk.width() and
               y < self.yOffsetImg+self.imgTk.height())

    def FindNearestPtWithinCrosshairs(self, x, y):
        """Returns index of landmark within crosshair length of (x,y), or -1"""
        i = 0
        imin = -1
        minDist = self.imgTk.width()+self.imgTk.height()
        for pair in self.lPtsCanvas:
            xdist = x-pair[0]
            ydist = y-pair[1]
            dist = sqrt(xdist*xdist+ydist*ydist)
            if dist <= self.CrossHalfLength and dist < minDist:
                imin = i
            i += 1
        return(imin)

    def savePts(self):
        """Save pts file for selection self.iSelection()"""
        # remove whatever was there before
        if self.bHasPtsFile():
            os.remove(self.strPtsFilename())
        # save current result
        if len(self.lPtsOrig) > 0:
            hFile = open(self.strPtsFilename(), 'w')
            for pair in self.lPtsOrig:
                strToWrite = str(pair[0])+', '+str(pair[1])+'\n'
                hFile.write(strToWrite)
            hFile.close()

    def ReorderPoints(self):
        """
        Reorder points, assuming face labeling, so that the first point
        is always the person's right eye, the second point is the person's
        left eye and the third point is the mouth.  NB: this function only
        (destructively) works on self.lPtsOrig
        """
        if len(self.lPtsOrig) != 3: return
        # step 1 sort the points according to y-value
        self.lPtsOrig.sort(lambda ptA, ptB: cmp(ptA[1], ptB[1]))
        # step 2: from the top-most two points, call the leftmost one
        # the person's right eye and call the other the person's left eye
        if self.lPtsOrig[0][0] > self.lPtsOrig[1][0]:
            # swap first and second points' x-coordinate
            tmp = self.lPtsOrig[0][0]
            self.lPtsOrig[0][0] = self.lPtsOrig[1][0]
            self.lPtsOrig[1][0] = tmp
            # swap first and second points' y-coordinate
            tmp = self.lPtsOrig[0][1]
            self.lPtsOrig[0][1] = self.lPtsOrig[1][1]
            self.lPtsOrig[1][1] = tmp
            self.bChangedAny = True

    def bHasPtsFile(self, i=None):
        """Returns whether (i'th) selection has a pts file with landmarks"""
        if i == None: i = self.iSelection()
        return(os.path.exists(self.strPtsFilename(i)))

    def strPtsFilename(self, i=None):
        """Returns filename of selected (or i'th) .pts file"""
        if i == None: i = self.iSelection()
        strImgFilename = self.lImgFilenames[i]
        return(os.path.splitext(strImgFilename)[0]+'.pts')

    def strImgFilename(self, i=None):
        """Returns filename of (i'th) selection's image"""
        if i == None: i = self.iSelection()
        return(self.lImgFilenames[i])

    def readPtsFile(self, i=None):
        """Returns list of points (lists) in (i'th) selection's .pts file"""
        if i == None: i = self.iSelection()
        if self.bHasPtsFile(i):
            hFile = open(self.strPtsFilename(i), 'r')
            lstrPoints = hFile.readlines()
            hFile.close()
            return(map(lambda(s): map(float, s.split(',')), lstrPoints))
        else:
            return([])

    def MarkAsLabeled(self, i=None):
        """Mark (i'th) selection as having a .pts file"""
        if i == None: i = self.iSelection()
        self.lbPts.insert(i, '+')
        self.lbPts.delete(i+1)
        self.lbPts.selection_set(i)

    def MarkAsUnlabeled(self, i=None):
        """Unmark (i'th) selection as having a .pts file"""
        if i == None: i = self.iSelection()
        self.lbPts.insert(i, '')
        self.lbPts.delete(i+1)
        self.lbPts.selection_set(i)

###############################################################################

def FindImgFiles(strPath):
    """Find all image files recursively in directory 'strPath'"""

    def bIsImgFile(strFilename):
        """Returns whether strFilename is an image file that's PIL-openable"""
        try:
            img = PIL.Image.open(strFilename)
            return(True)
        except IOError, e:
            return(False)

    def walker(strPath, lFilenames=[]):
        """Recursive file finder that follows symbolic links"""
        for strRoot, lDirs, lFiles in os.walk(strPath):
            # collect full paths for all files recursively found
            for strFile in lFiles:
                # svn stores a copy of the image so ignore those
                if strFile[len(strFile)-9:] != ".svn-base":
                    strFilename = os.path.join(strRoot, strFile)
                    if bIsImgFile(strFilename):
                        lFilenames.append(strFilename)
            # also walk directories that are symbolic links
            for strDir in lDirs:
                if os.path.islink(os.path.join(strRoot, strDir)):
                    walker(os.path.join(strRoot, strDir), lFilenames)
        return(lFilenames)

    # get a list of all files recursively found
    lFilenames = walker(strPath)
    lFilenames.sort()
    return(lFilenames)

###############################################################################

def main():
    strProgname = sys.argv[0]
    strUsage = '\n\tUsage: %s <directory>\n\n' % strProgname

    nArgs = len(sys.argv)-1
    if nArgs == 0 or nArgs > 1:
        print strUsage
        print '\t%s finds images recursively in given directory ' % strProgname
        print '\tand brings up a GUI for marking points in each image. The\n'+\
              '\tmarked points are saved to a file with the same name as\n'+\
              '\tthe image file, but with a .pts extension.\n'
        raise SystemExit(-1)

    strPath = sys.argv[1];
    if not os.path.isdir(strPath):
        print '\tError: directory %s does not exist.  Exiting...' % strPath
        raise SystemExit(-1)

    print '\nINSTRUCTIONS:'
    print '-------------'
    print 'Anywhere in the appliations:'
    print '\t<Down Arrow>  - go to next image'
    print '\t<Up Arrow>    - go to previous image'
    print '\t<Alt-F4>      - quit'
    print 'When the mouse is over displayed image:'
    print '\t<Left Mouse>  - add a point'
    print '\t<Right Mouse> - remove a point'
    print 'When the mouse is over the list of image filenames:'
    print '\t<Mouse wheel> - move through image list'
    print '\t<Left Mouse>  - select image to work on'
    print '\nNB: tagging is more accurate when this tool is maximized\n'
    print 'OUTPUT: For each tagged image, a text file with the same name'
    print '        as the original image filename (but with a .pts extension)'
    print '        is saved at the same location as the image.'

    Application(sys.argv[1]).mainloop()

###############################################################################

if __name__ == '__main__':
    main()
