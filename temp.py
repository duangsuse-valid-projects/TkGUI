import tkinter as tk
import tkinter.ttk as ttk

class WidgetWrapper:
  '''base mixin  class for widgets that wraps another widget. _reconfig is called when configure'''
  def __init__(self, widget, key_map):
    self._wid:TkWidget = widget
    self._keyMap:dict = key_map
    self._wid.bind("<Configure>", lambda ev: self._reconfig())
  def _wkeys(self): return self._wid.keys() + list(self._keyMap.keys())
  def _wcget(self, key):
    name = self._keyMap.get(key)
    return self.__getattribute__(name) if name != None else self._wid.cget(key)
  def _wconfigure(self, cnf={}, **kw):
    cnf.update(kw)
    poped = set()
    for (key, value) in cnf.items():
      name = self._keyMap.get(key)
      if name != None: self.__setattr__(name, value); poped.add(key)
    for key in poped: del cnf[key]
    self._wid.configure(cnf)
    self._reconfig()

import tkinter as tk
import tkinter.ttk as ttk

class AutoHideScrollbar(ttk.Scrollbar):
  """Scrollbar that automatically hides when not needed."""
  def __init__(self, parent=None, **kwargs):
    super().__init__(parent, **kwargs)
    self._kw = {}
    self._layout = 'place'

  def set(self, lo, hi):
    """Set the fractional values of the slider position."""
    if float(lo) <= 0.0 and float(hi) >= 1.0:
      if self._layout == 'place':
        self.place_forget()
      elif self._layout == 'pack':
        self.pack_forget()
      else: self.grid_remove()
    else:
      if self._layout == 'place':
        self.place(**self._kw)
      elif self._layout == 'pack':
        self.pack(**self._kw)
      else: self.grid()
    super().set(lo, hi)

  def _get_info(self, layout):
      """Alternative to pack_info and place_info in case of bug."""
      info = str(self.tk.call(layout, "info", self._w)).split("-")
      return dict([it.strip().split() for it in info if it != None])

  def _tryGet(self, get, name):
    self._layout = name
    try: return get()
    except TypeError: return self._get_info(name)
  def place_configure(self, **kw):
    super().place_configure(**kw)
    self._kw = self._tryGet(self.place_info, "place")

  def pack_configure(self, **kw):
    super().pack_configure(**kw)
    self._kw = self._tryGet(self.pack_info, "pack")

  def grid_configure(self, **kw):
    super().grid_configure(**kw)
    self._layout = "grid"

class ScrolledFrame(ttk.Frame):
    """
    A frame that sports a vertically oriented scrollbar for scrolling.
    :ivar interior: :class:`ttk.Frame` in which to put the widgets to be scrolled with any geometry manager.
    """
    def __init__(self, master=None, canvas_dim=(400,400), canvas_border=0, scroll_autohide=True, scroll_compound=tk.RIGHT, **kwargs):
      super.__init__(master, **kwargs)
      self.rowconfigure(0, weight=1)
      self.columnconfigure(1, weight=1)
      self._scrollbar = AutoHideScrollbar(self, orient=tk.VERTICAL) if scroll_autohide else ttk.Scrollbar(self, orient=tk.VERTICAL)
      self._canvas = tk.Canvas(self, width=canvas_dim[0], height=canvas_dim[1], borderwidth=canvas_border,
        highlightthickness=0, yscrollcommand=self._scrollbar.set)
      self.__compound = scroll_compound
      self._scrollbar.config(command=self._canvas.yview)
      self._canvas.yview_moveto(0)
      self.interior = ttk.Frame(self._canvas)
      self._interior_id = self._canvas.create_window(0, 0, window=self.interior, anchor=tk.NW)
      self.interior.bind("<Configure>", self.__configure_interior)
      self._canvas.bind("<Configure>", self.__configure_canvas)
      self.__grid_widgets()

    def __grid_widgets(self):
      """Places all the child widgets in the appropriate positions."""
      scrollbar_column = 0 if self.__compound is tk.LEFT else 2
      self._canvas.grid(row=0, column=1, sticky="nswe")
      self._scrollbar.grid(row=0, column=scrollbar_column, sticky="ns")

    def __configure_interior(self, *args):
      """Private function to configure the interior Frame."""
      # Resize the canvas scrollregion to fit the entire frame
      (size_x, size_y) = (self.interior.winfo_reqwidth(), self.interior.winfo_reqheight())
      self._canvas.config(scrollregion="0 0 {0} {1}".format(size_x, size_y))
      if self.interior.winfo_reqwidth() is not self._canvas.winfo_width():
          # If the interior Frame is wider than the canvas, automatically resize the canvas to fit the frame
          self._canvas.config(width=self.interior.winfo_reqwidth())

    def __configure_canvas(self, *args):
      if self.interior.winfo_reqwidth() is not self._canvas.winfo_width():
        self._canvas.configure(width=self.interior.winfo_reqwidth())

    def __mouse_wheel(self, event): self._canvas.yview_scroll(-1 * (event.delta // 100), "units")
    def resize_canvas(self, height=400, width=400): self._canvas.configure(width=width, height=height)


class TtkScale(ttk.Frame, WidgetWrapper):
  def __init__(self, parent=None, from_=0, to=1, variable=None, **kwargs):
    super().__init__(parent, class_="TickScale", padding=2)
    self.rowconfigure(0, weight=1); self.columnconfigure(0, weight=1)
    var = variable or tk.DoubleVar(self, 0)
    var.trace_add("write", self._increment)
    self._step = kwargs.pop("resolution", 0)
    self._showValue = kwargs.pop("showvalue", True)
    self._n = kwargs.pop("digits", None) # no implicit (-1) use
    self._tickInterv = max(kwargs.pop("tickinterval", 0), self._step) # useless rounding (if 0 <= self._digits < d) removed

    self._start = from_
    self._extent = to - from_
    self._nb_interv = int(self._extent / self._tickInterv)
    # adapt resolution, digits and tickinterval to avoid conflicting values
    prec = lambda n: -1 if n < 1e-6 else ("%f" %n).rstrip('0')[::-1].find('.')
    d = max(map(prec, [self._tickInterv, self._step, from_, to]))
    self._n = self._n or d; assert self._n >= 0
    self._fmt = "%.0f" if self._n == None else "%%.%df" %self._n

    WidgetWrapper.__init__(self, ttk.Scale(self, variable=var, from_=round(from_, self._n),to=round(to, self._n), **kwargs),
      {"showvalue":"_showValue", "resolution":"_step", "digits":"_n"})

    self._var = var
    self.isHor = str(self._wid.cget("orient")) == "horizontal"
    self._labelPos = kwargs.pop("labelpos", 'n' if self.isHor else 'w')
    self._tickPos = kwargs.pop("tickpos", 's' if self.isHor else 'w')
    self.tick_labels = []
    self._ticklabels = []

    # get slider length
    self._style_name = kwargs.get('style', '%s.TScale' % (str(self._wid.cget('orient')).capitalize()))
    self._sliderLength = ttk.Style(self).lookup(self._style_name, 'sliderlength', default=30)

    # showvalue
    self.label = ttk.Label(self, padding=1)
    self._reinit()
    self._wid.bind("<<ThemeChanged>>", lambda ev: self._reinit())
  def get(self): return self._var.get()
  def keys(self): return self._wkeys()
  def cget(self, key): return self._wcget(key)
  def configure(self, cnf={}, **kw): return self._wconfigure(cnf, kw)

  def _reinit(self):
    for it in self._ticklabels: it.destroy()
    self.label.place_forget()
    self._ticklabels.clear(); self.tick_labels.clear()

    if self._step > 0:
      from_ = self._wid.cget("from"); to = self._wid.cget("to")
      nb_steps = round((to - from_) / self._step)
      self._wid.configure(to=from_ + nb_steps*self._step)
      self._extent = to-from_

    self._init_horizontal() if self.isHor else self._init_vertical()
    self._wid.lift()
    self._update_slider_length()

  def _valPixels(self, value):
    dist_slider = self._wid.winfo_width() if self.isHor else self._wid.winfo_height()
    return ((value-self._start) / self._extent) * (dist_slider-self._sliderLength) + self._sliderLength / 2

  def displayValue(self, value):
    if not self._showValue: return
    self.label.configure(text=self._fmt %(self._roundInterval(value)))
    if not self.isHor:
      y = self._valPixels(float(value))
      self.label.place_configure(y=y)
      return
    # position (in pixel) of the center of the slider
    x = self._valPixels(float(value))
    # pay attention to the borders
    half_width = self.label.winfo_width() / 2
    self.label.place_configure(x=max(TtkScale._bounds(x, self._wid.winfo_width(), half_width), half_width))

  def _reconfig(self):
    """Redisplay the ticks and the label so that they adapt to the new size of the scale."""
    self.displayValue(self._wid.get())
    self.place_ticks() # auto returned not-required

  def createLabel(self, i, anchor, **kwargs): # one shadow another... should be removed
    tick = self._start + i * self._tickInterv
    lbl = ttk.Label(self, style=self._style_name + ".TLabel", text=self._fmt %tick)
    lbl.place(in_=self._wid, bordermode="outside", anchor=anchor, **kwargs)
    self.tick_labels.append((tick, lbl))
    self._ticklabels.append(lbl)
  def place_ticks(self):
    if self._tickInterv == 0: return
    if not self.isHor:
      for (tick, label) in self.tick_labels:
        y = self._valPixels(tick)
        label.place_configure(y=y)
      return
    (tick, label) = self.tick_labels[0]
    w_me = self._wid.winfo_width()
    sval = lambda: self._valPixels(tick)
    w_half = lambda: TtkScale._wHalf(label)
    labelX = lambda x: label.place_configure(x=x)
    # first tick
    labelX(max(sval(), w_half()) )
    # ticks in the middle
    for (tick, label) in self.tick_labels[1:-1]:
        x = self._valPixels(tick)
        label.place_configure(x=x)
    # last tick
    (tick, label) = self.tick_labels[-1]
    labelX(TtkScale._bounds(sval(), w_me, w_half()) )

  @staticmethod
  def _bounds(n, max, sub):
    return max-sub if n+sub > max else n
  @staticmethod
  def _wHalf(e): return e.winfo_width() / 2
  def _roundInterval(self, v): return self._step * round(v/self._step)
  def _increment(self, *args):
    '''Move the slider only by increment given by resolution.'''
    value = self._var.get()
    if self._step != 0:
      value = self._start + self._roundInterval(value - self._start)
      self._var.set(value)
    self.displayValue(value)

  def _update_slider_length(self):
    if self._wid.identify(2, 2) == "": # not displayed yet so we cannot measure the length of the slider
      self.after(10, self._update_slider_length)
    else:
      dist = self._wid.winfo_width() if self.isHor else self._wid.winfo_height()
      # find the first pixel of the slider
      i = 0 #v increment i until the pixel (2, i) belongs to the slider
      while i < dist and 'slider' not in self._wid.identify(i, 2): i += 1
      j = i  #v increment j until the pixel (2, j) no longer belongs to the slider
      while j < dist and 'slider' in self._wid.identify(j, 2): j += 1
      # so the value of the sliderlength from the style is used
      self._sliderLength = (j - i) if (j != i) else ttk.Style(self).lookup(self._style_name, 'sliderlength', default=30)
    self._reconfig() # update ticks and label placement

  def _labelMaxBetween(self, op, get):
    a = get(self.label)
    op(self.label); self.update_idletasks()
    return max(a, get(self.label))
  def _padPair(self, tick_pos, d, d_slider, pad1, pad2):
    if d_slider <= d: return
    pad = (d - d_slider) // 2
    if self._tickInterv != 0:
      if self._tickPos == tick_pos:
        return (pad, pad2)
      else:
        return (pad1, pad)
    else:
        return (pad, pad)
  def _place(self, anchor, **kwargs):
    self.label.place(in_=self._wid, bordermode='outside', anchor=anchor, **kwargs)
    self.update_idletasks()
  def _init_vertical(self):
    self._wid.grid(row=0, sticky='ns')
    padx1, padx2 = 0, 0
    pady1, pady2 = 0, 0
    if self._showValue:
      place = self._place
      labelCfg = lambda it: it.configure(text=self._fmt %(self._start + self._extent))
      width = lambda it: it.winfo_width()
      self.label.configure(text=self._fmt %self._start)
      if self._labelPos == 'w':
        place("e", relx=0, y=0)
        padx1 = self._labelMaxBetween(labelCfg, width)
      elif self._labelPos == 'e':
        place("w", relx=1, y=1)
        padx2 = self._labelMaxBetween(labelCfg, width)
      else: # self._labelPos in ['n', 's']:
        if self._labelPos == 'n':
            anchor = 's'; rely = 0
            pady1 = self.label.winfo_reqheight()
        else:
            anchor = 'n'; rely = 1
            pady2 = self.label.winfo_reqheight()
        place(anchor, relx=0.5, rely=rely)
        w = self._labelMaxBetween(labelCfg, width)
        ws = self._wid.winfo_reqwidth()
        (padx1, padx2) = self._padPair("e", w, ws, padx1, padx2)
    # ticks
    padx1_2, padx2_2 = 0, 0
    if self._tickInterv != 0:
      if self._tickPos == 'w':
        for i in range(self._nb_interv+1):
          self.createLabel(i, "e", x=-(1+padx1), y=0)
          self.update_idletasks()
          padx1_2 = max(self._ticklabels[i].winfo_width(), padx1_2)
      elif self._tickPos == 'e':
        w = self._wid.winfo_reqwidth()
        for i in range(self._nb_interv+1):
          self.createLabel(i, "w", x=w+1+padx2, y=0)
          self.update_idletasks()
          padx2_2 = max(self._ticklabels[i].winfo_width(), padx2_2)
    self._wid.grid_configure(padx=(padx1 + padx1_2 + 1, padx2 + padx2_2 + 1), pady=(pady1, pady2))

  def _init_horizontal(self):
    self._wid.grid(row=0, sticky='ew')
    padx1, padx2 = 0, 0
    pady1, pady2 = 0, 0
    if self._showValue:
      place = self._place
      labelCfg = lambda it: it.configure(text=self._fmt %(self._start + self._extent))
      reqwidth = lambda it: it.winfo_reqwidth()
      self.label.configure(text=self._fmt %(self._start))
      if self._labelPos == 'n':
        place("s", rely=0, x=0)
        pady1 = self.label.winfo_reqheight()
      elif self._labelPos == 's':
        self.label.place("n", rely=1, x=0)
        pady2 = self.label.winfo_reqheight()
      else: # self._labelPos in ['w', 'e']:
        padx = self._labelMaxBetween(labelCfg, reqwidth)
        if self._labelPos == 'w':
            anchor = 'e'; relx = 0
            padx1 = padx
        else:
            anchor = 'w'; relx = 1
            padx2 = padx
        place(anchor, relx=relx, rely=0.5)
        h = self.label.winfo_reqheight() # reqheight, so no update.
        hs = self._wid.winfo_reqheight()
        (pady1, pady2) = self._padPair("n", h, hs, pady1, pady2)
    # ticks
    pady1_2, pady2_2 = 0, 0
    if self._tickInterv != 0:
      h = self._wid.winfo_reqheight()
      if self._tickPos == 's':
        for i in range(self._nb_interv+1): self.createLabel(i, "n", x=0, y = h+pady2+1)
        pady2_2 = self._ticklabels[-1].winfo_reqheight()
      elif self._tickPos == 'n':
        for i in range(self._nb_interv+1): self.createLabel(i, "s", x=0, y= -(1+pady1))
        pady1_2 = self._ticklabels[-1].winfo_reqheight()
      self.update_idletasks()
    self._wid.grid_configure(pady=(pady1 + pady1_2, pady2 + pady2_2), padx=(padx1, padx2))

from tkgui import TickScale
if __name__ == '__main__':
    root = tk.Tk()
    root.geometry('400x300')
    style = ttk.Style(root)
    style.configure('my.Horizontal.TScale', sliderlength=10)

    s1 = tk.Scale(root, orient='horizontal', tickinterval=0.2, from_=-1, 
                  to=1, showvalue=True, resolution=0.1,  sliderlength=10)
    s2 = TtkScale(root, style='my.Horizontal.TScale', orient='horizontal', 
                  resolution=0.2, tickinterval=0.1, from_=-1, to=1, showvalue=True, 
                  digits=1)
    s3 = TickScale(root, style='my.Horizontal.TScale', orient='horizontal', 
                  resolution=0.2, from_=-1, to=1, showvalue=True, 
                  digits=1)
    s4 = ttk.Scale(root, orient='horizontal', from_=-1, to=1)

    s1v = tk.Scale(root, orient='vertical', tickinterval=0.2, from_=-1, 
                  to=1, showvalue=True, resolution=0.1,  sliderlength=10)
    s2v = TtkScale(root, style='my.Vertical.TScale', orient='vertical', 
                  resolution=0.2, from_=-1, to=1, showvalue=True, 
                  digits=1, tickinterval=0.5)
    s3v = TickScale(root, style='my.Vertical.TScale', orient='vertical', 
                  resolution=0.2, from_=-1, to=1, showvalue=True, 
                  digits=1, tickinterval=0.5)
    s4v = ttk.Scale(root, orient='vertical', from_=-1, to=1)

    print(s2v.keys())
    ttk.Label(root, text='tk.Scale').pack()
    s1.pack(fill='x'); s1v.pack(fill='x')
    ttk.Label(root, text='ttk.Scale').pack()
    s2.pack(fill='x'); s2v.pack(fill='x')
    ttk.Label(root, text='TickScale').pack()
    s3.pack(fill='x'); s3v.pack(fill='x')
    ttk.Label(root, text='ttk orig Scale').pack()
    s4.pack(fill='x'); s4v.pack(fill='x')

    root.mainloop()

class TtkScale1(ttk.Frame, WidgetWrapper):
    def __init__(self, master=None, variable=None, **kwargs):
      super().__init__(master)
      var = variable or tk.DoubleVar(self, kwargs["from_"])
      self._step = kwargs.pop("resolution", 0)
      self._showValue = kwargs.pop("showvalue", True)
      self._digits = kwargs.pop("tick_format", "%.0f")
      WidgetWrapper.__init__(self, ttk.Scale(self, variable=var, **kwargs), {"showvalue":"_showValue", "resolution":"_step", "tick_format":"_digits"})
      self.columnconfigure(0, weight=1)
      self._var = var; self._var.trace_add("write", self._increment)
      self._start = var.get()
      self._extent = kwargs["to"] - kwargs["from_"]

      style = ttk.Style(self) # slider length.
      self._styleName = kwargs.get("style", "%s.TScale" %str(self._wid.cget("orient")).capitalize() )
      self._w_slider = style.lookup(self._styleName, "sliderlength", default=30)
        
    def convert_to_pixels(self, value):
      return ((value - self._start)/ self._extent) * (self._wid.winfo_width()- self._w_slider) + self._w_slider / 2

    def _roundInterval(self, v): # or round(a/b) *b
      return round(v/self._step) * self.step
    def _increment(self, *args):
      '''Move the slider only by increment given by resolution.'''
      value = self._var.get()
      self._var.set(self._start + self._roundInterval(value))
      self.display_value(value)

    def display_value(self, value):
      if not self._showValue: return
      value = float(value)
      w_me = self._wid.winfo_width()
      h_me = self._wid.winfo_height()
      dist = self._valPixels(value) # position (in pixel) of the center of the slider
      self.label.configure(text=self._digits %self._roundInterval(value))
      # pay attention to the borders
      self.label.place_configure(x=TtkScale._bounds(dist, w_me, TtkScale._wHalf(self.label)))
    @staticmethod
    def _bounds(n, max, sub):
      return max-sub if n+sub > max else n
    @staticmethod
    def _wHalf(e): return e.winfo_width() / 2
    def place_ticks(self):
      def createLabel(i): # one shadow another... should be removed
        lbl = ttk.Label(self, text=self._digits %self.ticks[i])
        lbl.place(in_=self._wid, bordermode="outside", x=0, rely=1, anchor="n")
        return lbl
      # first tick 
      tick = self.ticks[0]; label = createLabel(0)
      w_me = self._wid.winfo_width()
      sval = lambda: self._valPixels(tick)
      w_half = lambda: TtkScale._wHalf(label)
      labelX = lambda x: label.place_configure(x=x)
      labelX(max(sval(), w_half()) )
      # ticks in the middle
      for (i, tick) in enumerate(self.ticks[1:-1]):
        createLabel(1+i).place_configure(x=sval())
      # last tick
      tick = self.ticks[-1]; label = createLabel(len(self.ticks)-1)
      labelX(TtkScale._bounds(sval(), w_me, w_half()) )

