from typing import NamedTuple, Optional
import abc

from tkinter import Frame, PanedWindow, Label, Button, Entry, Text, StringVar
from tkinter import Radiobutton, Checkbutton, Listbox, Scrollbar, Scale, Spinbox
from tkinter import LabelFrame, Menubutton, Menu, Canvas
from tkinter import Widget as TkWidget
from tkinter import FLAT, RAISED, HORIZONTAL, VERTICAL
from tkinter import LEFT, TOP, RIGHT, BOTTOM, X, Y, BOTH
from tkinter import SINGLE, MULTIPLE, BROWSE, EXTENDED, INSERT, END, DISABLED
from tkinter.ttk import Separator, Progressbar, Combobox, Notebook, Treeview

from .ui import TkGUI, MenuItem, EventName, widget, kwargsNotNull, mayGive1, nop,  bindXScrollBar, bindYScrollBar
from .utils import Backend
from .utils import guiCodegen as c

import tkinter.ttk as ttk
class TickScale(ttk.Frame):
  '''look function compat for TTk scale'''
  def __init__(self, master=None, command=None, **kwargs):
    super().__init__(master)
    self._showValue = kwargs.pop("showvalue", True)
    self._step = kwargs.pop("resolution", 0)
    self.columnconfigure(0, weight=1)
    def cmd(x): command(x); self.display_value(x) # must. call refresh.
    self.scale = ttk.Scale(self, command = cmd if command != None else self.display_value, **kwargs)
    self.scale.grid(row=1, sticky=TkGUI.Anchors.HOR)
    style = Style(self) # slider length.
    style_name = kwargs.get("style", "%s.TScale" % str(self.scale["orient"]).capitalize())
    self._w_slider = style.lookup(style_name, "sliderlength", default=30)
    self.digits = kwargs.get("tick_format", "%.0f")

    self._start = kwargs["from_"]
    self._extent = kwargs["to"] - kwargs["from_"]
    if self._showValue:
      Label(self, text=" ").grid(row=0)
      self.label = Label(self, text="0")
      self.label.place(in_=self.scale, bordermode="outside", x=0, y=0, anchor=TkGUI.Anchors.BOTTOM)
      self.display_value(self.scale.get())

    self.scale.grid(row=1, sticky=TkGUI.Anchors.HOR)
    # ticks
    if self._step != 0:
      Label(self, text=" ").grid(row=2)
      n_i = round(self._extent / self._step)
      self.ticks = [self._start + i*self._step for i in range(0, n_i+1)]
      self.place_ticks()

    self.scale.bind("<Configure>", self._reconfig)

  def _valPixels(self, value, w_max):
    percent = ((value - self._start) / self._extent)
    return percent * (w_max - self._w_slider) + (self._w_slider / 2)
  @staticmethod
  def roundInterval(v, step):
    rnd = round(v)
    dist = -1 if rnd > step else +1
    while rnd % step != 0: rnd += dist
    return rnd

  def display_value(self, value):
    value = float(value)
    w_me = self.scale.winfo_width()
    x = self._valPixels(value, w_me) # position (in pixel) of the center of the slider
    # pay attention to the borders
    self.label.place_configure(x=TickScale._bounds(x, w_me, TickScale._wHalf(self.label)))
    v = TickScale.roundInterval(value, self._step)
    self.label.configure(text=self.digits %v)
  @staticmethod
  def _bounds(n, max, sub):
    return max-sub if n+sub > max else n
  @staticmethod
  def _wHalf(e): return e.winfo_width() / 2
  def place_ticks(self):
    def createLabel(i):
      lbl = Label(self, text=self.digits %self.ticks[i])
      lbl.place(in_=self.scale, bordermode="outside", x=0, rely=1, anchor="n")
      return lbl
    # first tick 
    tick = self.ticks[0]; label = createLabel(0)
    w_me = self.scale.winfo_width()
    sval = lambda: self._valPixels(tick, w_me)
    w_half = lambda: TickScale._wHalf(label)
    labelX = lambda x: label.place_configure(x=x)
    labelX(max(sval(), w_half()) )
    # ticks in the middle
    for (i, tick) in enumerate(self.ticks[1:-1]):
      createLabel(1+i).place_configure(x=sval())
    # last tick
    tick = self.ticks[-1]; label = createLabel(len(self.ticks)-1)
    labelX(TickScale._bounds(sval(), w_me, w_half()) )

  def _reconfig(self, event):
    """Redisplay the ticks and the label so that they adapt to the new size of the scale."""
    if self._showValue: self.display_value(self.scale.get())
    self.place_ticks()

if Backend.TTk.isUsed():
  from tkinter.ttk import * # TTK support

'''
MenuItems: OpNamed(named), SubMenu, Sep(sep), CheckBox, RadioButton
Widgets(button/bar/line/box): button, radioButton, menuButton; scrollBar, progressBar; slider, text;
  (string:)input, textarea, (number:)spinBox, (boolean:)checkBox, (listing:)listBox, comboBox;
  menu, separator, canvas, treeWidget
Containers: HBox(horizontalLayout), VBox(verticalLayout); labeledBox,
  splitter, tabWidget, withFill, withScroll

Aux funs:
- _.fill(widget) can make a widget(.e) packed at specified side/fill
- _.var(type) can create a Tk value storage
- _.by(name, widget) can dynamic set widget as self.name attribute
'''

class Widget(TkWidget, metaclass=abc.ABCMeta): #TODO more GUI framework support
  def __init__(self, parent): pass
  def on(self, event_name:EventName, callback): return super().bind(event_name.name, callback)
  def __getitem__(self, conf): return super().__getitem__(conf)
  def __setitem__(self, conf, value): super().__setitem__(conf, value)
  @property
  def width(self): return super().winfo_width()
  @property
  def height(self): return super().winfo_height()
  def pack(self, **kwargs): return super().pack_configure(**kwargs)
  def forget(self): return super().forget()
  def destroy(self): return super().destroy()
class TkWidgetDelegate(Widget):
  def __init__(self, e):
    super().__init__(None)
    self.e:TkWidget = e
  def pack(self, **kwargs): return self.e.pack(**kwargs)
  def forget(self): return self.e.forget()
  def destroy(self): return self.e.destroy()
  def bind(self, event_name, callback): return self.e.bind(event_name, callback)
  def __getitem__(self, key): return self.e[key]
  def __setitem__(self, key, v): self.e[key] = v
  def configure(self, cnf=None, **kwargs): self.e.configure(cnf, **kwargs)
  config = configure

class Textarea(Text, Widget):
  def __init__(self, master=None, **kwargs):
    super().__init__(master=master, **kwargs)
    self.marker = Textarea.MarkerPos(self)
  class LineCol(NamedTuple("LineCol", [("line", int), ("col", int)])): #v text indexes comparing inherited.
    def __repr__(self): return f"LineCol({self.line}:{self.col})"

  class MarkerPos:
    def __init__(self, outter):
      self._outter = outter
    def coerceInBounds(self, index):
      o = self._outter
      if index < o.start: return o.start
      if index > o.end: return o.end
      return index
    def stepFrom(self, loc, chars=0, indices=0, lines=0):
      code = "%d.%d %+d lines %+d chars %+d indices" % (loc.line, loc.col, lines, chars, indices)
      return self.coerceInBounds(self[code])

    def __getitem__(self, name) -> "Textarea.LineCol":
      (line, col) = map(int, self._outter.index(name).split("."))
      return Textarea.LineCol(line, col)
    def __setitem__(self, name, pos):
      self._outter.mark_set(name, "%i.%i" %(pos.line, pos.col))
    def __delitem__(self, name):
      self._outter.mark_unset(name)

  @property
  def start(self): return Textarea.LineCol(1, 0)
  @property
  def end(self): return self.marker["end - 1 char"]
  @property
  def wrap(self): return self["wrap"]
  @wrap.setter
  def wrap(self, v): self["wrap"] = v

MSG_INSERT_EMPTY = "inserting empty [] to: %s"
class TreeWidget(Treeview, Widget):
  def __init__(self, parent=None, **kw):
    super().__init__(parent, **kw)
    self._ids = {}
  def _unqid(self, text): # Tk can generate ids, but we shall use indexable ones
    qid = text
    while qid in self._ids: qid = c.nextName(qid)
    self._ids[text] = qid
    return qid

  def makeTree(self, headings, tree):
    '''[tree] is a (tuple name, childs for nested), or str list'''
    if len(headings) == 0: self["show"] = "tree"
    else:
      headings1 = [headings[0], "hide"] + headings[1:]
      self["columns"] = headings1
      for (i, hd) in enumerate(headings1): self.heading("#%d" %i, text=hd, anchor="w")
      self.column("#1", stretch=False, minwidth=0, width=0)
    def insert(nd, src):
      self.insert(nd, END, self._unqid(src), text=str(src), values=(str(src),))
    def insertRec(nd, src):
      if isinstance(src, tuple):
        (name, childs) = src
        insert(nd, name)
        for it in childs: insertRec(name, it)
      elif isinstance(src, list):
        if len(src) == 0: raise ValueError(MSG_INSERT_EMPTY %nd)
        self.insert(nd, END, self._unqid(src[0]), text=str(src[0]), values=src)
      else: insert(nd, src)
    for leaf in tree: insertRec("", leaf) # required for texts in root
  class TreeItem:
    '''you must call [TreeWidget.makeTree] before indexing any column, note None is returned if key missing'''
    def __init__(self, id, outter):
      self._outter:TreeWidget = outter
      self.id = id
    def __eq__(self, other): return self.id == other.id
    def __hash__(self): return self.id.__hash__()
    def __repr__(self): return "TreeItem(%s)" %self.id
    def wrap(self, id): return TreeWidget.TreeItem(id, self._outter)
    def isExists(self): return self._outter.exists(self.id)
    def __getitem__(self, index): return self._outter.set(self.id, index)
    def __setitem__(self, index, v): return self._outter.set(self.id, index, v)
    def focus(self):
      self._outter.see(self.id)
      self._outter.focus(self.id)
    def remove(self):
      self._outter.delete(self.id)
    def removeChilds(self):
      self._outter.delete(*self._outter.get_children(self.id))
    def detach(self):
      self._outter.detach(self.id)
    def moveTo(self, dst):
      self._outter.move(self.id, dst, END)
    def addChild(self, values, is_open=False) -> "TreeWidget.TreeItem":
      if values == None or len(values) == 0: raise ValueError(MSG_INSERT_EMPTY %self.id)
      name = values[0]
      iid = None if name == None else self._outter._unqid(str(name))
      child = self._outter.insert(self.id, END, iid, text=(name or ""), values=values, open=is_open)
      return self.wrap(child)
    @property
    def parent(self) -> "Optional[TreeWidget.TreeItem]":
      id = self._outter.parent(self.id)
      return self.wrap(id) if id != "" else None
    @property
    def childs(self): return [self.wrap(it) for it in self._outter.get_children(self.id)]

  def item(self, text):
    '''gets the latest item inserted named [text]'''
    return TreeWidget.TreeItem(self._ids.get(text) or text, self)
  @property
  def rootItem(self): return self.item("")
  @property
  def focusItem(self): return self.item(self.focus())
  @property
  def selectedItems(self): return [self.item(id) for id in self.selection()]
  def selectItems(self, items):
    self.selection(items=[it.id for it in items])
  open = EventName("<<TreeviewOpen>>")


class Box(Frame, Widget):
  def __init__(self, parent, pad, is_vertical):
    super().__init__(parent)
    self.childs = []
    self.pad,self.is_vertical = pad,is_vertical
  def pack(self, **kwargs):
    super().pack(**kwargs)
    if len(self.childs) == 0: return
    self.childs[0].pack(side=(TOP if self.is_vertical else LEFT) )
    for it in self.childs[1:]: self._appendChild(it)
  def destroy(self):
    for it in self.childs: self.removeChild(it)

  def _appendChild(self, e):
    if self.is_vertical: e.pack(side=TOP, fill=Y, pady=self.pad)
    else: e.pack(side=LEFT, fill=X, padx=self.pad)
  def appendChild(self, e_ctor):
    e = mayGive1(self, e_ctor)
    if isinstance(e, list):
      for it in e: self._appendChild(it)
      self.childs.extend(e)
    else:
      self._appendChild(e)
      self.childs.append(e)
  def removeChild(self, e):
    e.forget()
    try: e.destory()
    except AttributeError: pass
    self.childs.remove(e)
  @property
  def firstChild(self): return self.childs[0]
  @property
  def lastChild(self): return self.childs[-1]
class HBox(Box):
  def __init__(self, parent, pad=3):
    super().__init__(parent, pad, False)
class VBox(Box):
  def __init__(self, parent, pad=5):
    super().__init__(parent, pad, True)

class ScrolledFrame(Frame):
  def __init__(self, parent, orient):
    super().__init__(parent)
    self.oreint = orient
    o = self.oreint
    both = (o == BOTH)
    self.hbar = Scrollbar(self, orient=HORIZONTAL) if o == HORIZONTAL or both else None
    self.vbar = Scrollbar(self, orient=VERTICAL) if o == VERTICAL or both else None
    self.item:Optional[TkWidget] = None
  def pack(self, **kwargs):
    super().pack(**kwargs)
    if self.hbar != None: self.hbar.pack(side=BOTTOM, fill=X)
    if self.vbar != None: self.vbar.pack(side=RIGHT, fill=Y)
    self.item.pack()
    if self.hbar: bindXScrollBar(self.item, self.hbar)
    if self.vbar: bindYScrollBar(self.item, self.vbar)

class PackSideFill(TkWidgetDelegate):
  def __init__(self, e, side:Optional[str], fill):
      super().__init__(e)
      self.side,self.fill = side,fill
  def reside(self, new_side):
    return type(self)(self.e, new_side, self.fill)
  def pack(self, *args, **kwargs):
    kwargs.update({"side": self.side or kwargs.get("side"), "fill": self.fill, "expand": self.fill == BOTH})
    self.e.pack(*args, **kwargs)
  def set(self, *args): return self.e.__getattribute__("set")(*args) #dytype

def _createLayout(ctor_box, p, items):
  box = c.callNew(ctor_box, p)
  c.named("lh" if isinstance(box, HBox) else "lv", box)
  c.setAttr(box, "childs", list(mayGive1(box, it) for it in items))
  return box
def verticalLayout(*items): return lambda p: _createLayout(VBox, p, items)
def horizontalLayout(*items): return lambda p: _createLayout(HBox, p, items)
@widget
def createLayout(p, orient, pad, *items):
  box = c.named("box", c.callNew(HBox, p, pad) if orient == HORIZONTAL else c.callNew(VBox, p, pad))
  c.setAttr(box, "childs", list(mayGive1(box, it) for it in items))
  return box

@widget
def menu(p, *items, use_default_select = False):
  e_menu = c.callNew(Menu, p, tearoff=use_default_select)
  for it in items:
    if isinstance(it, MenuItem.OpNamed):
      c.invoke(e_menu, "add_command", label=it.name, command=it.op)
    elif isinstance(it, MenuItem.SubMenu):
      child = menu(*it.childs, use_default_select)(e_menu) # cg:flatten
      c.invoke(e_menu, "add_cascade", label=it.name, menu=child)
    elif isinstance(it, MenuItem.Sep): c.invoke(e_menu, "add_separator")
    elif isinstance(it, MenuItem.CheckBox): c.invoke(e_menu, "add_checkbutton", label=it.name, variable=it.dst)
    elif isinstance(it, MenuItem.RadioButton): c.invoke(e_menu, "add_radiobutton", label=it.name, variable=it.dst, value=it.value)
  return e_menu

#^ layouts+menu v button/bar/slider/box
@widget
def text(p, valr, **kwargs):
  kwargs["textvariable" if isinstance(valr, StringVar) else "text"] = valr
  return c.named("t", c.callNew(Label, p, **kwargs))
@widget
def textarea(p, placeholder=None, readonly=False, **kwargs):
  text = c.callNew(Textarea, p, **kwargs)
  if placeholder != None: c.invoke(text, "insert", INSERT, placeholder)
  if readonly: c.setItem(text, "state", DISABLED)
  return text
@widget
def button(p, text, on_click, **kwargs):
  return c.named("btn", c.callNew(Button, p, text=text, command=on_click, **kwargs))
@widget
def radioButton(p, text, dst, value, on_click=nop):
  return c.named("rbtn", c.callNew(Radiobutton, p, text=text, variable=dst, value=value, command=on_click))
@widget
def menuButton(p, text, menu_ctor, **kwargs):
  menub = c.callNew(Menubutton, p, text=text, **kwargs)
  c.setItem(menub, "menu", mayGive1(menub, menu_ctor))
  return menub
@widget
def input(p, placeholder="", **kwargs):
  ent = c.named("ent", c.callNew(Entry, p, **kwargs))
  c.invoke(ent, "delete", 0, END)
  c.invoke(ent, "insert", 0, placeholder)
  return ent
@widget
def spinBox(p, range:range, **kwargs):
  if range.step != 1: return c.callNew(Spinbox, p, values=tuple(range), **kwargs)
  else: return c.callNew(Spinbox, p, from_=range.start, to=range.stop-1, **kwargs)
@widget
def slider(p, range:range, **kwargs):
  ctor = TickScale if Backend.TTk.isUsed() else Scale
  return c.callNew(ctor, p, from_=range.start, to=range.stop-1, resolution=range.step, **kwargs)
@widget
def checkBox(p, text_valr, dst, a=True, b=False, on_click=nop):
  '''make [text_valr] and [dst] points to same if you want to change text when checked'''
  valr = text_valr
  cbox = c.named("ckbox", c.callNew(Checkbutton, p, **{"textvariable" if isinstance(valr, StringVar) else "text": valr}, 
    variable=dst, onvalue=a, offvalue=b, command=nop))
  return cbox
@widget
def listBox(p, items, mode=SINGLE, **kwargs):
  mode1 = BROWSE if mode == SINGLE else EXTENDED
  lbox = c.named("lbox", c.callNew(Listbox, p, selectmode=mode1, **kwargs))
  for (i, it) in enumerate(items): c.invoke(lbox, "insert", i, it)
  return lbox
@widget
def comboBox(p, dst, items):
  cmbox = c.named("cbox", c.callNew(Combobox, p, textvariable=dst, values=items))
  return cmbox
@widget
def scrollBar(p, orient=VERTICAL):
  scroll = c.callNew(Scrollbar, p, orient=orient)
  sbar = c.callNew(PackSideFill, scroll, None, Y if orient==VERTICAL else X)
  return c.named("sbar", sbar)
@widget
def progressBar(p, dst, orient=HORIZONTAL):
  return c.callNew(Progressbar, p, variable=dst, orient=orient)

@widget
def separator(p, orient=HORIZONTAL):
  return c.callNew(Separator, p, orient=orient)
@widget
def canvas(p, dim, **kwargs):
  (width,height) = dim
  return c.callNew(Canvas, p, width=width, height=height, **kwargs)
@widget
def treeWidget(p, mode=SINGLE):
  mode1 = BROWSE if mode == SINGLE else EXTENDED
  treev = c.callNew(TreeWidget, p, selectmode=mode1)
  return treev

@widget
def labeledBox(p, text, *items, **kwargs):
  box = c.named("labox", c.callNew(LabelFrame, p, text=text, **kwargs))
  for it in items: c.invoke(mayGive1(box, it), "pack")
  return box
@widget
def splitter(p, orient, *items, weights=None, **kwargs): #TODO
  paned_win = c.named("spl", c.callNew(PanedWindow, p, orient=orient, **kwargs))
  for it in items: c.invoke(paned_win, "add", mayGive1(paned_win, it))
  return paned_win
@widget
def tabWidget(p, *entries):
  '''you may want tabs to fill whole window, use [fill].'''
  tab =  c.named("tab", c.callNew(Notebook, p))
  for (name, e_ctor) in entries:
    e = mayGive1(tab, e_ctor)
    if isinstance(e, Box): c.invoke(e, "pack") # in tabs, should pack early
    c.invoke(tab, "add", e, text=name)
  return tab
@widget
def withFill(p, e_ctor, fill=BOTH, side=None):
  filler = c.named("filler", c.callNew(PackSideFill, mayGive1(p, e_ctor), side, fill))
  return filler
@widget
def withScroll(p, orient, e_ctor):
  '''must call setup() to bind scroll in setup()'''
  frame = c.named("scrolld", c.callNew(ScrolledFrame, p, orient))
  c.setAttr(frame, "item", mayGive1(frame, e_ctor))
  return frame
