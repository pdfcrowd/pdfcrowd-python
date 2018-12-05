#!/usr/bin/env python

# Copyright (C) 2009 pdfcrowd.com
# 
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
# 
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.

from distutils.core import setup

py_modules=['pdfcrowd']

setup(name='pdfcrowd',
      version='4.4.1',
      description="A client library for the Pdfcrowd API.",
      url='https://pdfcrowd.com/doc/api/',
      license="License :: OSI Approved :: MIT License",
      author='Pdfcrowd Team',
      author_email='support@pdfcrowd.com',
      long_description="""
The Pdfcrowd API lets you easily convert between HTML, PDF and various image formats.
""",
      py_modules=py_modules,
      scripts=['./html2pdf',
               './html2image',
               './image2image',
               './image2pdf',
               './pdf2pdf'
               ],
      classifiers=["License :: OSI Approved :: MIT License",
                   "Operating System :: MacOS",
                   "Operating System :: Microsoft",
                   "Operating System :: POSIX",
                   "Operating System :: Unix",
                   "Intended Audience :: Developers",
                   "Topic :: Software Development :: Libraries"])
