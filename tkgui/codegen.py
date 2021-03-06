from traceback import extract_stack #codegen autoname

class SyntaxFmt: #singleton
  '''some language-sepcific syntax formatters'''
  @staticmethod
  def pyArg(params):
    '''arg1, arg2, kw1=kw1v, kw2=kw2v'''
    (args, kwargs) = params
    sb = []
    sb.extend(args)
    for (name, v) in kwargs.items(): sb.append("%s=%s" %(name, v) )
    return ", ".join(sb)
  @staticmethod
  def pyOpRef(op):
    def joinLast(rsep, sep, xs):
      part = sep.join(xs[:-1])
      return xs[0] if len(xs) < 2 else part+rsep+xs[-1]
    valid = op.__qualname__.replace(".", "").isidentifier()
    return joinLast(".", "_" if hasattr(op, "__self__") else ".", op.__qualname__.split(".")) if valid else None #e.g. lambda, check not serious
  argList = pyArg
  value = repr
  list = lambda xs: "[%s]" %", ".join(xs)
  assign = lambda name, x: "%s = %s" %(name, x)
  nameRef = lambda name: name
  opRef = lambda op: SyntaxFmt.pyOpRef(op)
  call = lambda op, params: "%s(%s)" %(op.__qualname__, SyntaxFmt.argList(params))
  callNew = lambda ty, params: "%s(%s)" %(ty.__qualname__, SyntaxFmt.argList(params))
  invoke = lambda x, op, params: "%s.%s(%s)" %(x, op.__name__, SyntaxFmt.argList(params))
  setAttr = lambda x, name, v: "%s.%s = %s" %(x, name, v)
  setItem = lambda x, key, v: "%s[%s] = %s" %(x, SyntaxFmt.value(key), v)
  getAttr = lambda x, name: "%s.%s" %(x, name)
  tfNil = ("True", "False", "None")
  lineSep = "\n"
  autoExpr = lambda x: None
  specialCaller = "createWidget"
  defaultNameMap = {}
fmt = SyntaxFmt

def indexOfLast(p, xs):
  idxPart = 0; idxXs = len(xs) -1
  for (i, x) in enumerate(reversed(xs)):
    if not p(x): idxPart = idxXs-i +1; break
  return idxPart

class Codegen:
  '''Python stmt/expression construction&execution result provider,
    so adding side-effects(generate code) besides values are possible.
    The code generator generally uses value-name substitution,
    to provide generated-file-wise argument, use [named] method.
    NOTE: non-flat syntax structures are NOT supported, the result is mainly post-order tree walk'''
  useDebug = False
  def __init__(self):
    super().__init__()
    self.isEnabled = False; self._isAlwaysRegResult = False
    self._sb = []
    self._names = id_dict(); self._exprs = id_dict()
    self._autoNamed = id_set()
    self._externNames = Codegen._initConstNames()
    self._recvRefs = id_dict()
  @staticmethod
  def _initConstNames():
    (t,f,nil) = fmt.tfNil
    return id_dict({True: t, False:f, None: nil})
  def clear(self, drop_state=True):
    self._sb.clear()
    if not drop_state: return
    self._names.clear(); self._exprs.clear()
    self._autoNamed.clear()
    self._externNames = Codegen._initConstNames()
    self._recvRefs.clear() #invoke&assign
  def _write(self, text): self._sb.append(text)
  def write(self, get_text):
    if not self.isEnabled: return
    text = get_text()
    self._write(text)
  def getCode(self):
    code = fmt.lineSep.join(self._sb)
    if Codegen.useDebug: print("\tCodeDump:"); print(code)
    return code
  def regResult(self): return Codegen.AlwaysRegResult(self)
  class AlwaysRegResult:
    def __init__(self, outter):
      self._outter = outter
    def __enter__(self): self._outter._isAlwaysRegResult = True
    def __exit__(self, *args): self._outter._isAlwaysRegResult = False

  @staticmethod
  def nextName(name):
    '''a, a1, a2, ...'''
    if name == "": return "_"
    if not name[-1].isnumeric(): return "%s1" %name
    else:
      idxNPart = indexOfLast(str.isnumeric, name)
      return "%s%d" %(name[:idxNPart], 1+int(name[idxNPart:]))
  def _allocName(self, name):
    qname = name # find, could be tailrec
    while qname in self._names.values(): qname = Codegen.nextName(qname)
    return qname
  def named(self, name, x, is_extern=False):
    '''this may give an value a name, if [x] is provided before, then [nextName] is used. see [nv]'''
    self._names[x] = self._allocName(name)
    if is_extern:
      assert name not in self._externNames, "extern duplicate: %s" %name
      self._externNames[x] = name
    return x
  def newName(self, name, x):
    '''give [x] a new name'''
    self.named(name, x)
    return self._names.get(x)

  def _nvUnwrap(self, x):
    if isinstance(x, list): return fmt.list([self.nv(it) for it in x])
    return None
  def nv(self, x):
    '''name a expression result, note [named] could not be used twice on the same value,
      or inconsistence nameRef (e.g. created@callNew foo, re-named to xxx later) will be wrote'''
    def nameRef():
      kst = self._externNames.get(x)
      if kst != None: return kst
      nam = self._names.get(x)
      if nam != None: nam = fmt.nameRef(nam)
      return nam or self._nvUnwrap(x) or fmt.value(x)
    expr = self._exprs.get(x)
    if expr == None:
      expr = fmt.autoExpr(x)
      if expr != None: self._autoNamed.add(x)
    if expr != None and expr != "+":
      name = self._names.get(x)
      if name == None and (x in self._autoNamed):
        name = self.newName("%s_1" %type(x).__name__.lower(), x)
      if name != None and x not in self._externNames:
        code = fmt.assign(name, expr)
        self._write(code)
        self._recvRefs.getOrPut(x, list).append(code)
      self._exprs[x] = "+"
    return nameRef()
  def _regResult(self, res, get_code):
    shouldDo = self._isAlwaysRegResult
    if shouldDo: shouldDo = self.isEnabled; self.isEnabled = True #shorten.
    if self.isEnabled:
      if res != None: # python's default func result
        code = get_code()
        self._exprs[res] = code
        self._autoNamed.add(res)
      else: self.write(get_code)
    if self._isAlwaysRegResult: self.isEnabled = shouldDo
  def _name(self, args, kwargs):
    '''name those actual param values'''
    namArgs = [self.nv(arg) for arg in args]
    namKwargs = {}
    for (key, x) in kwargs.items():
      if callable(x):
        qname = fmt.opRef(x)
        if qname != None: namKwargs[key] = qname
      else: namKwargs[key] = self.nv(x)
    return (namArgs, namKwargs)
  def defaultName(self, callee, x):
    return fmt.defaultNameMap.get(callee) or callee

  def call(self, op, *args, **kwargs):
    res = op(*args, **kwargs)
    self._regResult(res, lambda: fmt.call(op, self._name(args, kwargs)))
    return res
  def callNew(self, ctor, *args, **kwargs):
    insta = ctor(*args, **kwargs)
    self._regResult(insta, lambda: fmt.callNew(ctor, self._name(args, kwargs)))
    tb = extract_stack(limit=3) # determine whatif result is a GUI widget
    (caller, callee) = [it[2] for it in tb[:-1]] #drop this "call"'s frame, get func name(2)
    if caller == fmt.specialCaller:
      deftName = self.defaultName(callee, insta)
      if deftName != None: self.named(deftName, insta) # scope[value] may rewrote to new name
    return insta
  def invoke(self, x, op_name, *args, **kwargs):
    opBound = x.__getattribute__(op_name)
    res = opBound(*args, **kwargs)
    def regCode():
      code = fmt.invoke(self.nv(x), opBound, self._name(args, kwargs))
      self._recvRefs.getOrPut(x, list).append(code)
      return code
    self._regResult(res, regCode)
    return res
  def setAttr(self, x, name, v):
    x.__setattr__(name, v)
    self.write(lambda: fmt.setAttr(self.nv(x), name, self.nv(v)) )
  def setItem(self, x, key, v):
    x[key] = v
    self.write(lambda: fmt.setItem(self.nv(x), key, self.nv(v)) )
  def getAttr(self, x, name):
    '''return value of x.name, also denotes it is already initialized so don't generate assignment again'''
    attr = x.__getattribute__(name)
    self.named(fmt.getAttr(self.nv(x), name), attr, is_extern=True)
    refs = self._recvRefs.get(attr)
    if refs != None:
      for ref in refs: self._sb.remove(ref)

import struct
import json
import sys
class TupleSerialize:
  def __init__(self, type, pack_fmt, destruct_names):
    '''[convert]: pair of callable (fmt, from, into) bytes called to transform _ position in [pack_fmt], indexConvert[i] (dump,load)'''
    self.type = type
    self.memberNames = destruct_names
    self._reprIndices = []
    packFmts = list(pack_fmt)
    for (i, c) in enumerate(packFmts):
      if c == '^': packFmts[i] = 's'; self._reprIndices.append(i)
    self.packFmt = "".join(packFmts).replace("s", "%ds")
    nStr = packFmts.count("s")
    self._packFmtNSize = nStr*struct.calcsize("I")
    self._packFmtNF = 'I'*nStr
    self.indexConvert = [None for _ in range(len(pack_fmt))]
  def _transform(self, data, op_index, is_load):
    proc = (self._postprocess if is_load else self._preprocess)
    for i in self._reprIndices:
      dat = data[i]; isList = isinstance(dat, list)
      if isinstance(dat, tuple):
        dat=list(dat); dat.append("T")
      elif isList: dat.append("_") # support tuple/list, reduce memory use
      def load():
        obj = json.loads(dat)
        if isinstance(obj, list):
          xs = obj[:-1]; p = obj[-1]
          return tuple(xs) if p == "T" else xs
        return obj
      data[i] = proc(load() if is_load else json.dumps(dat, ensure_ascii=False, separators=(",",":")), i)
      if isList: del dat[-1]
  def _preprocess(self, v, i):
    op = self.indexConvert[i]
    if op != None: return op[0](v)
    if isinstance(v, str): return bytes(v, "utf8")
    return v
  def _postprocess(self, v, i):
    op = self.indexConvert[i]
    if op != None: return op[1](v)
    if isinstance(v, bytes): return str(v, "utf8")
    return v
  def dumpItems(self, v):
    data = [self._preprocess(v.__getattribute__(name), i) for (i, name) in enumerate(self.memberNames)]
    self._transform(data, 2, False)
    return data
  def loadItems(self, stm):
    data = [self._postprocess(v, i) for (i, v) in enumerate(stm)]
    self._transform(data, 1, True)
    return data

  def dumps(self, v):
    isStr = lambda it: isinstance(it, (str, bytes))
    data = self.dumpItems(v)
    lens = []; i = 0; i_len = 0
    while i < len(data):
      dat = data[i]
      if isStr(dat):
        n = len(dat); lens.append(n)
        #data.insert(i, n); i+=1 #collecting sizes is not good idea, but struct does not support sized types
        data.insert(i_len, n); i_len+=1
        i += 1 # skip dat
      i += 1
    return struct.pack(self._packFmtNF + self.packFmt %tuple(lens), *data)
  def loads(self, bytes):
    n = self._packFmtNSize
    lens = struct.unpack(self._packFmtNF, bytes[:n])
    data = struct.unpack(self.packFmt %lens, bytes[n:])
    return self.type(*self.loadItems(data))

_code = type(compile("1", "<get-type(code)>", "eval"))
_codeMembers = "argcount kwonlyargcount nlocals stacksize flags code consts names varnames filename name firstlineno lnotab freevars cellvars".split(" ")
_codeMembersPY2 = list(_codeMembers); _codeMembersPY2.remove("kwonlyargcount")
_isPY3 = (sys.version_info.major == 3)

codeSer = TupleSerialize(_code, "i%siiis^ssssisss" %("i" if _isPY3 else ""), ["co_%s" %it for it in (_codeMembers if _isPY3 else _codeMembersPY2)])
def _initCodeSer(dist, sep=",", enc="utf8"):
  itself = (lambda x: x, lambda x: x)
  nameList = (lambda v: bytes(sep.join(v), enc), lambda v: tuple(str(v, enc).split(sep)) if len(v) != 0 else tuple())
  codeSer.indexConvert[dist+5] = itself
  codeSer.indexConvert[dist+12] = itself
  for i in map(lambda i: dist+i, [7,8,13,14]): codeSer.indexConvert[i] = nameList
_initCodeSer(0 if _isPY3 else -1)

# boilerplates
class id_dict(dict):
  '''try to store objects, use its identity to force store unhashable types'''
  def get(self, key): return super().get(id(key))
  def getOrPut(self, key, get_value): return super().setdefault(id(key), get_value())
  def __getitem__(self, key): return super().__getitem__(id(key))
  def __setitem__(self, key, value): return super().__setitem__(id(key), value)
  def __delitem__(self, key): return super().__delitem__(id(key))
  def __contains__(self, key): return super().__contains__(id(key))
class id_set(set):
  '''same as [id_dict]'''
  def add(self, value): super().add(id(value))
  def remove(self, value): super().remove(id(value))
  def __contains__(self, value): return super().__contains__(id(value))

