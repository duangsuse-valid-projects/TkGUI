from argparse import ArgumentParser, FileType
from json import loads, dumps

from tkinter import Menu

import threading, time, requests
import os

from tkgui.utils import startFile, Backend
from tkgui.utils import guiCodegen as c
Backend.TTk.use()

from tkgui.ui import TkGUI, TkWin, nop, Timeout, callThreadSafe, thunkifySync, delay, runAsync, rescueWidgetOption, bindYScrollBar, bindXScrollBar
from tkgui.widgets import MenuItem, TreeWidget
import tkgui.widgets as _

app = ArgumentParser(prog="hachi-groups", description="GUI tool for recording lyric sentences with hachi")
app.add_argument("music", type=FileType("r"), nargs="*", help="music BGM to play")
app.add_argument("-seek-minus", type=float, default=3.0, help="back-seek before playing the sentence")
app.add_argument("-mix-multi", action="store_true", default=False, help="give multi-track mix")
app.add_argument("-o", type=str, default="mix.mid", help="mixed output file")
app.add_argument("-replay", type=FileType("r"), default=None, help="MIDI File to replay")
app.add_argument("-import", type=str, default=None, help="import a sentence list")

#GUI: ($lyric @ $n s .Rec-Edit .Play)[] (input-lyric @ input-n s .Add .Remove_Last) (input-JSON .Mix .Delete .Export) (-) ($music) (slider-volume)
rescueWidgetOption["relief"] = lambda _: None

class GUI(TkGUI):
  def __init__(self):
    super().__init__()
    z = self.shorthand
    self.a=z.var(str, "some"); self.b=z.var(bool); self.c=z.var(int)
    c.getAttr(self, "a"); c.getAttr(self, "b"); c.getAttr(self, "c")
  def up(self):
    self.a.set("wtf")
    self.ui.removeChild(self.ui.lastChild)
    a=GUI.ThreadDemo()
    a.run("Thread Demo", compile_binding={"GUI_ThreadDemo":a})
  def pr(self):
    print(self.c.get())
    self.ui.removeChild(self.ui.childs[5])
  def addChild(self): self.ui.appendChild(_.text("hhh"))
  def layout(self):
    z = self.shorthand
    return _.verticalLayout(
      _.button("Yes", self.quit),
      _.text(self.a),
      _.button("Change", self.up),
      _.horizontalLayout(_.text("ex"), _.text("wtf"), _.button("emmm",self.addChild), _.text("aa")),
      _.input("hel"),
      _.separator(),
      _.withScroll(z.vert, z.by("ta", _.textarea("wtf"))),
      z.by("ah", _.text("ah")),
      _.checkBox("Some", self.b),
      _.horizontalLayout(_.radioButton("Wtf", self.c, 1, self.pr), _.radioButton("emm", self.c, 2, self.pr)),
      _.horizontalLayout(
        z.by("sbar", _.scrollBar(z.vert)),
        _.verticalLayout(
          z.by("lbox", _.listBox(("1 2 3  apple juicy lamb clamp banana  "*20).split("  "), z.chooseMulti)),
          z.by("hsbar", _.scrollBar(z.hor))
        )
      ),
      _.withScroll(z.both, z.by("box", _.listBox(("1 2 3  apple juicy lamb clamp banana  "*20).split("  ")))),
      _.comboBox(self.a, "hello cruel world".split(" ")),
      _.spinBox(range(0, 100+1, 10)),
      _.slider(range(0, 100+1, 2), orient=z.hor),
      _.button("hello", self.run1),
      _.button("split", self.run2),
      _.menuButton("kind", _.menu(MenuItem.CheckBox("wtf", self.b), MenuItem.RadioButton("emm", self.c, 9)), relief=z.raised),
      _.labeledBox("emmm", _.button("Dangerous", self.run3))
    )
  def run1(self): GUI.Layout1().run("Hello", compile_binding={"GUI":GUI})
  def run2(self): GUI.SplitWin().run("Split", compile_binding={})
  def run3(self): print(self.ta.marker["insert"])
  def setup(self):
    z = self.shorthand
    bindYScrollBar(self.lbox, self.sbar)
    bindXScrollBar(self.lbox, self.hsbar)
    themes = self.listThemes()
    themez = iter(themes)
    self.ah["text"] = ",".join(themes)
    def nextTheme(event):
      nonlocal themez
      try: self.theme = next(themez)
      except StopIteration:
        themez = iter(themes)
    self.ah.bind(z.Events.click, nextTheme)
    self.ah.bind(z.Events.mouseR, z.makeMenuPopup(_.menu(*[MenuItem.named(it, nop) for it in "Cut Copy Paste Reload".split(" ")], MenuItem.sep, MenuItem.named("Rename", nop))))
    self.initLooper()

  class Layout1(TkWin):
    def layout(self):
      menubar = _.menu(self.tk,
        MenuItem.named("New", nop),
        MenuItem.named("Open", GUI.Layout1.run1),
        MenuItem.SubMenu("Help", [MenuItem.named("Index...", nop), MenuItem.sep, MenuItem.named("About", nop)])
      ) # probably bug: menu (label='Open', command=GUI.Layout1.run1) works no matter command is correct or not
        # possible: win.tk uses attribute assign(when getCode() ) bound to created menu and it's reused
      self.setMenu(menubar)
      self.setSizeBounds((200,100))
      z = self.shorthand
      return _.verticalLayout(
        _.text("Hello world"),
        z.by("can", _.canvas((250, 300)))
      )
    @staticmethod
    def run1(): GUI.DoNothing().run("x", compile_binding={})
    def setup(self):
      self.addSizeGrip()
      self.can["bg"] = "blue"
      coord = (10, 50, 240, 210)
      self.can.create_arc(coord, start=0, extent=150, fill="red")
  class SplitWin(TkWin):
    def layout(self):
      z = self.shorthand
      return _.withFill(_.splitter(z.hor,
        _.text("left pane"),
        _.splitter(z.vert,
          _.text("top pane"),
          _.text("bottom pane")
        )
      ))
  class DoNothing(TkWin):
    def __init__(self):
      super().__init__()
      self.nodes = dict()
      self.ftv:TreeWidget
    def layout(self):
      z = self.shorthand
      return _.withFill(_.tabWidget(
        ("Tab 1", _.text("a")),
        ("Tab 2", _.verticalLayout(_.text("Lets dive into the world of computers"))),
        ("TabTree", z.by("tv", _.treeWidget())),
        ("File Man", z.by("ftv", _.treeWidget()))
      ))
    def setup(self):
      self.tv.makeTree(["Name", "Desc"], [
        "GeeksforGeeks",
        ("Computer Science", [
          ["Algorithm", "too hard"],
          ["Data structure", "just right"]
        ]),
        ("GATE papers", [
          "2018", "2019"
        ]),
        ("Programming Languages", [
          "Python", "Java"
        ])
      ])
      self.tv.item("GATE papers").moveTo("GeeksforGeeks")
      abspath = os.path.abspath(".")
      self.ftv.makeTree(["Project tree"], [])
      self.insertNode(self.ftv.rootItem, abspath, abspath)
      self.ftv.on(TreeWidget.open, self.openNode)
    def insertNode(self, parent:TreeWidget.TreeItem, text, abspath):
      node = parent.addChild((text,))
      if os.path.isdir(abspath):
        self.nodes[node[0]] = abspath
        node.addChild((None,))
    def openNode(self, event):
      node = self.ftv.focusItem
      abspath = self.nodes.pop(node[0], None) # This don't work for same-name opens, use multi-map (key-values) or multi column can fix this.
      if abspath:
        print(abspath)
        node.removeChilds()
        for p in os.listdir(abspath):
          self.insertNode(node, p, os.path.join(abspath, p))
      else: startFile(node[0])
  class ThreadDemo(TkWin):
    def __init__(self):
      super().__init__()
      self.ta = None
      z = self.shorthand
      self.active = z.var(str)
      self.confirmed = z.var(str)
    def layout(self):
      z = self.shorthand
      return _.verticalLayout(
        z.by("ta", _.textarea()),
        _.createLayout(z.hor, 0, _.text("Total active cases: ~"), _.text(self.active)),
        _.createLayout(z.vert, 0, _.text("Total confirmed cases:"), _.text(self.confirmed)),
        _.button("Refresh", self.on_refresh)
      )
    url = "https://api.covid19india.org/data.json"
    def on_refresh(self):
      runAsync(thunkifySync(requests.get, self.url), self.on_refreshed)
      runAsync(delay(1000), lambda ms: self.ta.insert("end", "233"))

    def on_refreshed(self, page):
      data = loads(page.text)
      #print(data)
      self.active.set(data["statewise"][0]["active"])
      self.confirmed.set(data["statewise"][0]["confirmed"])
      self.btn_refresh["text"] = "Data refreshed"
    def setup(self):
      self.setSizeBounds((220, 70))
      threading.Thread(target=self.thread_target).start()
    def thread_target(self):
      callThreadSafe(lambda: self.setSize(self.size, (0,0)))
      def addText(text): callThreadSafe(lambda: self.ta.insert("end", text))
      addText('doing things...\n')
      time.sleep(1)
      addText('doing more things...\n')
      time.sleep(2)
      addText('done')

from sys import argv
from tkgui.utils import Codegen
def main(args = argv[1:]):
  cfg = app.parse_args(args)
  gui = GUI()
  Codegen.useDebug = True
  gui.run("Widget Factory", compile_binding={"GUI":gui, "TkGUI":gui})

if __name__ == "__main__": main()
