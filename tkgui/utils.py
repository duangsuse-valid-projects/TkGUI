import threading
import queue
import traceback
from sys import stderr

from tkinter import Tk, Toplevel, PhotoImage
from .codegen import Codegen
guiCodegen = Codegen()

from platform import system as platformName #< for startFile
from subprocess import call as startSubProcess
def startFile(path:str):
  name = platformName()
  def run(prog): startSubProcess((prog, path))
  if name == "Darwin": run("open")
  elif name == "Windows":
    __import__("os").startfile(path)
  else: run("xdg-open") # POSIX

import os.path
def _getAssestDir():
  return os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), "assets"))

def _openIcon(name):
  return PhotoImage(name, {"file": os.path.join(_getAssestDir(), name)})

def thunkify(op, kw_callback="callback", *args, **kwargs):
  '''make a function with named callback param as thunk'''
  def addCb(cb, kws):
    kws[kw_callback] = cb
    return kws
  return lambda cb: op(*args, **addCb(kwargs, cb))

def thunkifySync(op, *args, **kwargs):
  def callAsync(cb):
    threading.Thread(target=lambda args1, kwargs1: cb(op(*args1, **kwargs1)), args=(args, kwargs) ).start()
  return callAsync

MSG_CALL_FROM_THR_MAIN = "call from main thread."
MSG_CALLED_TWICE = "called twice"
NOT_THREADSAFE = RuntimeError("call initLooper() first")
TCL_CMD_POLLER = "teek_init_threads_queue_poller"

class BackendEnum():
  def __init__(self, name:str, module_name:str):
    self.name=name;self.module_name=module_name
  def __eq__(self, other): return other.name == self.name
  def __hash__(self): return self.name.__hash__()
  def isAvaliable(self):
    try: __import__(self.module_name); return True
    except ImportError: return False
  def use(self):
    global guiBackend
    if self.isAvaliable(): guiBackend = self
    else: next(filter(BackendEnum.isAvaliable, Backend.fallbackOrder)).use()
  def isUsed(self):
    global guiBackend; return guiBackend == self

class Backend:
  Tk = BackendEnum("tk", "tkinter")
  TTk = BackendEnum("ttk", "tkinter.ttk")
  ThemedTk = BackendEnum("themedtk", "ttkthemes")
  Wx = BackendEnum("wx", "wx")
  GTK = BackendEnum("gtk", "gi")
  fallbackOrder = [GTK, Wx, ThemedTk, TTk, Tk]
guiBackend = Backend.TTk

class irange:
  '''inclusive (float) range (first, last)+step, (start/stop fields) compatible with range
  when used as irange(n), first defaults to 1, and last is inclusive!
  '''
  def __init__(self, first, last=None, step=1):
    if step == 0: raise ValueError("step == 0")
    self.first = first if last != None else 1; self.last = last if last != None else first; self.step = step
    self.start = self.first; self.stop = self.last+(1 if self.step > 0 else -1)
  def __repr__(self):
    rep = "irange(%s, %s" %(self.first, self.last)
    if self.step != 1: rep += ", %s" %self.step
    return rep+")"
  __str__ = __repr__
  def __eq__(self, other): return self.first == other.first and self.last == other.last and self.step == other.step
  def __iter__(self):
    if isinstance(self.first, int) and isinstance(self.last, int) and isinstance(self.step, int):
      return iter(range(self.start, self.stop, self.step))
    return irange._iterator(self)
  def __reversed__(self):
    return irange(self.last, self.first, -self.step)
  class _iterator:
    def __init__(self, rng:"irange"):
      self._rng = rng
      self._i = rng.first
    def __next__(self):
      i = self._i; print(i)
      stop = (i > self._rng.last) if (self._rng.step > 0) else (i < self._rng.last) # count down
      if stop: raise StopIteration()
      self._i = i + self._rng.step
      return i

class EventCallback:
  """An object that calls functions. Use [bind] / [__add__] or [run]"""
  def __init__(self):
    self._callbacks = []

  class CallbackBreak(Exception): pass
  callbackBreak = CallbackBreak()
  @staticmethod
  def stopChain(): raise EventCallback.callbackBreak

  def isIgnoredFrame(self, frame):
    '''Is a stack trace frame ignored by [bind]'''
    return False
  def bind(self, op, args=(), kwargs={}):
    """Schedule `callback(*args, **kwargs) to [run]."""
    stack = traceback.extract_stack()
    while stack and self.isIgnoredFrame(stack[-1]): del stack[-1]
    stack_info = "".join(traceback.format_list(stack))
    self._callbacks.append((op, args, kwargs, stack_info))
  def __add__(self, op):
    self.bind(op); return self

  def remove(self, op):
    """Undo a [bind] call. only [op] is used as its identity, args are ignored"""
    idx_callbacks = len(self._callbacks) -1 # start from 0
    for (i, cb) in enumerate(self._callbacks):
      if cb[0] == op:
        del self._callbacks[idx_callbacks-i]
        return

    raise ValueError("not bound: %r" %op)

  def run(self) -> bool:
    """Run the connected callbacks(ignore result) and print errors. If one callback requested [stopChain], return False"""
    for (op, args, kwargs, stack_info) in self._callbacks:
      try: op(*args, **kwargs)
      except EventCallback.CallbackBreak: return False
      except Exception:
        # it's important that this does NOT call sys.stderr.write directly
        # because sys.stderr is None when running in windows, None.write is error
        (trace, rest) = traceback.format_exc().split("\n", 1)
        print(trace, file=stderr)
        print(stack_info+rest, end="", file=stderr)
        break
    return True

class FutureResult:
  '''pending operation result, use [getValue] / [getValueOr] to wait'''
  def __init__(self):
    self._cond = threading.Event()
    self._value = None
    self._error = None

  def setValue(self, value):
    self._value = value
    self._cond.set()

  def setError(self, exc):
    self._error = exc
    self._cond.set()

  def getValueOr(self, on_error):
    self._cond.wait()
    if self._error != None: on_error(self._error)
    return self._value
  def getValue(self): return self.getValueOr(FutureResult.rethrow)
  def fold(self, done, fail):
    self._cond.wait()
    return done(self._value) if self._error == None else fail(self._error)
  @staticmethod
  def rethrow(ex): raise ex

class EventPoller:
  '''after-event loop operation dispatcher for Tk'''
  def __init__(self):
      assert threading.current_thread() is threading.main_thread()
      self._main_thread_ident = threading.get_ident() #< faster than threading.current_thread()
      self._init_looper_done = False
      self._call_queue = queue.Queue() # (func, args, kwargs, future)
      self.tk:Tk; self.on_quit:EventCallback
  def isThreadMain(self): return threading.get_ident() == self._main_thread_ident
  def initLooper(self, poll_interval_ms=(1_000//20) ):
      assert self.isThreadMain(), MSG_CALL_FROM_THR_MAIN
      assert not self._init_looper_done, MSG_CALLED_TWICE #< there is a race condition, but just ignore this

      timer_id = None
      def poller():
        nonlocal timer_id
        while True:
          try: item = self._call_queue.get(block=False)
          except queue.Empty: break

          (func, args, kwargs, future) = item
          try: value = func(*args, **kwargs)
          except Exception as ex: future.setError(ex)
          else: future.setValue(value)

        timer_id = self.tk.tk.call("after", poll_interval_ms, TCL_CMD_POLLER)
      self.tk.tk.createcommand(TCL_CMD_POLLER, poller)

      def quit_cancel_poller():
        if timer_id != None: self.tk.after_cancel(timer_id)

      self.on_quit += quit_cancel_poller

      poller()
      self._init_looper_done = True

  def callThreadSafe(self, op, args, kwargs) -> FutureResult:
    if self.isThreadMain():
      return op(*args, **kwargs)

    if not self._init_looper_done: raise NOT_THREADSAFE

    future = FutureResult()
    self._call_queue.put((op, args, kwargs, future))
    return future
