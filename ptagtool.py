#!/usr/bin/env python
"""ptagtool.py - tool to tag images with points"""
# ptagtool.py - an image point tagging tool.  Saves tagged point coordinates
#               into text files with extension '.pts' and filename the same
#               as the image filename. Run this for instructions.

# File: ptagtool.py
# Author: Doron Tal

import sys
import os
from Tkinter import Frame, N, S, E, W, Canvas, Scrollbar, Listbox,\
    HORIZONTAL, VERTICAL, SINGLE, END, NW, SCROLL, UNITS
from tkFont import Font
from math import sqrt
from ImageTk import PhotoImage
import PIL.Image

class Application(Frame):
    """Container class, encapsulates app"""
    # this class inherits from Tkinter.parent
    def __init__(self, path, master=None):
        """Constructor"""
        # call parent class constructor
        Frame.__init__(self, master)

        self.path = path
        self.image_filenames = find_image_files(path)

        # necessary to make the application actually appear on the screen
        self.grid(sticky=N+S+E+W)

        # PIL image, for loading from file and for resizing
        self.image_pil = None

        # Tk photoimage, for display
        self.image_tk = None

        # list of coords (2-element lists) of current selection's pts
        self.points_orig = []

        # points_canvas is 'points_orig', in canvas coordinates
        self.points_canvas = []

        # x- and y-coords of displayed image in canvas coordinate frame
        self.x_offset = -1
        self.y_offset = -1

        # font in listbox text
        self.font = Font(family='Helvetica', size=10, weight='normal')

        # crosshair line size , as fraction of
        # min(displayed-imagewidth, displayed-image-height)
        self.crosshair_fraction = 0.05

        # color for drawing first crosshair - the origin
        self.crosshair1_color = 'red'

        # color for drawing second crosshair - (together with the first
        # crosshair, these two points define a coordinate frame) -
        self.crosshair2_color = 'green'

        # color for drawing third and on crosshairs - all points other
        # than the first and second, have this color
        self.crosshair3_color = 'cyan'

        # the width, in pixels, of crosshairs
        self.crosshair_thickness = 2

        # length of crosshair (updated upon display)
        self.crosshair_radius = -1

        # the scale of currently displayed image (updated upon display)
        self.image_scaling = 1.0

        # create all widges and set their initial conditions
        self.create_widgets()

    def create_widgets(self):
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
        top.bind_all('<Up>', self.select_prev)
        top.bind_all('<Down>', self.select_next)

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
                         s.on_resize_canvas(e.width-2, e.height-2))

        # bind canvas mouse clicks
        self.canvas.bind('<Button-1>', self.on_click_button1)
        self.canvas.bind('<Button-3>', self.on_click_button3)

        # create scrollbars
        self.scrollbar_x = Scrollbar(self, orient=HORIZONTAL, width=10)
        self.scrollbar_y = Scrollbar(self, orient=VERTICAL, width=10)

        self.scrollbar_x.grid(row=1, column=1, columnspan=2, sticky=E+W)
        self.scrollbar_y.grid(row=0, column=3, sticky=N+S)

        # create lb for showing labeled/not-labeled images
        self.listbox_marks = Listbox(self, width=1, takefocus=0,
                                     exportselection=0,
                                     font=self.font)

        self.listbox_marks.grid(row=0, column=1, sticky=N+S+E+W)

        # create lb for showing image filenames
        self.lisbox_filenames = Listbox(self, width=30, selectmode=SINGLE,
                                        xscrollcommand=self.scrollbar_x.set,
                                        yscrollcommand=self.scrollbar_y.set,
                                        exportselection=0, font=self.font)
        self.lisbox_filenames.grid(row=0, column=2, sticky=N+S+E+W)

        # bind scrollbar movement
        self.scrollbar_x['command'] = self.lisbox_filenames.xview
        self.scrollbar_y['command'] = self.on_scrollbar_y

        # bind left mouse click selection
        self.lisbox_filenames.bind('<Button-1>', lambda e, s=self:
                                   s.select(self.lisbox_filenames.nearest(e.y)))
        self.listbox_marks.bind('<Button-1>', lambda e, s=self:
                                s.select(self.lisbox_filenames.nearest(e.y)))

        # bind wheel scroll
        self.lisbox_filenames.bind('<Button-4>', lambda e, s=self:
                                   on_mousewheel(self.listbox_marks, 4))
        self.lisbox_filenames.bind('<Button-5>', lambda e, s=self:
                                   on_mousewheel(self.listbox_marks, 5))
        self.listbox_marks.bind('<Button-4>', lambda e, s=self:
                                on_mousewheel(self.lisbox_filenames, 4))
        self.listbox_marks.bind('<Button-5>', lambda e, s=self:
                                on_mousewheel(self.lisbox_filenames, 5))

        # skip is # of chars to skip in path string so that only the
        # part of the path that was not supplied is displayed
        skip = len(self.path)
        if self.path[skip-1] != '/':
            skip += 1

        # insert image filenames plus marks into lists and
        # select first image that does not have pts file
        i = 0
        index_of_image_with_no_pts_file = -1
        for image_filename in self.image_filenames:
            self.lisbox_filenames.insert(END, image_filename[skip:])
            if self.has_pts_file(i):
                self.listbox_marks.insert(END, '+')
            else:
                self.listbox_marks.insert(END, '')
                if index_of_image_with_no_pts_file < 0:
                    index_of_image_with_no_pts_file = i
            i += 1

        if index_of_image_with_no_pts_file < 0:
            self.select(0)
        else:
            self.select(index_of_image_with_no_pts_file)

    def on_scrollbar_y(self, *args):
        """Vertical scrollbar motion callback"""
        apply(self.lisbox_filenames.yview, args)
        apply(self.listbox_marks.yview, args)

    def on_click_button1(self, event):
        """Button 1 click callback: adds a crosshair at click location"""
        if self.coord_in_img(event.x, event.y):
            point = [(event.x-self.x_offset)/self.image_scaling,
                     (event.y-self.y_offset)/self.image_scaling]
            point_scaled = [float(event.x), float(event.y)]
            self.points_orig.append(point)
            self.points_canvas.append(point_scaled)
            if len(self.points_orig) == 1:
                self.mark_labeled()
            self.on_resize_canvas(self.canvas['width'], self.canvas['height'])
            self.save_points()

    def on_click_button3(self, event):
        """Button 3 click callback: deletes landmark near click location"""
        if not self.coord_in_img(event.x, event.y):
            return
        i = self.find_point_near_crosshair(event.x, event.y)
        if i >= 0:
            del self.points_orig[i]
            del self.points_canvas[i]
            if len(self.points_orig) == 0:
                self.mark_unlabeled()
            self.on_resize_canvas(self.canvas['width'], self.canvas['height'])
            self.save_points()

    def select(self, i):
        """Select the i'th image to work with - make current selection = i"""
        # uncomment the following line if you are only dealing with
        # faces that have three points labeled on them and you want to
        # automatically reorder a previously tagged database so that
        # the person's right eye is the first point, left eye is
        # second point and mouth is third point
        self.sort_points()
        self.lisbox_filenames.selection_clear(0, END)
        self.listbox_marks.selection_clear(0, END)
        self.lisbox_filenames.selection_set(i)
        self.listbox_marks.selection_set(i)
        self.lisbox_filenames.see(i)
        self.listbox_marks.see(i)
        self.image_pil = PIL.Image.open(self.get_image_filename())
        self.points_orig = self.read_pts_file()
        self.on_resize_canvas(self.canvas['width'], self.canvas['height'])

    def select_prev(self, *args):
        #pylint: disable=unused-argument
        """Select entry that comes before current selection"""
        i = self.get_selected_index()
        if i > 0:
            self.select(i-1)

    def select_next(self, *args):
        #pylint: disable=unused-argument
        """Select entry that comes after current selection"""
        i = self.get_selected_index()
        if i < len(self.image_filenames)-1:
            self.select(i+1)

    def on_resize_canvas(self, width, height):
        """Called when canvas is resized"""
        if width <= 0 or height <= 0:
            return
        # maximize image width or height depending on aspect ratios
        image_width = self.image_pil.size[0]
        image_height = self.image_pil.size[1]
        image_aspect_ratio = float(image_width)/float(image_height)

        self.canvas['width'] = width
        self.canvas['height'] = height
        canvas_width = int(self.canvas['width'])
        canvas_height = int(self.canvas['height'])
        canvas_aspect_ratio = float(canvas_width)/float(canvas_height)

        if image_aspect_ratio < canvas_aspect_ratio:
            new_image_width = int(image_aspect_ratio*float(canvas_height))
            new_image_height = canvas_height
        else:
            new_image_width = canvas_width
            new_image_height = int(float(canvas_width)/image_aspect_ratio)

        self.image_tk = PhotoImage(self.image_pil.resize((new_image_width,
                                                          new_image_height),
                                                         PIL.Image.BILINEAR))

        self.x_offset = 0.5*(float(canvas_width)-float(new_image_width))
        self.y_offset = 0.5*(float(canvas_height)-float(new_image_height))

        self.crosshair_radius = 0.5*self.crosshair_fraction*float(
            min(new_image_width, new_image_height))

        self.canvas.delete('image')
        self.canvas.create_image(self.x_offset, self.y_offset, anchor=NW,
                                 image=self.image_tk, tags='image')

        width_scale = float(new_image_width)/float(image_width)
        height_scale = float(new_image_height)/float(image_height)
        self.image_scaling = 0.5*(width_scale+height_scale)
        self.points_canvas = [[x[0]*self.image_scaling+self.x_offset,
                               x[1]*self.image_scaling+self.y_offset]
                              for x in self.points_orig]
        self.redraw_points()

    def redraw_points(self):
        """redraw points in current entry's .pts file"""
        self.canvas.delete('line')

        # draw first crosshair in color1
        if len(self.points_canvas) > 0:
            point1 = self.points_canvas[0]
            self.draw_crosshair(point1[0], point1[1], self.crosshair1_color)

        # draw second crosshair in color2
        if len(self.points_canvas) > 1:
            point2 = self.points_canvas[1]
            self.draw_crosshair(point2[0], point2[1], self.crosshair2_color)

        # draw third or higher crosshair in color3
        if len(self.points_canvas) > 2:
            for point in self.points_canvas[2:]:
                self.draw_crosshair(point[0], point[1], self.crosshair3_color)

    def draw_crosshair(self, x_coord, y_coord, fill_color):
        """Draw a cross at (x_coord, y_coord) in the currently selected image"""
        start_x = x_coord-self.crosshair_radius
        start_y = y_coord-self.crosshair_radius

        end_x = x_coord+self.crosshair_radius
        end_y = y_coord+self.crosshair_radius

        min_x = self.x_offset
        min_y = self.y_offset

        max_x = self.x_offset+self.image_tk.width()-1
        max_y = self.y_offset+self.image_tk.height()-1

        if start_x < min_x:
            start_x = min_x
        if start_y < min_y:
            start_y = min_y

        if end_x > max_x:
            end_x = max_x
        if end_y > max_y:
            end_y = max_y

        self.canvas.create_line(x_coord, start_y, x_coord, end_y,
                                width=self.crosshair_thickness, tags='line',
                                fill=fill_color)
        self.canvas.create_line(start_x, y_coord, end_x, y_coord,
                                width=self.crosshair_thickness, tags='line',
                                fill=fill_color)

    def get_selected_index(self):
        """Returns index of current selection"""
        return int(self.lisbox_filenames.curselection()[0])

    def coord_in_img(self, x_coord, y_coord):
        """Returns whether (x_coord, y_coord) is inside the shown image"""
        return (x_coord >= self.x_offset and
                y_coord >= self.y_offset and
                x_coord < self.x_offset+self.image_tk.width() and
                y_coord < self.y_offset+self.image_tk.height())

    def find_point_near_crosshair(self, x_coord, y_coord):
        """Returns index of landmark point near (x_coord, y_coord), or -1"""
        i = 0
        i_min = -1
        min_dist = self.image_tk.width()+self.image_tk.height()
        for pair in self.points_canvas:
            x_dist = x_coord-pair[0]
            y_dist = y_coord-pair[1]
            dist = sqrt(x_dist*x_dist+y_dist*y_dist)
            if dist <= self.crosshair_radius and dist < min_dist:
                i_min = i
            i += 1
        return i_min

    def save_points(self):
        """Save current points to pts file"""
        # remove whatever was there before
        if self.has_pts_file():
            os.remove(self.get_pts_filename())
        # save current result
        if len(self.points_orig) > 0:
            filehandle = open(self.get_pts_filename(), 'w')
            for pair in self.points_orig:
                message = str(pair[0])+', '+str(pair[1])+'\n'
                filehandle.write(message)
            filehandle.close()

    def sort_points(self):
        """
        Reorder points, assuming face labeling, so that the first point
        is always the person's right eye, the second point is the person's
        left eye and the third point is the mouth.  NB: this function only
        (destructively) works on self.points_orig
        """
        if len(self.points_orig) != 3:
            return
        # step 1 sort the points according to y-value
        self.points_orig.sort(lambda ptA, ptB:
                              cmp(ptA[1], ptB[1]))
        # step 2: from the top-most two points, call the leftmost one
        # the person's right eye and call the other the person's left eye
        if self.points_orig[0][0] > self.points_orig[1][0]:
            # swap first and second points' x-coordinate
            tmp = self.points_orig[0][0]
            self.points_orig[0][0] = self.points_orig[1][0]
            self.points_orig[1][0] = tmp
            # swap first and second points' y-coordinate
            tmp = self.points_orig[0][1]
            self.points_orig[0][1] = self.points_orig[1][1]
            self.points_orig[1][1] = tmp
            # order changed, so re-save
            self.save_points()

    def has_pts_file(self, i=None):
        """Returns whether (i'th) selection has a pts file with landmarks"""
        if i is None:
            i = self.get_selected_index()
        return os.path.exists(self.get_pts_filename(i))

    def get_pts_filename(self, i=None):
        """Returns filename of selected (or i'th) .pts file"""
        if i is None:
            i = self.get_selected_index()
        image_filename = self.image_filenames[i]
        return os.path.splitext(image_filename)[0]+'.pts'

    def get_image_filename(self, i=None):
        """Returns filename of (i'th) selection's image"""
        if i is None:
            i = self.get_selected_index()
        return self.image_filenames[i]

    def read_pts_file(self, i=None):
        """Returns list of points (lists) in (i'th) selection's .pts file"""
        if i is None:
            i = self.get_selected_index()
        if self.has_pts_file(i):
            filehandle = open(self.get_pts_filename(i), 'r')
            lines = filehandle.readlines()
            filehandle.close()
            return [[float(pair[0]), float(pair[1])]
                    for pair in [line.split(',') for line in lines]]
        else:
            return []

    def mark_labeled(self, i=None):
        """Mark (i'th) selection as having a .pts file"""
        if i is None:
            i = self.get_selected_index()
        self.listbox_marks.insert(i, '+')
        self.listbox_marks.delete(i+1)
        self.listbox_marks.selection_set(i)

    def mark_unlabeled(self, i=None):
        """Unmark (i'th) selection as having a .pts file"""
        if i is None:
            i = self.get_selected_index()
        self.listbox_marks.insert(i, '')
        self.listbox_marks.delete(i+1)
        self.listbox_marks.selection_set(i)

###############################################################################

def on_mousewheel(listbox, i_button, n_units=5):
    """Mouse wheel move callback"""
    if i_button == 5:
        listbox.yview(SCROLL, n_units, UNITS)
    if i_button == 4:
        listbox.yview(SCROLL, -n_units, UNITS)

def is_image_file(filename):
    """Returns whether filename is an image file that's PIL-openable"""
    try:
        PIL.Image.open(filename)
        return True
    except IOError:
        return False

def walker(path, filenames):
    """Recursive image file search (follows symlinked folders)"""
    for root, dirs, files in os.walk(path):
        # collect full paths for all files recursively found
        for filename in files:
            # svn stores a copy of the image so ignore those
            if filename[len(filename)-9:] != ".svn-base":
                full_path = os.path.join(root, filename)
                if is_image_file(full_path):
                    filenames.append(full_path)
        # also walk directories that are symbolic links
        for dirname in dirs:
            if os.path.islink(os.path.join(root, dirname)):
                walker(os.path.join(root, dirname), filenames)
    return filenames

def find_image_files(path):
    """Find all image files recursively in directory 'path'"""
    filenames = walker(path, [])
    filenames.sort()
    return filenames

###############################################################################

def main():
    """Function that runs when this script is called from the commandline"""
    progname = sys.argv[0]
    usage_message = '\n\tUsage: %s <directory>\n\n' % progname

    num_args = len(sys.argv)-1
    if num_args == 0 or num_args > 1:
        print usage_message
        print '\t%s finds images recursively in given directory ' % progname
        print '\tand brings up a GUI for marking points in each image. The\n'+\
              '\tmarked points are saved to a file with the same name as\n'+\
              '\tthe image file, but with a .pts extension.\n'
        raise SystemExit(-1)

    path = sys.argv[1]
    if not os.path.isdir(path):
        print '\tError: directory %s does not exist.  Exiting...' % path
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
