'''
This is a declarative wrapper for Python's tkinter GUI layout support.
use TkGUI(toplevel) / TkWin from tkgui.ui ; text(str)/input()/... from tkgui.widgets

Common knowledges on Tk:
- there's three layout managers: pack(box-layout), grid, posit(absolute)
- in pack there's three common property: master(parent), side(gravity), fill(size-match-parent), expand(able-to-change)
- packing order is useful: e.g. you have a full-size listBox with yScrollBar, then pack scrollBar first
- use keyword arg(k=v) in constructor or item.configure(k=v)/item[k]=v for widget setup
- Tk should be singleton, use Toplevel for a new window
- Parallelism: Tk cannot gurantee widgets can be updated correctly from other threads, set event loop [Tk.after] instead
Notice:
- this lib uses [widget] decorator to make first arg(parent) *curried*(as first arg in returned lambda)
- two main Box layout (VBox, HBox) .appendChild can accept (curried widget ctor)/widget-value/(widget list ctor)
- use .childs for children list of a layout, since .children is a Tk property
- use shorthand: _ = self.underscore
- spinBox&slider: range(start, stop) is end-exclusive, so 1..100 represented as range(1,100+1)
- rewrite layout&setup (do setXXX setup or bind [TkGUI.connect] listener) and call run(title) to start GUI application

Features adopted from Teek:
- init_threads to add a global event poller from threads (but this lib is not globally thread safe :( )
- make textarea marks from float to (line,col)
- remove Widget.after&after_cancel, use Timeout objects with global creator

TODO:
- Adopt Font, Color, Pen/Palette objects
- Adopt Image, ScreenDistance(dimension), Varaible (maybe, but _.by is enough?)
- Adopt Extras: Links for Textarea, and tooltips for all widgets
- Make window object like GTK: isDecorated, modal, position
- Table (kind of Treeview with drag/sort column), ColumnEditor
- Grid, ToggledFrame, ScrolledFrame
- Calendar, askFont
'''

__all__ = ["ui", "widgets", "utils"]
from .tickscale import TickScale