#!/usr/bin/env python

import pdfcrowd
import sys

if len(sys.argv) != 4:
    print 'required args: username apikey hostname'
    sys.exit(2)

c = pdfcrowd.Client(*sys.argv[1:])
c.convertURI('http://www.jagpdf.org')
c.convertHtml('raw html')
c.convertFile('./test_files/in/simple.html')

