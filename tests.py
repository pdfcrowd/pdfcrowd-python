#!/usr/bin/env python

# Copyright (C) 2009-2013 pdfcrowd.com
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


if __name__ == "__main__":
    import sys
    import os
    import pdfcrowd

    if len(sys.argv) < 2:
        print "usage: python pdfcrowd.py username apikey [apihost [http-port https-port]]"
        sys.exit(1)

    if len(sys.argv) > 3:
        pdfcrowd.HOST = sys.argv[3]

    if len(sys.argv) == 6:
        pdfcrowd.HTTP_PORT = int(sys.argv[4])
        pdfcrowd.HTTPS_PORT = int(sys.argv[5])

    print "using %s ports %d %d" % (pdfcrowd.HOST, pdfcrowd.HTTP_PORT, pdfcrowd.HTTPS_PORT)

    os.chdir(os.path.dirname(sys.argv[0]))
    test_dir = '../test_files'
    if not os.path.exists(test_dir + '/out'):
        os.makedirs(test_dir + '/out')

    def out_stream(name, use_ssl):
        fname = './out/py_client_%s' % name
        if use_ssl:
            fname = fname + '_ssl'
        return open(fname + '.pdf', 'wb')

    html="<html><body>Uploaded content!</body></html>"
    client = pdfcrowd.Client(sys.argv[1], sys.argv[2])
    for use_ssl in [False, True]:
        client.useSSL(use_ssl)
        try:
            ntokens = client.numTokens()
            client.setFooterText("%p out of %n")
            client.convertURI('http://www.web-to-pdf.com', out_stream('uri', use_ssl))
            client.convertHtml(html, out_stream('content', use_ssl))
            client.convertFile(test_dir + '/in/simple.html', out_stream('upload', use_ssl))
            client.convertFile(test_dir + '/in/archive.tar.gz', out_stream('archive', use_ssl))
            after_tokens = client.numTokens()
            print 'remaining tokens:', after_tokens
            assert ntokens-4 == after_tokens
        except pdfcrowd.Error, why:
            print 'FAILED:', why
            sys.exit(1)
    # test individual methods
    tests = (('setPageWidth', 500),
             ('setPageHeight', -1),
             ('setHorizontalMargin', 72),
             ('setVerticalMargin', 72),
             ('setEncrypted', True),
             ('setUserPassword', 'userpwd'),
             ('setOwnerPassword', 'ownerpwd'),
             ('setNoPrint', True),
             ('setNoModify', True),
             ('setNoCopy', True),
             ('setPageLayout', pdfcrowd.CONTINUOUS),
             ('setPageMode', pdfcrowd.FULLSCREEN),
             ('setFooterText', '%p/%n | source %u'),
             ('enableImages', False),
             ('enableBackgrounds', False),
             ('setHtmlZoom', 300),
             ('enableJavaScript', False),
             ('enableHyperlinks', False),
             ('setDefaultTextEncoding', 'iso-8859-1'),
             ('usePrintMedia', True),
             ('setMaxPages', 1),
             ('enablePdfcrowdLogo', True),
             ('setInitialPdfZoomType', pdfcrowd.FIT_PAGE),
             ('setInitialPdfExactZoom', 113),
             ('setPdfScalingFactor', .5),
             ('setFooterHtml', '<b>bold</b> and <i>italic</i> <img src="http://pdfcrowd.com/static/images/logo175x30.png" />'),
             ('setFooterUrl', 'http://google.com'),
             ('setHeaderHtml', 'page %p out of %n'),
             ('setHeaderUrl', 'http://google.com'),             
             ('setAuthor', 'Your Name'),
             ('setPageBackgroundColor', 'ee82EE'),
             ('setTransparentBackground', True)
             )

    try:
        for method, arg in tests:
            client = pdfcrowd.Client(sys.argv[1], sys.argv[2])
            client.setVerticalMargin("1in")
            getattr(client, method)(arg)
            client.convertFile(test_dir + '/in/simple.html', out_stream(method.lower(), False))
    except pdfcrowd.Error, why:
        print 'FAILED', why
        sys.exit(1)
    # 4 margins
    client = pdfcrowd.Client(sys.argv[1], sys.argv[2])
    client.setPageMargins('0.25in', '0.5in', '0.75in', '1.0in')
    client.convertHtml('<div style="background-color:red;height:100%">4 margins</div>', out_stream('4margins', False))
    # expected failures
    client = pdfcrowd.Client(sys.argv[1], sys.argv[2])
    try:
        client.setFailOnNon200(True)
        client.convertURI("http://pdfcrowd.com/this/url/does/not/exist/")
        print "FAILED expected an exception"
        sys.exit(1)
    except pdfcrowd.Error, why:
        pass # expected
