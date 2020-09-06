from tkinter import Menu, PhotoImage
from tkinter import Tk, Toplevel
from tkinter import StringVar, BooleanVar, IntVar, DoubleVar
import tkinter.constants as kst

import tkinter.messagebox as tkMsgBox
import tkinter.filedialog as tkFileMsgBox
from tkinter import Widget as TkWidget
from tkinter.ttk import Style, Sizegrip

from typing import cast, TypeVar, Callable, Any, Optional, Union, Tuple, MutableMapping
import threading
import time # for async:delay

from .utils import EventCallback, EventPoller
from .utils import guiCodegen as c

from functools import wraps
def makeThreadSafe(op:Callable):
  '''
  A decorator that makes a function safe to be called from any thread, (and it runs in the main thread).
  If you have a function runs a lot of Tk update and will be called asynchronous, better decorate with this (also it will be faster)
  [op] should not block the main event loop.
  '''
  @wraps(op)
  def safe(*args, **kwargs): return callThreadSafe(op, args, kwargs).getValue()
  return safe

T = TypeVar("T"); R = TypeVar("R")
def mayGive1(value:T, op_obj:Union[Callable[[T], R], R]) -> R:
  '''creates a [widget]. If TkGUI switch to use DSL tree-data construct, this dynamic-type trick can be removed'''
  return op_obj(value) if callable(op_obj) else op_obj

def kwargsNotNull(**kwargs):
  to_del = []
  for key in kwargs:
    if kwargs[key] == None: to_del.append(key)
  for key in to_del: del kwargs[key]
  return kwargs

def nop(*arg): pass

rescueWidgetOption:MutableMapping[str, Callable[[str], Tuple[str, Any]]] = {}

import re
from tkinter import TclError

def widget(op):
  '''make a "create" with kwargs configuration = lambda parent: '''
  def curry(*args, **kwargs):
    kwargs1 = kwargs
    def createWidget(p): #< cg: NO modify
      try: return op(p, *args, **kwargs1)
      except TclError as e:
        mch = re.search("""unknown option "-([^"]+)"$""", str(e))
        if mch != None:
          opt = mch.groups()[0]
          rescue = rescueWidgetOption.get(opt)
          if rescue != None: # dirty hack for tk/ttk configure compat
            subst = rescue(kwargs1[opt])
            if subst == None: del kwargs1[opt]
            else: kwargs1[subst[0]] = subst[1]
            return createWidget(p)
        raise e
    return createWidget
  return curry

class EventName:
  def __init__(self, name:str):
    self.name = "on%s" %name.capitalize() if name.isalnum() else name
  def __str__(self):
    return self.name
  __repr__ = __str__

class MenuItem:
  def __init__(self, name):
    self.name = name
class MenuItem:
  class OpNamed(MenuItem):
    def __init__(self, name, op):
      super().__init__(name); self.op = op
  @staticmethod
  def named(name, op): return MenuItem.OpNamed(name, op)
  class SubMenu(MenuItem):
    def __init__(self, name, childs):
      super().__init__(name); self.childs = childs
  class Sep(MenuItem):
    def __init__(self): super().__init__("|")
  sep = Sep()
  class CheckBox(MenuItem):
    def __init__(self, name, dst):
      super().__init__(name); self.dst=dst
  class RadioButton(MenuItem):
    def __init__(self, name, dst, value):
      super().__init__(name); self.dst,self.value = dst,value

class BaseTkGUI:
  def __init__(self, root):
    self.tk:Toplevel = root
    self.ui:Optional[TkWidget] = None #>layout
    self.treeUI:TkWidget
    self.style:Style = Style(self.tk)
  def layout(self) -> "widgets.Widget":
    '''
    you can also put static layout configuration (e.g. title/icon/size/sizeBounds) and they are inclueded in codegen.
    (FAILED since Python has NO overriding) I'm sorry about adding so many kwargs, but Python is not real OOP (just obj.op_getter property-based),
    there's no name can be implicitly(w/o "self") solved in scope -- inner class, classmethod, staticmethod, property, normal defs
    so only global/param/local can be used without boilerplates, I've choosen keyword args.
    '''
    raise NotImplementedError("main layout")
  def setup(self): pass

  def var(self, type, initial=None, var_map = {str: StringVar, bool: BooleanVar, int: IntVar, float: DoubleVar}):
    with c.regResult():
      variable = c.named("var", c.callNew(var_map[type], self.tk))
      if initial != None: c.invoke(variable, "set", initial)
    return variable # may in ctor, no codegen autoname
  def by(self, attr, e_ctor):
    def createAssign(p):
      e = mayGive1(p, e_ctor)
      c.setAttr(self, attr, e); return e
    return createAssign
  @property
  def shorthand(self) -> "BaseTkGUI": return self

  def run(self, title="App", compile_binding=None):
    self.tk.wm_deiconify()
    self.tk.wm_title(title)
    if compile_binding != None:
      self.runCode(self.getCode(), **compile_binding)
      return
    self.ui = mayGive1(self.tk, self.layout())
    self.ui.pack()
    self.setup()
    self.focus(); self.tk.mainloop()
  def getCode(self, run=False) -> str:
    '''gets code for layout&widgets, note codes in __init__ (e.g. var) is ignored (replace with _.by(attr,it) in layout)'''
    c.isEnabled = True
    if run: self.run("Codegen Running")
    ui = self.ui or mayGive1(self.tk, self.layout())
    # give missing epilog assign
    c.setAttr(self, "treeUI", ui)
    code = c.getCode()
    c.isEnabled = False
    c.clear()
    return code
  def _compile(self, code): return compile(code, "<runCode-%s>" %type(self).__qualname__, "exec")
  def runCode(self, code, **extra_names):
    '''run generated code or type:code, then show result self.treeUI'''
    codeRef = self._compile(code) if isinstance(code, str) else code
    from .widgets import __dict__ as widgets_globals
    widgets_globals.update(globals())
    exec(codeRef, widgets_globals, {"tkgui": TkGUI.root, "root": TkGUI.root.tk, "win": self, **extra_names})
    self.treeUI.pack()
    self.ui = self.ui or self.treeUI #:dytype
    self.setup()
    self.focus(); self.tk.mainloop()
  @property
  def title(self) -> str: return self.tk.wm_title()
  @title.setter
  def title(self, v): c.invoke(self.tk, "wm_title", v)
  def setIcon(self, path:str):
    try: c.invoke(self.tk, "wm_iconphoto", c.callNew(PhotoImage, file=path) ) #cg:note
    except TclError: self.tk.wm_iconbitmap(path)
  @property
  def size(self) -> tuple:
    code = self.tk.wm_geometry()
    return tuple(int(d) for d in code[0:code.index("+")].split("x"))
  def setSize(self, dim, xy=None):
    '''sets the actual size/position of window'''
    code = "x".join(str(i) for i in dim)
    if xy != None: code += "+%d+%d" %(xy[0],xy[1])
    c.invoke(self.tk, "wm_geometry", code)
  def setSizeBounds(self, min:tuple, max:tuple=None):
    '''set [min] to (1,1) if no limit'''
    c.invoke(self.tk, "wm_minsize", min[0], min[1])
    if max: c.invoke(self.tk, "wm_maxsize", max[0], max[1])
  def setWindowAttributes(self, attrs): self.tk.wm_attributes(*attrs)
  @property
  def screenSize(self):
    return (self.tk.winfo_screenwidth(), self.tk.winfo_screenheight() )

  def focus(self): self.tk.focus_set()
  def listThemes(self): return self.style.theme_names()
  @property
  def theme(self): return self.style.theme_use()
  @theme.setter
  def theme(self, v): return self.style.theme_use(v) #cg:no
  def addSizeGrip(self):
    sg = c.callNew(Sizegrip, self.ui)
    c.invoke(sg, "pack", side=kst.RIGHT)

  hor = kst.HORIZONTAL;
  vert = kst.VERTICAL;
  both = kst.BOTH;
  left,top,right,bottom = kst.LEFT,kst.TOP,kst.RIGHT,kst.BOTTOM;
  raised,flat= kst.RAISED,kst.FLAT;
  atCursor,atEnd= kst.INSERT,kst.END;
  chooseSingle,chooseMulti = kst.SINGLE,kst.MULTIPLE;
  class Anchors:
    LT=kst.NW; TOP=kst.N; RT=kst.NE;
    L=kst.W; CENTER=kst.CENTER; R=kst.E;
    LD=kst.SW; BOTTOM=kst.S; RD=kst.SE;
    HOR=kst.EW; VERT=kst.NS;
    ALL=kst.NSEW;

  class Cursors:
    arrow="arrow"; deny="circle"
    wait="watch"
    cross="cross"; move="fleur"; kill="pirate"

  class Events:
    click = EventName("<Button-1>")
    doubleClick = EventName("<Double 1>")
    mouseM = EventName("<Button-2>")
    mouseR = EventName("<Button-3>")
    key = EventName("<Key>")
    enter = EventName("<Enter>"); leave = EventName("<Leave>")

  def setMenu(self, menu_ctor):
    c.setItem(self.tk, "menu", menu_ctor(self.tk))
  def makeMenuPopup(self, menu_ctor):
    menu = mayGive1(self.tk, menu_ctor)
    def popup(event):
      try: menu.tk_popup(event.x_root, event.y_root) 
      finally: menu.grab_release()
    return popup

  def alert(self, msg, title=None, kind="info"):
    tie = title or kind.capitalize()
    if kind == "info": tkMsgBox.showinfo(msg, tie)
    elif kind == "warn": tkMsgBox.showwarning(msg, tie)
    elif kind == "error": tkMsgBox.showerror(msg, tie)
    else: raise ValueError("unknown kind: "+kind)

  def ask(self, msg, title="Question") -> str: return tkMsgBox.askquestion(title, msg)
  def askCancel(self, msg, title="Proceed?") -> bool: return not tkMsgBox.askokcancel(title, msg)
  def askOrNull(self, msg, title="Question") -> Optional[bool]: return tkMsgBox.askyesnocancel(title, msg)

  def askOpen(self, file_types, title=None, initial_dir=None, mode=kst.SINGLE) -> str:
    '''ask path(s) to open, with file types and (optional)title, init dir'''
    kws = kwargsNotNull(filetypes=file_types, title=title, initialdir=initial_dir)
    return tkFileMsgBox.askopenfilename(**kws) if mode == kst.SINGLE else tkFileMsgBox.askopenfilenames(**kws)
  def askSave(self, default_extension, file_types, title=None, initial=None, initial_dir=None) -> str:
    '''ask path (initial) to save to, with choosed file type'''
    kws = kwargsNotNull(title=title, initialfile=initial, initialdir=initial_dir)
    return tkFileMsgBox.asksaveasfilename(defaultextension=default_extension, filetypes=file_types, **kws)
  def askSaveDir(self, title=None) -> str: return tkFileMsgBox.askdirectory(**kwargsNotNull(title=title))

def connect(sender, signal, receiver, slot): #cg:todo?
  ''' connects a command from [sender] to notify [receiver].[slot], or call slot(sender, receiver, *signal_args) '''
  def runProc(*arg, **kwargs):
    return slot(sender, receiver, *arg, **kwargs)
  listen = receiver.__getattribute__(slot) if not callable(slot) else runProc
  sender[signal+"command"] = listen

def _bindScrollBarY(a, b, evt, v, *args): b.yview_moveto(v)
def _bindScrollBarX(a, b, evt, v, *args): b.xview_moveto(v)

def bindYScrollBar(box, bar):
  connect(box, "yscroll", bar, "set")
  connect(bar, "", box, _bindScrollBarY)
def bindXScrollBar(box, bar):
  connect(box, "xscroll", bar, "set")
  connect(bar, "", box, _bindScrollBarX)


class TkGUI(BaseTkGUI, EventPoller):
  root:"TkGUI" = None
  def __init__(self):
    super().__init__(Tk())
    EventPoller.__init__(self)
    self.on_quit = EventCallback()
    TkGUI.root = self
    c.named("tkgui", self, is_extern=True)
    c.named("root", self.tk, is_extern=True)
    def onQuit(ev): self.on_quit.run()
    self.tk.bind("<Destroy>", onQuit)
  def quit(self):
    self.tk.destroy()

class TkWin(BaseTkGUI):
  def __init__(self):
    super().__init__(Toplevel(TkGUI.root.tk))
    c.named("win", self, is_extern=True)
    c.getAttr(self, "tk")

def callThreadSafe(op, args=(), kwargs={}):
  return TkGUI.root.callThreadSafe(op, args, kwargs)

def runAsync(thunk, op, **kwargs):
  '''launch the [thunk], then call [op] safely with args, return thunk() result'''
  future = lambda res: callThreadSafe(op, (res,), kwargs)
  return thunk(future)

def delay(msec):
  return lambda cb: threading.Thread(target=lambda cb1: cb1(time.sleep(msec/1000)), args=(cb,)).start()

class Timeout:
  def __init__(self, after_what, op):
    assert TkGUI.root != None, "TkGUI not initialized"
    self.op = op
    self._id = TkGUI.root.tk.after(after_what, op)

  def cancel(self):
    """Prevent this timeout from running as scheduled."""
    TkGUI.root.tk.after_cancel(self._id) # race condition?
