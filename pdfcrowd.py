# Copyright (C) 2009-2014 pdfcrowd.com
# 
# Portions of this code:
#   <http://code.activestate.com/recipes/146306/>
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

import urllib
import httplib
import mimetypes
import socket

__version__ = "2.5"


# constants for Client.setPageLayout()
SINGLE_PAGE, CONTINUOUS, CONTINUOUS_FACING = range(1,4)

# constants for Client.setPageMode()
NONE_VISIBLE, THUMBNAILS_VISIBLE, FULLSCREEN = range(1,4)

# constants for setInitialPdfZoomType()
FIT_WIDTH, FIT_HEIGHT, FIT_PAGE = range(1, 4)


class Error(Exception):
    """Thrown when an error occurs."""
    def __init__(self, error, http_code=None):
        self.http_code = http_code
        self.error = error

    def __str__(self):
        if self.http_code:
            return "%d - %s" % (self.http_code, self.error)
        else:
            return self.error


class Client:
    """Pdfcrowd API client."""
    
    def __init__(self, username, apikey, host=None, http_port=None):
        """Client constructor.
    
        username -- your username at Pdfcrowd
        apikey  -- your API key
        host     -- API host, defaults to pdfcrowd.com
   
        """
        self.fields = dict(username=username, key=apikey, \
                           pdf_scaling_factor=1, html_zoom=200)
        self.host = host or HOST
        self.http_port = http_port or HTTP_PORT
        self.useSSL(False)

    def convertURI(self, uri, outstream=None):
        """Converts a web page.
        
        uri        -- a web page URL
        outstream -- an object having method 'write(data)' - e.g. file,
                      StringIO, etc.; if None then the return value is a string
                      containing the PDF.
        """
        body = urllib.urlencode(self._prepare_fields(dict(src=uri)))
        content_type = 'application/x-www-form-urlencoded'
        return self._post(body, content_type, 'pdf/convert/uri/', outstream)

    def convertHtml(self, html, outstream=None):
        """Converts an in-memory html document.
    
        html    -- a string containing an html document
        outstream -- an object having method 'write(data)' - e.g. file,
                      StringIO, etc.; if None then the return value is a string
                      containing the PDF.
        """
        if type(html) == unicode:
            html = html.encode('utf-8')
        body = urllib.urlencode(self._prepare_fields(dict(src=html)))
        content_type = 'application/x-www-form-urlencoded'
        return self._post(body, content_type, 'pdf/convert/html/', outstream)

    def convertFile(self, fpath, outstream=None):
        """Converts an html file.
    
        fpath      -- a path to an html file
        outstream -- an object having method 'write(data)' - e.g. file,
                      StringIO, etc.; if None then the return value is a string
                      containing the PDF.
        """
        body, content_type = self._encode_multipart_post_data(fpath)
        return self._post(body, content_type, 'pdf/convert/html/', outstream)

    def numTokens(self):
        """Returns the number of available conversion tokens."""
        body = urllib.urlencode(self._prepare_fields())
        content_type = 'application/x-www-form-urlencoded'
        return int(self._post(body, content_type, 'user/%s/tokens/' % self.fields['username']))

    def useSSL(self, use_ssl):
        if use_ssl:
            self.port = HTTPS_PORT
            scheme = 'https'
            self.conn_type = httplib.HTTPSConnection
        else:
            self.port = self.http_port
            scheme = 'http'
            self.conn_type = httplib.HTTPConnection
        self.api_uri = '%s://%s:%d%s' % (scheme, self.host, self.port, API_SELECTOR_BASE)

    def setUsername(self, username):
        self.fields['username'] = username

    def setApiKey(self, key):
        self.fields['key'] = key

    def setPageWidth(self, value):
        self.fields['width'] = value

    def setPageHeight(self, value):
        self.fields['height'] = value

    def setHorizontalMargin(self, value):
        self.fields['margin_right'] = self.fields['margin_left'] = str(value)

    def setVerticalMargin(self, value):
        self.fields['margin_top'] = self.fields['margin_bottom'] = str(value)

    def setPageMargins(self, top, right, bottom, left):
        self.fields['margin_top'] = str(top)
        self.fields['margin_right'] = str(right)
        self.fields['margin_bottom'] = str(bottom)
        self.fields['margin_left'] = str(left)

    def setEncrypted(self, val=True):
        self.fields['encrypted'] = val

    def setUserPassword(self, pwd):
        self.fields['user_pwd'] = pwd

    def setOwnerPassword(self, pwd):
        self.fields['owner_pwd'] = pwd

    def setNoPrint(self, val=True):
        self.fields['no_print'] = val

    def setNoModify(self, val=True):
        self.fields['no_modify'] = val

    def setNoCopy(self, val=True):
        self.fields['no_copy'] = val

    def setPageLayout(self, value):
        assert value > 0 and value <= 3
        self.fields['page_layout'] = value

    def setPageMode(self, value):
        assert value > 0 and value <= 3
        self.fields['page_mode'] = value

    def setFooterText(self, value):
        self.fields['footer_text'] = value

    def enableImages(self, value=True):
        self.fields['no_images'] = not value

    def enableBackgrounds(self, value=True):
        self.fields['no_backgrounds'] = not value

    def setHtmlZoom(self, value):
        self.fields['html_zoom'] = value

    def enableJavaScript(self, value=True):
        self.fields['no_javascript'] = not value

    def enableHyperlinks(self, value=True):
        self.fields['no_hyperlinks'] = not value

    def setDefaultTextEncoding(self, value):
        self.fields['text_encoding'] = value

    def usePrintMedia(self, value=True):
        self.fields['use_print_media'] = value

    def setMaxPages(self, value):
        self.fields['max_pages'] = value

    def enablePdfcrowdLogo(self, value=True):
        self.fields['pdfcrowd_logo'] = value

    def setInitialPdfZoomType(self, value):
        assert value>0 and value<=3
        self.fields['initial_pdf_zoom_type'] = value
    
    def setInitialPdfExactZoom(self, value):
        self.fields['initial_pdf_zoom_type'] = 4
        self.fields['initial_pdf_zoom'] = value

    def setAuthor(self, value):
        self.fields['author'] = value

    def setFailOnNon200(self, value):
        self.fields['fail_on_non200'] = value

    def setPdfScalingFactor(self, value):
        self.fields['pdf_scaling_factor'] = value

    def setFooterHtml(self, value):
        self.fields['footer_html'] = value
        
    def setFooterUrl(self, value):
        self.fields['footer_url'] = value
        
    def setHeaderHtml(self, value):
        self.fields['header_html'] = value
        
    def setHeaderUrl(self, value):
        self.fields['header_url'] = value

    def setPageBackgroundColor(self, value):
        self.fields['page_background_color'] = value

    def setTransparentBackground(self, value=True):
        self.fields['transparent_background'] = value
        
    def setPageNumberingOffset(self, value):
        self.fields['page_numbering_offset'] = value

    def setHeaderFooterPageExcludeList(self, value):
        self.fields['header_footer_page_exclude_list'] = value
        
    def setWatermark(self, url, offset_x=0, offset_y=0):
        self.fields["watermark_url"] = url
        self.fields["watermark_offset_x"] = offset_x
        self.fields["watermark_offset_y"] = offset_y
    
    def setWatermarkRotation(self, angle):
        self.fields["watermark_rotation"] = angle

    def setWatermarkInBackground(self, val=True):
        self.fields["watermark_in_background"] = val


    # ----------------------------------------------------------------------
    #
    #                       Private stuff
    # 

    def _prepare_fields(self, extra_data={}):
        result = extra_data.copy()
        for key, val in self.fields.iteritems():
            if val:
                if type(val) == float:
                    val = str(val).replace(',', '.')
                result[key] = val
        return result

    def _encode_multipart_post_data(self, filename):
        boundary = '----------ThIs_Is_tHe_bOUnDary_$'
        body = []
        for field, value in self._prepare_fields().iteritems():
            body.append('--' + boundary)
            body.append('Content-Disposition: form-data; name="%s"' % field)
            body.append('')
            body.append(str(value))
        # filename
        body.append('--' + boundary)
        body.append('Content-Disposition: form-data; name="src"; filename="%s"' % filename)
        mime_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        body.append('Content-Type: ' + mime_type)
        body.append('')
        body.append(open(filename, 'rb').read())
        # finalize
        body.append('--' + boundary + '--')
        body.append('')
        body = '\r\n'.join(body)
        content_type = 'multipart/form-data; boundary=%s' % boundary
        return body, content_type

    # sends a POST to the API
    def _post(self, body, content_type, api_path, outstream=None):
        try:
            conn = self.conn_type(self.host, self.port)
            conn.putrequest('POST', API_SELECTOR_BASE + api_path)
            conn.putheader('content-type', content_type)
            conn.putheader('content-length', str(len(body)))
            conn.endheaders()
            conn.send(body)
            response = conn.getresponse()
            if response.status != 200:
                raise Error(response.read(), response.status)
            if outstream:
                while True:
                    data = response.read(16384)
                    if data:
                        outstream.write(data)
                    else:
                        break
                return outstream
            else:
                return response.read()
        except httplib.HTTPException, err:
            raise Error(str(err))
        except socket.gaierror, err:
            raise Error(err[1])


API_SELECTOR_BASE = '/api/'
HOST = 'pdfcrowd.com'
HTTP_PORT = 80
HTTPS_PORT = 443



