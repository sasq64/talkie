
## Intro

Talkie runs terminal based interpreters directly and write stdout to the screen and sends stdin from player input.

To support graphics and other special things escape codes are used.

A terminal based interpreter can be adopted to send strings in this format;

#[<data>]

These lines will be stripped from the output and tell the graphical UI what to do

## Commands

keymode

Game is in single key mode. Any key pressed by the player
will be sent to game. Prompt/input in UI should be hidden.

linemode

Game is in line mode. Input will not be sent until return is pressed (EOL should be included).

### Line Art

Line art images is assumed to have a fixed palette that
depends on the game being played.

gfx <mode>

Set graphics mode

imgsize <width> <height>

Resize canvas

line <x0> <y0> <x1> <y1> <col> <targetcol>

Draw a line into the canvas. Only affect pixels
that have the color target_col.

fill <x> <y> <col> <targetcol>

Flood fill at x,y with color col. Only fill if
the current color in the canvas is targetcol.

clear

Clear current canvas

setcolor <col0> <col1>

Remap colors. After this, drawing with col0 will
procuce col1 (from the fixed palette).

### Bitmaps


img <no> <width> <height> <ncolors>

Define attributes for bitmap <no>

pal <no> <color0> <color1> ...

Define the palette for bitmap <no>

pixels <no> <index0> <index1> ...

Define the pixels for bitmap <no>

bitmap <no>

Show bitmap number <no>. Must have been defined.


