#!/usr/bin/env python

import pdfcrowd
import sys

if len(sys.argv) != 4:
    print(len(sys.argv))
    print('required args: username apikey hostname')
    sys.exit(2)

c = pdfcrowd.Client(*sys.argv[1:])
c.convertURI('http://dl.dropboxusercontent.com/u/9346438/tests/webtopdfcom.html')
c.convertHtml('raw html')
c.convertFile('./test_files/in/simple.html')

