#!/bin/env python3
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(
  name="tkgui", version="0.1.1",
  python_requires=">=3.5",
  author="duangsuse", author_email="fedora-opensuse@outlook.com",
  url="https://github.com/duangsuse-valid-projects/Hachiko",
  description="Declarative tkinter wrapper for Python, features quick prototype & codegen",
  long_description="""
TkGUI is a declarative tkinter wrapper for Python, with lambdas, you can omit the parent argument for all widgets,
and let your code represents widget view tree directly
""",

  packages=find_packages())
