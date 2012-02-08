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
      version='2.3',
      description="A client for Pdfcrowd API.",
      url='http://pdfcrowd.com/html-to-pdf-api/',
      license="License :: OSI Approved :: MIT License",
      author='Pdfcrowd Team',
      author_email='info@pdfcrowd.com',
      long_description="""
The Pdfcrowd API lets you easily create PDF from web pages or raw HTML
code in your Python applications.


To use the API, you need an account on `pdfcrowd.com
<https://pdfcrowd.com>`_, if you don't have one you can sign up `here
<https://pdfcrowd.com/pricing/api/>`_. This will give you a username
and an API key.


An example::

    import pdfcrowd
    
    try:
        # create an API client instance
        client = pdfcrowd.Client("username", "apikey")
    
        # convert a web page and store the generated PDF into a pdf variable
        pdf = client.convertURI('http://example.com')
    
        # convert an HTML string and save the result to a file
        html="<html><body>In-memory HTML.</body></html>"
        client.convertHtml(html, open('html.pdf', 'wb'))
    
        # convert an HTML file
        client.convertFile('/path/to/local/file.html', open('file.pdf', 'wb'))
    
    except pdfcrowd.Error, why:
        print 'Failed:', why

""",
      py_modules=py_modules,
      classifiers=["Development Status :: 5 - Production/Stable",
                   "License :: OSI Approved :: MIT License",
                   "Operating System :: MacOS",
                   "Operating System :: Microsoft",
                   "Operating System :: POSIX",
                   "Operating System :: Unix",
                   "Intended Audience :: Developers",
                   "Programming Language :: Python",
                   "Topic :: Software Development :: Libraries"])

