# Copyright (C) 2009-2026 pdfcrowd.com
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

try:
    from urllib import urlencode
    PYTHON_3 = False
except ImportError:
    from urllib.parse import urlencode
    PYTHON_3 = True

try:
    import httplib
except:
    import http.client as httplib

import mimetypes
import socket
import base64
import re
import sys
import os
import ssl
import time
import warnings

__version__ = '7.0.0'

class BaseError(Exception):
    def __init__(self, error, http_code):
        self.error = error

        error_match = re.match(
            r'^(\d+)\.(\d+)\s+-\s+(.*?)(?:\s+Documentation link:\s+(.*))?$',
            self.error,
            re.DOTALL)

        if error_match:
            self.http_code = error_match.group(1)
            self.reason_code = error_match.group(2)
            self.message = error_match.group(3)
            self.doc_link = error_match.group(4) or ''
        else:
            self.http_code = http_code
            self.reason_code = -1
            self.message = self.error
            if self.http_code:
                self.error = "%s - %s" % (self.http_code, self.error)
            self.doc_link = ''

    def __str__(self):
        return self.error

    def getCode(self):
        warnings.warn(
            '`getCode` is obsolete and will be removed in future '
            'versions. Use `getStatusCode` instead.',
            DeprecationWarning,
            stacklevel=2
        )
        return self.http_code

    def getStatusCode(self):
        return self.http_code

    def getReasonCode(self):
        return self.reason_code

    def getMessage(self):
        return self.message

    def getDocumentationLink(self):
        return self.doc_link

# ======================================
# === PDFCrowd legacy version client ===
# ======================================

if PYTHON_3:
    # constants for Client.setPageLayout()
    SINGLE_PAGE, CONTINUOUS, CONTINUOUS_FACING = range(1, 4)

    # constants for Client.setPageMode()
    NONE_VISIBLE, THUMBNAILS_VISIBLE, FULLSCREEN = range(1, 4)

    # constants for setInitialPdfZoomType()
    FIT_WIDTH, FIT_HEIGHT, FIT_PAGE = range(1, 4)


    class Error(BaseError):
        """Thrown when an error occurs."""
        def __init__(self, error, http_code=None):
            super().__init__(
                error if isinstance(error, str) else str(error, "utf-8"),
                http_code)

    class Client:
        """PDFCrowd API client."""

        def __init__(self, username, apikey, host=None, http_port=None):
            """Client constructor.

            username -- your username at PDFCrowd
            apikey  -- your API key
            host     -- API host, defaults to pdfcrowd.com

            """
            self.fields = dict(username=username, key=apikey,
                               pdf_scaling_factor=1, html_zoom=200)
            self.host = host or HOST_LEGACY
            self.http_port = http_port or HTTP_PORT
            self.useSSL(False)
            self.setProxy(None, None)

        def setProxy(self, host, port, username=None, password=None):
            self.proxy_host = host
            self.proxy_port = port
            self.proxy_username = username
            self.proxy_password = password

        def convertURI(self, uri, outstream=None):
            """Converts a web page.

            uri        -- a web page URL
            outstream -- an object having method 'write(data)' - e.g. file,
                          StringIO, etc.; if None then the return value is a string
                          containing the PDF.
            """
            body = urlencode(self._prepare_fields(dict(src=uri)))
            content_type = 'application/x-www-form-urlencoded'
            return self._post(body, content_type, 'pdf/convert/uri/', outstream)

        def convertHtml(self, html, outstream=None):
            """Converts an in-memory html document.

            html    -- a string containing an html document
            outstream -- an object having method 'write(data)' - e.g. file,
                          StringIO, etc.; if None then the return value is a string
                          containing the PDF.
            """
            if not isinstance(html, str):
                html = html.encode('utf-8')
            body = urlencode(self._prepare_fields(dict(src=html)))
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
            body = urlencode(self._prepare_fields())
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
            for key, val in iter(self.fields.items()):
                if val:
                    if type(val) == float:
                        val = str(val).replace(',', '.')
                    result[key] = val
            return result

        def _encode_multipart_post_data(self, filename):
            boundary = '----------ThIs_Is_tHe_bOUnDary_$'
            head, tail = [], []

            for field, value in iter(self._prepare_fields().items()):
                head.append('--' + boundary)
                head.append('Content-Disposition: form-data; name="%s"' % field)
                head.append('')
                head.append(str(value))

            # filename
            head.append('--' + boundary)
            head.append('Content-Disposition: form-data; name="src"; filename="%s"' % filename)
            mime_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
            head.append('Content-Type: ' + mime_type)
            head.append('')
            content = open(filename, 'rb').read()

            # finalize
            tail.append('--' + boundary + '--')
            tail.append('')
            body = ["\r\n".join(head).encode("utf-8"), content, "\r\n".join(tail).encode("utf-8")]
            body = b"\r\n".join(body)
            content_type = 'multipart/form-data; boundary=%s' % boundary

            return body, content_type

        # sends a POST to the API
        def _post(self, body, content_type, api_path, outstream=None):
            try:
                if self.proxy_host:
                    if self.conn_type == httplib.HTTPSConnection:
                        raise Error("HTTPS over a proxy is not supported.")

                    conn = self.conn_type(self.proxy_host, self.proxy_port)
                    conn.putrequest('POST', "http://%s:%d%s" % (self.host, self.port, API_SELECTOR_BASE + api_path))
                    if self.proxy_username:
                        user_string = "%s:%s" % (self.proxy_username, self.proxy_password)
                        proxy_auth = "Basic " + base64.b64encode(user_string)
                        conn.putheader('Proxy-Authorization', proxy_auth)
                else:
                    conn = self.conn_type(self.host, self.port)
                    conn.putrequest('POST', API_SELECTOR_BASE + api_path)

                conn.putheader('content-type', content_type)
                body = body if isinstance(body, bytes) else body.encode()
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
            except httplib.HTTPException as err:
                raise Error(str(err))
            except socket.gaierror as err:
                raise Error(str(err))

    API_SELECTOR_BASE = '/api/'
    HOST_LEGACY = os.environ.get('PDFCROWD_HOST', 'pdfcrowd.com')
    HTTP_PORT = 80
    HTTPS_PORT = 443
else:
    # constants for Client.setPageLayout()
    SINGLE_PAGE, CONTINUOUS, CONTINUOUS_FACING = range(1,4)

    # constants for Client.setPageMode()
    NONE_VISIBLE, THUMBNAILS_VISIBLE, FULLSCREEN = range(1,4)

    # constants for setInitialPdfZoomType()
    FIT_WIDTH, FIT_HEIGHT, FIT_PAGE = range(1, 4)


    class Error(BaseError):
        """Thrown when an error occurs."""
        def __init__(self, error, http_code=None):
            BaseError.__init__(self, error, http_code)

    class Client:
        """PDFCrowd API client."""

        def __init__(self, username, apikey, host=None, http_port=None):
            """Client constructor.

            username -- your username at PDFCrowd
            apikey  -- your API key
            host     -- API host, defaults to pdfcrowd.com

            """
            self.fields = dict(username=username, key=apikey, \
                               pdf_scaling_factor=1, html_zoom=200)
            self.host = host or HOST_LEGACY
            self.http_port = http_port or HTTP_PORT
            self.useSSL(False)
            self.setProxy(None, None)

        def setProxy(self, host, port, username=None, password=None):
            self.proxy_host = host
            self.proxy_port = port
            self.proxy_username = username
            self.proxy_password = password

        def convertURI(self, uri, outstream=None):
            """Converts a web page.

            uri        -- a web page URL
            outstream -- an object having method 'write(data)' - e.g. file,
                          StringIO, etc.; if None then the return value is a string
                          containing the PDF.
            """
            body = urlencode(self._prepare_fields(dict(src=uri)))
            content_type = 'application/x-www-form-urlencoded'
            return self._post(body, content_type, 'pdf/convert/uri/', outstream)

        def convertHtml(self, html, outstream=None):
            """Converts an in-memory html document.

            html    -- a string containing an html document
            outstream -- an object having method 'write(data)' - e.g. file,
                          StringIO, etc.; if None then the return value is a string
                          containing the PDF.
            """
            if isinstance(html, unicode):
                html = html.encode('utf-8')
            body = urlencode(self._prepare_fields(dict(src=html)))
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
            body = urlencode(self._prepare_fields())
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
            body.append('Content-Type: ' + str(mime_type))
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
                if self.proxy_host:
                    if self.conn_type == httplib.HTTPSConnection:
                        raise Error("HTTPS over a proxy is not supported.")
                    conn = self.conn_type(self.proxy_host, self.proxy_port)
                    conn.putrequest('POST', "http://%s:%d%s" % (self.host, self.port, API_SELECTOR_BASE + api_path))
                    if self.proxy_username:
                        user_string = "%s:%s" % (self.proxy_username, self.proxy_password)
                        proxy_auth = "Basic " + base64.b64encode(user_string)
                        conn.putheader('Proxy-Authorization', proxy_auth)
                else:
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
            except httplib.HTTPException as err:
                raise Error(str(err))
            except socket.gaierror as err:
                raise Error(str(err))


    API_SELECTOR_BASE = '/api/'
    HOST_LEGACY = os.environ.get('PDFCROWD_HOST', 'pdfcrowd.com')
    HTTP_PORT = 80
    HTTPS_PORT = 443

# =====================================
# === PDFCrowd cloud version client ===
# =====================================

HOST = os.environ.get('PDFCROWD_HOST', 'api.pdfcrowd.com')
MULTIPART_BOUNDARY = '----------ThIs_Is_tHe_bOUnDary_$'
CLIENT_VERSION = '7.0.0'

def get_utf8_string(string):
    if PYTHON_3:
        # get Python3 string
        try:
            return string.decode()
        except AttributeError:
            pass
    else:
        # get Python2 string
        if isinstance(string, unicode):
            return string.encode('utf-8')
    return string

def create_invalid_value_message(value, field, converter, hint, id):
    message = "400.311 - Invalid value '%s' for the '%s' option." % (value, field)
    if hint:
        message += " " + hint
    return message + ' ' + "Documentation link: https://www.pdfcrowd.com/api/%s-python/ref/#%s" % (converter, id)

def iter_items(dictionary):
    if PYTHON_3:
        return dictionary.items()
    return dictionary.iteritems()

def gen_fields(fields):
    for key, val in iter_items(fields):
        # Numeric zero is an explicitly supplied value.
        if val or (val == 0 and not isinstance(val, bool)):
            yield key, str(val)

def add_file_field(name, file_name, data, body, mime_type = None):
    # file field
    head = []
    head.append('--' + MULTIPART_BOUNDARY)
    head.append(
        'Content-Disposition: form-data; name="{0}"; filename="{1}"'.format(
            name, get_utf8_string(file_name)))
    if not mime_type:
        mime_type = 'application/octet-stream'
    head.append('Content-Type: {0}'.format(mime_type))
    head.append('')
    if PYTHON_3:
        body.append('\r\n'.join(head).encode('utf-8'))
    else:
        body.append('\r\n'.join(head))
    body.append(data)

def encode_multipart_post_data(fields, files, raw_data):
    head, tail = [], []
    body = []
    for field, value in gen_fields(fields):
        head.append('--' + MULTIPART_BOUNDARY)
        head.append('Content-Disposition: form-data; name="%s"' % field)
        head.append('')
        head.append(value)
    if PYTHON_3:
        body.append('\r\n'.join(head).encode('utf-8'))
    else:
        body.append('\r\n'.join(head))

    for name, file_name in iter_items(files):
        with open(file_name, 'rb') as f:
            add_file_field(name, file_name, f.read(), body, mimetypes.guess_type(file_name)[0])

    for name, data in iter_items(raw_data):
        add_file_field(name, name, data, body)

    # finalize
    tail.append('--' + MULTIPART_BOUNDARY + '--')
    tail.append('')
    body.append('\r\n'.join(tail).encode('utf-8'))

    return b'\r\n'.join(body)

def base64_encode(value):
    if not isinstance(value, bytes):
        value = value.encode()
    value = base64.b64encode(value)
    if PYTHON_3:
        return value.decode()
    return value

def encode_credentials(user_name, password):
    auth = '%s:%s' % (user_name, password)
    return 'Basic ' + base64_encode(auth)

class ConnectionHelper:
    def __init__(self, user_name, api_key):
        self.user_name = user_name
        self.api_key = api_key

        self._reset_response_data()
        self.setProxy(None, None, None, None)
        self.setUseHttp(False)
        self.setUserAgent('pdfcrowd_python_client/7.0.0 (https://pdfcrowd.com)')

        self.retry_count = 1
        self.converter_version = '24.04'

    def reset_input(self, fields, files, raw_data):
        # Preserve conversion options and auxiliary files between requests.
        fields.pop('url', None)
        fields.pop('text', None)
        files.pop('file', None)
        raw_data.pop('file', None)
        raw_data.pop('stream', None)

    def _reset_response_data(self):
        self.debug_log_url = None
        self.credits = 999999
        self.consumed_credits = 0
        self.job_id = ''
        self.page_count = 0
        self.total_page_count = 0
        self.output_size = 0
        self.retry = 0

    def post(self, fields, files, raw_data, out_stream = None):
        body = encode_multipart_post_data(fields, files, raw_data)
        content_type = 'multipart/form-data; boundary=' + MULTIPART_BOUNDARY
        return self._do_post(body, content_type, out_stream)

    def _create_connection(self, host, port):
        kwargs = {}
        if not self.use_http and host != 'api.pdfcrowd.com':
            kwargs['context'] = ssl._create_unverified_context()
        return self.conn_type(host, port, **kwargs)

    def _get_connection(self):
        conv_selector = '/convert/{0}/'.format(self.converter_version)
        if self.proxy_host:
            conn = self._create_connection(self.proxy_host, self.proxy_port)
            conn.putrequest('POST', 'http://{0}:{1}{2}'.format(
                HOST, self.port, conv_selector))
            if self.proxy_user_name:
                conn.putheader('Proxy-Authorization',
                               encode_credentials(self.proxy_user_name,
                                                  self.proxy_password))
        else:
            conn = self._create_connection(HOST, self.port)
            conn.putrequest('POST', conv_selector)
        return conn

    # sends a POST to the API
    def _do_post(self, body, content_type, out_stream=None):
        if not self.use_http and self.proxy_host:
            raise Error('HTTPS over a proxy is not supported.')

        self._reset_response_data()

        while True:
            try:
                return self._exec_request(body, content_type, out_stream)
            except Error as err:
                if (err.getStatusCode() == 502 or err.getStatusCode() == 503) and self.retry_count > self.retry:
                    self.retry += 1
                    time.sleep(self.retry * 0.1)
                else:
                    raise

    def _exec_request(self, body, content_type, out_stream):
        writing_output = False
        try:
            conn = self._get_connection()
            conn.putheader('Content-Type', content_type)
            conn.putheader('Content-Length', str(len(body)))
            if self.user_agent != None:
                conn.putheader('User-Agent', self.user_agent)
            conn.putheader('Authorization',
                           encode_credentials(self.user_name, self.api_key))
            conn.endheaders()
            body = body if isinstance(body, bytes) else body.encode()
            conn.send(body)
            response = conn.getresponse()

            self.debug_log_url = response.getheader('X-Pdfcrowd-Debug-Log', '')
            # Python 3.0 joins getheader's default; apply numeric defaults here.
            self.credits = int(response.getheader(
                'X-Pdfcrowd-Remaining-Credits', '') or 999999)
            self.consumed_credits = int(response.getheader(
                'X-Pdfcrowd-Consumed-Credits', '') or 0)
            self.job_id = response.getheader('X-Pdfcrowd-Job-Id', '')
            self.page_count = int(response.getheader('X-Pdfcrowd-Pages', '') or 0)
            self.total_page_count = int(response.getheader(
                'X-Pdfcrowd-Total-Pages', '') or 0)
            self.output_size = int(response.getheader(
                'X-Pdfcrowd-Output-Size', '') or 0)

            if response.status > 299:
                raise Error(response.read(), response.status)

            if out_stream:
                while True:
                    data = response.read(16384)
                    if data:
                        writing_output = True
                        out_stream.write(data)
                        writing_output = False
                    elif response.length:
                        raise Error(
                            'Incomplete response from PDFCrowd: '
                            '{0} bytes are missing.'.format(response.length))
                    else:
                        break
                return out_stream

            return response.read()
        except httplib.HTTPException as err:
            raise Error(str(err))
        except ssl.SSLError as err:
            raise Error("400.356 - There was a problem connecting to PDFCrowd servers over HTTPS:\n" +
                        "{0} ({1})".format(err.reason, err.errno) +
                        "\nYou can still use the API over HTTP, you just need to add the following line right after PDFCrowd client initialization:\nclient.setUseHttp(True)",
                        0)
        except socket.gaierror as err:
            raise Error(str(err))
        except socket.error as err:
            if writing_output:
                # Local write failures must reach the caller unchanged.
                raise
            raise Error(str(err))

    def setUseHttp(self, use_http):
        if use_http:
            self.port = 80
            self.conn_type = httplib.HTTPConnection
        else:
            self.port = 443
            self.conn_type = httplib.HTTPSConnection
        self.use_http = use_http

    def setUserAgent(self, user_agent):
        self.user_agent = user_agent

    def setRetryCount(self, retry_count):
        self.retry_count = retry_count

    def setConverterVersion(self, converter_version):
        self.converter_version = converter_version

    def setProxy(self, host, port, user_name, password):
        self.proxy_host = host
        self.proxy_port = port
        self.proxy_user_name = user_name
        self.proxy_password = password

    def getDebugLogUrl(self):
        return self.debug_log_url

    def getRemainingCreditCount(self):
        return self.credits

    def getConsumedCreditCount(self):
        return self.consumed_credits

    def getJobId(self):
        return self.job_id

    def getPageCount(self):
        return self.page_count

    def getTotalPageCount(self):
        return self.total_page_count

    def getOutputSize(self):
        return self.output_size

    def getConverterVersion(self):
        return self.converter_version

# generated code

class HtmlToPdfClient:
    """Conversion from HTML to PDF.

    https://pdfcrowd.com/api/html-to-pdf-python/"""

    def __init__(self, user_name, api_key):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#__init__"""
        self.helper = ConnectionHelper(user_name, api_key)
        self.fields = {
            'input_format': 'html',
            'output_format': 'pdf'
        }
        self.file_id = 1
        self.files = {}
        self.raw_data = {}

    def convertUrl(self, url):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#convert_url"""
        if not re.match(r'(?i)^https?://.*$', url):
            raise Error(create_invalid_value_message(url, "convertUrl", "html-to-pdf", 'Supported protocols are http:// and https://.', "convert_url"), 470);
        
        self.helper.reset_input(self.fields, self.files, self.raw_data)
        self.fields['url'] = get_utf8_string(url)
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertUrlToStream(self, url, out_stream):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#convert_url_to_stream"""
        if not re.match(r'(?i)^https?://.*$', url):
            raise Error(create_invalid_value_message(url, "convertUrlToStream::url", "html-to-pdf", 'Supported protocols are http:// and https://.', "convert_url_to_stream"), 470);
        
        self.helper.reset_input(self.fields, self.files, self.raw_data)
        self.fields['url'] = get_utf8_string(url)
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertUrlToFile(self, url, file_path):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#convert_url_to_file"""
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "convertUrlToFile::file_path", "html-to-pdf", 'The string must not be empty.', "convert_url_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        succeeded = False
        try:
            self.convertUrlToStream(url,output_file)
            succeeded = True
        finally:
            if succeeded:
                output_file.close()
            else:
                try:
                    output_file.close()
                except BaseException:
                    pass
                try:
                    os.remove(file_path)
                except OSError:
                    pass

    def convertFile(self, file):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#convert_file"""
        if not (os.path.isfile(file) and os.path.getsize(file)):
            raise Error(create_invalid_value_message(file, "convertFile", "html-to-pdf", 'The file must exist and not be empty.', "convert_file"), 470);
        
        self.helper.reset_input(self.fields, self.files, self.raw_data)
        self.files['file'] = get_utf8_string(file)
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertFileToStream(self, file, out_stream):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#convert_file_to_stream"""
        if not (os.path.isfile(file) and os.path.getsize(file)):
            raise Error(create_invalid_value_message(file, "convertFileToStream::file", "html-to-pdf", 'The file must exist and not be empty.', "convert_file_to_stream"), 470);
        
        self.helper.reset_input(self.fields, self.files, self.raw_data)
        self.files['file'] = get_utf8_string(file)
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertFileToFile(self, file, file_path):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#convert_file_to_file"""
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "convertFileToFile::file_path", "html-to-pdf", 'The string must not be empty.', "convert_file_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        succeeded = False
        try:
            self.convertFileToStream(file,output_file)
            succeeded = True
        finally:
            if succeeded:
                output_file.close()
            else:
                try:
                    output_file.close()
                except BaseException:
                    pass
                try:
                    os.remove(file_path)
                except OSError:
                    pass

    def convertString(self, text):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#convert_string"""
        if not (text):
            raise Error(create_invalid_value_message(text, "convertString", "html-to-pdf", 'The string must not be empty.', "convert_string"), 470);
        
        self.helper.reset_input(self.fields, self.files, self.raw_data)
        self.fields['text'] = get_utf8_string(text)
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertStringToStream(self, text, out_stream):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#convert_string_to_stream"""
        if not (text):
            raise Error(create_invalid_value_message(text, "convertStringToStream::text", "html-to-pdf", 'The string must not be empty.', "convert_string_to_stream"), 470);
        
        self.helper.reset_input(self.fields, self.files, self.raw_data)
        self.fields['text'] = get_utf8_string(text)
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertStringToFile(self, text, file_path):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#convert_string_to_file"""
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "convertStringToFile::file_path", "html-to-pdf", 'The string must not be empty.', "convert_string_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        succeeded = False
        try:
            self.convertStringToStream(text,output_file)
            succeeded = True
        finally:
            if succeeded:
                output_file.close()
            else:
                try:
                    output_file.close()
                except BaseException:
                    pass
                try:
                    os.remove(file_path)
                except OSError:
                    pass

    def convertStream(self, in_stream):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#convert_stream"""
        self.helper.reset_input(self.fields, self.files, self.raw_data)
        self.raw_data['stream'] = in_stream.read()
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertStreamToStream(self, in_stream, out_stream):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#convert_stream_to_stream"""
        self.helper.reset_input(self.fields, self.files, self.raw_data)
        self.raw_data['stream'] = in_stream.read()
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertStreamToFile(self, in_stream, file_path):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#convert_stream_to_file"""
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "convertStreamToFile::file_path", "html-to-pdf", 'The string must not be empty.', "convert_stream_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        succeeded = False
        try:
            self.convertStreamToStream(in_stream,output_file)
            succeeded = True
        finally:
            if succeeded:
                output_file.close()
            else:
                try:
                    output_file.close()
                except BaseException:
                    pass
                try:
                    os.remove(file_path)
                except OSError:
                    pass

    def setZipMainFilename(self, filename):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_zip_main_filename"""
        self.fields['zip_main_filename'] = get_utf8_string(filename)
        return self

    def setPageSize(self, size):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_page_size"""
        if not re.match(r'(?i)^(A0|A1|A2|A3|A4|A5|A6|Letter)$', size):
            raise Error(create_invalid_value_message(size, "setPageSize", "html-to-pdf", 'Allowed values are A0, A1, A2, A3, A4, A5, A6, Letter.', "set_page_size"), 470);
        
        self.fields['page_size'] = get_utf8_string(size)
        return self

    def setPageWidth(self, width):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_page_width"""
        if not re.match(r'(?i)^0$|^[0-9]*\.?[0-9]+(pt|px|mm|cm|in)$', width):
            raise Error(create_invalid_value_message(width, "setPageWidth", "html-to-pdf", 'The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'.', "set_page_width"), 470);
        
        self.fields['page_width'] = get_utf8_string(width)
        return self

    def setPageHeight(self, height):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_page_height"""
        if not re.match(r'(?i)^0$|^\-1$|^[0-9]*\.?[0-9]+(pt|px|mm|cm|in)$', height):
            raise Error(create_invalid_value_message(height, "setPageHeight", "html-to-pdf", 'The value must be -1 or specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'.', "set_page_height"), 470);
        
        self.fields['page_height'] = get_utf8_string(height)
        return self

    def setPageDimensions(self, width, height):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_page_dimensions"""
        self.setPageWidth(width)
        self.setPageHeight(height)
        return self

    def setOrientation(self, orientation):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_orientation"""
        if not re.match(r'(?i)^(landscape|portrait)$', orientation):
            raise Error(create_invalid_value_message(orientation, "setOrientation", "html-to-pdf", 'Allowed values are landscape, portrait.', "set_orientation"), 470);
        
        self.fields['orientation'] = get_utf8_string(orientation)
        return self

    def setMarginTop(self, top):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_margin_top"""
        if not re.match(r'(?i)^0$|^[0-9]*\.?[0-9]+(pt|px|mm|cm|in)$', top):
            raise Error(create_invalid_value_message(top, "setMarginTop", "html-to-pdf", 'The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'.', "set_margin_top"), 470);
        
        self.fields['margin_top'] = get_utf8_string(top)
        return self

    def setMarginRight(self, right):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_margin_right"""
        if not re.match(r'(?i)^0$|^[0-9]*\.?[0-9]+(pt|px|mm|cm|in)$', right):
            raise Error(create_invalid_value_message(right, "setMarginRight", "html-to-pdf", 'The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'.', "set_margin_right"), 470);
        
        self.fields['margin_right'] = get_utf8_string(right)
        return self

    def setMarginBottom(self, bottom):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_margin_bottom"""
        if not re.match(r'(?i)^0$|^[0-9]*\.?[0-9]+(pt|px|mm|cm|in)$', bottom):
            raise Error(create_invalid_value_message(bottom, "setMarginBottom", "html-to-pdf", 'The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'.', "set_margin_bottom"), 470);
        
        self.fields['margin_bottom'] = get_utf8_string(bottom)
        return self

    def setMarginLeft(self, left):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_margin_left"""
        if not re.match(r'(?i)^0$|^[0-9]*\.?[0-9]+(pt|px|mm|cm|in)$', left):
            raise Error(create_invalid_value_message(left, "setMarginLeft", "html-to-pdf", 'The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'.', "set_margin_left"), 470);
        
        self.fields['margin_left'] = get_utf8_string(left)
        return self

    def setNoMargins(self, value):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_no_margins"""
        self.fields['no_margins'] = value
        return self

    def setPageMargins(self, top, right, bottom, left):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_page_margins"""
        self.setMarginTop(top)
        self.setMarginRight(right)
        self.setMarginBottom(bottom)
        self.setMarginLeft(left)
        return self

    def setPrintPageRange(self, pages):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_print_page_range"""
        if not re.match(r'^(?:\s*(?:\d+|(?:\d*\s*\-\s*\d+)|(?:\d+\s*\-\s*\d*)|odd|even|last)\s*,\s*)*\s*(?:\d+|(?:\d*\s*\-\s*\d+)|(?:\d+\s*\-\s*\d*)|odd|even|last)\s*$', pages):
            raise Error(create_invalid_value_message(pages, "setPrintPageRange", "html-to-pdf", 'A comma separated list of page numbers or ranges. Special strings may be used, such as \'odd\', \'even\' and \'last\'.', "set_print_page_range"), 470);
        
        self.fields['print_page_range'] = get_utf8_string(pages)
        return self

    def setContentViewportWidth(self, width):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_content_viewport_width"""
        if not re.match(r'(?i)^(balanced|small|medium|large|extra-large|[0-9]+(px)?)$', width):
            raise Error(create_invalid_value_message(width, "setContentViewportWidth", "html-to-pdf", 'The value must be \'balanced\', \'small\', \'medium\', \'large\', \'extra-large\', or a number in the range 96-65000px.', "set_content_viewport_width"), 470);
        
        self.fields['content_viewport_width'] = get_utf8_string(width)
        return self

    def setContentViewportHeight(self, height):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_content_viewport_height"""
        if not re.match(r'(?i)^(auto|large|[0-9]+(px)?)$', height):
            raise Error(create_invalid_value_message(height, "setContentViewportHeight", "html-to-pdf", 'The value must be \'auto\', \'large\', or a number.', "set_content_viewport_height"), 470);
        
        self.fields['content_viewport_height'] = get_utf8_string(height)
        return self

    def setContentFitMode(self, mode):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_content_fit_mode"""
        if not re.match(r'(?i)^(auto|smart-scaling|no-scaling|viewport-width|content-width|single-page|single-page-ratio)$', mode):
            raise Error(create_invalid_value_message(mode, "setContentFitMode", "html-to-pdf", 'Allowed values are auto, smart-scaling, no-scaling, viewport-width, content-width, single-page, single-page-ratio.', "set_content_fit_mode"), 470);
        
        self.fields['content_fit_mode'] = get_utf8_string(mode)
        return self

    def setRemoveBlankPages(self, pages):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_remove_blank_pages"""
        if not re.match(r'(?i)^(trailing|all|none)$', pages):
            raise Error(create_invalid_value_message(pages, "setRemoveBlankPages", "html-to-pdf", 'Allowed values are trailing, all, none.', "set_remove_blank_pages"), 470);
        
        self.fields['remove_blank_pages'] = get_utf8_string(pages)
        return self

    def setHeaderUrl(self, url):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_header_url"""
        if not re.match(r'(?i)^https?://.*$', url):
            raise Error(create_invalid_value_message(url, "setHeaderUrl", "html-to-pdf", 'Supported protocols are http:// and https://.', "set_header_url"), 470);
        
        self.fields['header_url'] = get_utf8_string(url)
        return self

    def setHeaderHtml(self, html):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_header_html"""
        if not (html):
            raise Error(create_invalid_value_message(html, "setHeaderHtml", "html-to-pdf", 'The string must not be empty.', "set_header_html"), 470);
        
        self.fields['header_html'] = get_utf8_string(html)
        return self

    def setHeaderHeight(self, height):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_header_height"""
        if not re.match(r'(?i)^0$|^[0-9]*\.?[0-9]+(pt|px|mm|cm|in)$', height):
            raise Error(create_invalid_value_message(height, "setHeaderHeight", "html-to-pdf", 'The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'.', "set_header_height"), 470);
        
        self.fields['header_height'] = get_utf8_string(height)
        return self

    def setZipHeaderFilename(self, filename):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_zip_header_filename"""
        self.fields['zip_header_filename'] = get_utf8_string(filename)
        return self

    def setFooterUrl(self, url):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_footer_url"""
        if not re.match(r'(?i)^https?://.*$', url):
            raise Error(create_invalid_value_message(url, "setFooterUrl", "html-to-pdf", 'Supported protocols are http:// and https://.', "set_footer_url"), 470);
        
        self.fields['footer_url'] = get_utf8_string(url)
        return self

    def setFooterHtml(self, html):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_footer_html"""
        if not (html):
            raise Error(create_invalid_value_message(html, "setFooterHtml", "html-to-pdf", 'The string must not be empty.', "set_footer_html"), 470);
        
        self.fields['footer_html'] = get_utf8_string(html)
        return self

    def setFooterHeight(self, height):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_footer_height"""
        if not re.match(r'(?i)^0$|^[0-9]*\.?[0-9]+(pt|px|mm|cm|in)$', height):
            raise Error(create_invalid_value_message(height, "setFooterHeight", "html-to-pdf", 'The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'.', "set_footer_height"), 470);
        
        self.fields['footer_height'] = get_utf8_string(height)
        return self

    def setZipFooterFilename(self, filename):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_zip_footer_filename"""
        self.fields['zip_footer_filename'] = get_utf8_string(filename)
        return self

    def setNoHeaderFooterHorizontalMargins(self, value):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_no_header_footer_horizontal_margins"""
        self.fields['no_header_footer_horizontal_margins'] = value
        return self

    def setExcludeHeaderOnPages(self, pages):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_exclude_header_on_pages"""
        if not re.match(r'^(?:\s*\-?\d+\s*,)*\s*\-?\d+\s*$', pages):
            raise Error(create_invalid_value_message(pages, "setExcludeHeaderOnPages", "html-to-pdf", 'A comma separated list of page numbers.', "set_exclude_header_on_pages"), 470);
        
        self.fields['exclude_header_on_pages'] = get_utf8_string(pages)
        return self

    def setExcludeFooterOnPages(self, pages):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_exclude_footer_on_pages"""
        if not re.match(r'^(?:\s*\-?\d+\s*,)*\s*\-?\d+\s*$', pages):
            raise Error(create_invalid_value_message(pages, "setExcludeFooterOnPages", "html-to-pdf", 'A comma separated list of page numbers.', "set_exclude_footer_on_pages"), 470);
        
        self.fields['exclude_footer_on_pages'] = get_utf8_string(pages)
        return self

    def setHeaderFooterScaleFactor(self, factor):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_header_footer_scale_factor"""
        if not (int(factor) >= 10 and int(factor) <= 500):
            raise Error(create_invalid_value_message(factor, "setHeaderFooterScaleFactor", "html-to-pdf", 'The accepted range is 10-500.', "set_header_footer_scale_factor"), 470);
        
        self.fields['header_footer_scale_factor'] = factor
        return self

    def setPageNumberingOffset(self, offset):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_page_numbering_offset"""
        self.fields['page_numbering_offset'] = offset
        return self

    def setPageWatermark(self, watermark):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_page_watermark"""
        if not (os.path.isfile(watermark) and os.path.getsize(watermark)):
            raise Error(create_invalid_value_message(watermark, "setPageWatermark", "html-to-pdf", 'The file must exist and not be empty.', "set_page_watermark"), 470);
        
        self.files['page_watermark'] = get_utf8_string(watermark)
        return self

    def setPageWatermarkUrl(self, url):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_page_watermark_url"""
        if not re.match(r'(?i)^https?://.*$', url):
            raise Error(create_invalid_value_message(url, "setPageWatermarkUrl", "html-to-pdf", 'Supported protocols are http:// and https://.', "set_page_watermark_url"), 470);
        
        self.fields['page_watermark_url'] = get_utf8_string(url)
        return self

    def setMultipageWatermark(self, watermark):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_multipage_watermark"""
        if not (os.path.isfile(watermark) and os.path.getsize(watermark)):
            raise Error(create_invalid_value_message(watermark, "setMultipageWatermark", "html-to-pdf", 'The file must exist and not be empty.', "set_multipage_watermark"), 470);
        
        self.files['multipage_watermark'] = get_utf8_string(watermark)
        return self

    def setMultipageWatermarkUrl(self, url):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_multipage_watermark_url"""
        if not re.match(r'(?i)^https?://.*$', url):
            raise Error(create_invalid_value_message(url, "setMultipageWatermarkUrl", "html-to-pdf", 'Supported protocols are http:// and https://.', "set_multipage_watermark_url"), 470);
        
        self.fields['multipage_watermark_url'] = get_utf8_string(url)
        return self

    def setPageBackground(self, background):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_page_background"""
        if not (os.path.isfile(background) and os.path.getsize(background)):
            raise Error(create_invalid_value_message(background, "setPageBackground", "html-to-pdf", 'The file must exist and not be empty.', "set_page_background"), 470);
        
        self.files['page_background'] = get_utf8_string(background)
        return self

    def setPageBackgroundUrl(self, url):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_page_background_url"""
        if not re.match(r'(?i)^https?://.*$', url):
            raise Error(create_invalid_value_message(url, "setPageBackgroundUrl", "html-to-pdf", 'Supported protocols are http:// and https://.', "set_page_background_url"), 470);
        
        self.fields['page_background_url'] = get_utf8_string(url)
        return self

    def setMultipageBackground(self, background):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_multipage_background"""
        if not (os.path.isfile(background) and os.path.getsize(background)):
            raise Error(create_invalid_value_message(background, "setMultipageBackground", "html-to-pdf", 'The file must exist and not be empty.', "set_multipage_background"), 470);
        
        self.files['multipage_background'] = get_utf8_string(background)
        return self

    def setMultipageBackgroundUrl(self, url):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_multipage_background_url"""
        if not re.match(r'(?i)^https?://.*$', url):
            raise Error(create_invalid_value_message(url, "setMultipageBackgroundUrl", "html-to-pdf", 'Supported protocols are http:// and https://.', "set_multipage_background_url"), 470);
        
        self.fields['multipage_background_url'] = get_utf8_string(url)
        return self

    def setPageBackgroundColor(self, color):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_page_background_color"""
        if not re.match(r'^[0-9a-fA-F]{6,8}$', color):
            raise Error(create_invalid_value_message(color, "setPageBackgroundColor", "html-to-pdf", 'The value must be in RRGGBB or RRGGBBAA hexadecimal format.', "set_page_background_color"), 470);
        
        self.fields['page_background_color'] = get_utf8_string(color)
        return self

    def setUsePrintMedia(self, value):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_use_print_media"""
        self.fields['use_print_media'] = value
        return self

    def setNoBackground(self, value):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_no_background"""
        self.fields['no_background'] = value
        return self

    def setDisableJavascript(self, value):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_disable_javascript"""
        self.fields['disable_javascript'] = value
        return self

    def setDisableImageLoading(self, value):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_disable_image_loading"""
        self.fields['disable_image_loading'] = value
        return self

    def setDisableRemoteFonts(self, value):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_disable_remote_fonts"""
        self.fields['disable_remote_fonts'] = value
        return self

    def setUseMobileUserAgent(self, value):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_use_mobile_user_agent"""
        self.fields['use_mobile_user_agent'] = value
        return self

    def setLoadIframes(self, iframes):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_load_iframes"""
        if not re.match(r'(?i)^(all|same-origin|none)$', iframes):
            raise Error(create_invalid_value_message(iframes, "setLoadIframes", "html-to-pdf", 'Allowed values are all, same-origin, none.', "set_load_iframes"), 470);
        
        self.fields['load_iframes'] = get_utf8_string(iframes)
        return self

    def setBlockAds(self, value):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_block_ads"""
        self.fields['block_ads'] = value
        return self

    def setDefaultEncoding(self, encoding):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_default_encoding"""
        self.fields['default_encoding'] = get_utf8_string(encoding)
        return self

    def setLocale(self, locale):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_locale"""
        self.fields['locale'] = get_utf8_string(locale)
        return self

    def setHttpAuthUserName(self, user_name):

        self.fields['http_auth_user_name'] = get_utf8_string(user_name)
        return self

    def setHttpAuthPassword(self, password):

        self.fields['http_auth_password'] = get_utf8_string(password)
        return self

    def setHttpAuth(self, user_name, password):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_http_auth"""
        self.setHttpAuthUserName(user_name)
        self.setHttpAuthPassword(password)
        return self

    def setCookies(self, cookies):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_cookies"""
        self.fields['cookies'] = get_utf8_string(cookies)
        return self

    def setVerifySslCertificates(self, value):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_verify_ssl_certificates"""
        self.fields['verify_ssl_certificates'] = value
        return self

    def setFailOnMainUrlError(self, fail_on_error):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_fail_on_main_url_error"""
        self.fields['fail_on_main_url_error'] = fail_on_error
        return self

    def setFailOnAnyUrlError(self, fail_on_error):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_fail_on_any_url_error"""
        self.fields['fail_on_any_url_error'] = fail_on_error
        return self

    def setNoXpdfcrowdHeader(self, value):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_no_xpdfcrowd_header"""
        self.fields['no_xpdfcrowd_header'] = value
        return self

    def setCssPageRuleMode(self, mode):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_css_page_rule_mode"""
        if not re.match(r'(?i)^(default|mode1|mode2)$', mode):
            raise Error(create_invalid_value_message(mode, "setCssPageRuleMode", "html-to-pdf", 'Allowed values are default, mode1, mode2.', "set_css_page_rule_mode"), 470);
        
        self.fields['css_page_rule_mode'] = get_utf8_string(mode)
        return self

    def setCustomCss(self, css):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_custom_css"""
        if not (css):
            raise Error(create_invalid_value_message(css, "setCustomCss", "html-to-pdf", 'The string must not be empty.', "set_custom_css"), 470);
        
        self.fields['custom_css'] = get_utf8_string(css)
        return self

    def setCustomJavascript(self, javascript):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_custom_javascript"""
        if not (javascript):
            raise Error(create_invalid_value_message(javascript, "setCustomJavascript", "html-to-pdf", 'The string must not be empty.', "set_custom_javascript"), 470);
        
        self.fields['custom_javascript'] = get_utf8_string(javascript)
        return self

    def setOnLoadJavascript(self, javascript):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_on_load_javascript"""
        if not (javascript):
            raise Error(create_invalid_value_message(javascript, "setOnLoadJavascript", "html-to-pdf", 'The string must not be empty.', "set_on_load_javascript"), 470);
        
        self.fields['on_load_javascript'] = get_utf8_string(javascript)
        return self

    def setCustomHttpHeader(self, header):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_custom_http_header"""
        if not re.match(r'^.+:.+$', header):
            raise Error(create_invalid_value_message(header, "setCustomHttpHeader", "html-to-pdf", 'A string containing the header name and value separated by a colon.', "set_custom_http_header"), 470);
        
        self.fields['custom_http_header'] = get_utf8_string(header)
        return self

    def setJavascriptDelay(self, delay):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_javascript_delay"""
        if not (int(delay) >= 0):
            raise Error(create_invalid_value_message(delay, "setJavascriptDelay", "html-to-pdf", 'Must be a positive integer or 0.', "set_javascript_delay"), 470);
        
        self.fields['javascript_delay'] = delay
        return self

    def setElementToConvert(self, selectors):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_element_to_convert"""
        if not (selectors):
            raise Error(create_invalid_value_message(selectors, "setElementToConvert", "html-to-pdf", 'The string must not be empty.', "set_element_to_convert"), 470);
        
        self.fields['element_to_convert'] = get_utf8_string(selectors)
        return self

    def setElementToConvertMode(self, mode):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_element_to_convert_mode"""
        if not re.match(r'(?i)^(cut-out|remove-siblings|hide-siblings)$', mode):
            raise Error(create_invalid_value_message(mode, "setElementToConvertMode", "html-to-pdf", 'Allowed values are cut-out, remove-siblings, hide-siblings.', "set_element_to_convert_mode"), 470);
        
        self.fields['element_to_convert_mode'] = get_utf8_string(mode)
        return self

    def setWaitForElement(self, selectors):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_wait_for_element"""
        if not (selectors):
            raise Error(create_invalid_value_message(selectors, "setWaitForElement", "html-to-pdf", 'The string must not be empty.', "set_wait_for_element"), 470);
        
        self.fields['wait_for_element'] = get_utf8_string(selectors)
        return self

    def setAutoDetectElementToConvert(self, value):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_auto_detect_element_to_convert"""
        self.fields['auto_detect_element_to_convert'] = value
        return self

    def setReadabilityEnhancements(self, enhancements):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_readability_enhancements"""
        if not re.match(r'(?i)^(none|readability-v1|readability-v2|readability-v3|readability-v4)$', enhancements):
            raise Error(create_invalid_value_message(enhancements, "setReadabilityEnhancements", "html-to-pdf", 'Allowed values are none, readability-v1, readability-v2, readability-v3, readability-v4.', "set_readability_enhancements"), 470);
        
        self.fields['readability_enhancements'] = get_utf8_string(enhancements)
        return self

    def setViewportWidth(self, width):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_viewport_width"""
        if not (int(width) >= 96 and int(width) <= 65000):
            raise Error(create_invalid_value_message(width, "setViewportWidth", "html-to-pdf", 'The accepted range is 96-65000.', "set_viewport_width"), 470);
        
        self.fields['viewport_width'] = width
        return self

    def setViewportHeight(self, height):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_viewport_height"""
        if not (int(height) > 0):
            raise Error(create_invalid_value_message(height, "setViewportHeight", "html-to-pdf", 'Must be a positive integer.', "set_viewport_height"), 470);
        
        self.fields['viewport_height'] = height
        return self

    def setViewport(self, width, height):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_viewport"""
        self.setViewportWidth(width)
        self.setViewportHeight(height)
        return self

    def setRenderingMode(self, mode):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_rendering_mode"""
        if not re.match(r'(?i)^(default|viewport)$', mode):
            raise Error(create_invalid_value_message(mode, "setRenderingMode", "html-to-pdf", 'Allowed values are default, viewport.', "set_rendering_mode"), 470);
        
        self.fields['rendering_mode'] = get_utf8_string(mode)
        return self

    def setSmartScalingMode(self, mode):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_smart_scaling_mode"""
        if not re.match(r'(?i)^(default|disabled|viewport-fit|content-fit|single-page-fit|single-page-fit-ex|mode1)$', mode):
            raise Error(create_invalid_value_message(mode, "setSmartScalingMode", "html-to-pdf", 'Allowed values are default, disabled, viewport-fit, content-fit, single-page-fit, single-page-fit-ex, mode1.', "set_smart_scaling_mode"), 470);
        
        self.fields['smart_scaling_mode'] = get_utf8_string(mode)
        return self

    def setScaleFactor(self, factor):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_scale_factor"""
        if not (int(factor) >= 10 and int(factor) <= 500):
            raise Error(create_invalid_value_message(factor, "setScaleFactor", "html-to-pdf", 'The accepted range is 10-500.', "set_scale_factor"), 470);
        
        self.fields['scale_factor'] = factor
        return self

    def setJpegQuality(self, quality):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_jpeg_quality"""
        if not (int(quality) >= 1 and int(quality) <= 100):
            raise Error(create_invalid_value_message(quality, "setJpegQuality", "html-to-pdf", 'The accepted range is 1-100.', "set_jpeg_quality"), 470);
        
        self.fields['jpeg_quality'] = quality
        return self

    def setConvertImagesToJpeg(self, images):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_convert_images_to_jpeg"""
        if not re.match(r'(?i)^(none|opaque|all)$', images):
            raise Error(create_invalid_value_message(images, "setConvertImagesToJpeg", "html-to-pdf", 'Allowed values are none, opaque, all.', "set_convert_images_to_jpeg"), 470);
        
        self.fields['convert_images_to_jpeg'] = get_utf8_string(images)
        return self

    def setImageDpi(self, dpi):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_image_dpi"""
        if not (int(dpi) >= 0):
            raise Error(create_invalid_value_message(dpi, "setImageDpi", "html-to-pdf", 'Must be a positive integer or 0.', "set_image_dpi"), 470);
        
        self.fields['image_dpi'] = dpi
        return self

    def setEnablePdfForms(self, value):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_enable_pdf_forms"""
        self.fields['enable_pdf_forms'] = value
        return self

    def setLinearize(self, value):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_linearize"""
        self.fields['linearize'] = value
        return self

    def setEncrypt(self, value):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_encrypt"""
        self.fields['encrypt'] = value
        return self

    def setUserPassword(self, password):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_user_password"""
        self.fields['user_password'] = get_utf8_string(password)
        return self

    def setOwnerPassword(self, password):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_owner_password"""
        self.fields['owner_password'] = get_utf8_string(password)
        return self

    def setNoPrint(self, value):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_no_print"""
        self.fields['no_print'] = value
        return self

    def setNoModify(self, value):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_no_modify"""
        self.fields['no_modify'] = value
        return self

    def setNoCopy(self, value):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_no_copy"""
        self.fields['no_copy'] = value
        return self

    def setTitle(self, title):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_title"""
        self.fields['title'] = get_utf8_string(title)
        return self

    def setSubject(self, subject):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_subject"""
        self.fields['subject'] = get_utf8_string(subject)
        return self

    def setAuthor(self, author):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_author"""
        self.fields['author'] = get_utf8_string(author)
        return self

    def setKeywords(self, keywords):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_keywords"""
        self.fields['keywords'] = get_utf8_string(keywords)
        return self

    def setExtractMetaTags(self, value):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_extract_meta_tags"""
        self.fields['extract_meta_tags'] = value
        return self

    def setConformance(self, conformance):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_conformance"""
        if not re.match(r'(?i)^(PDF/A-2a|PDF/A-2b|PDF/A-2u|PDF/A-3a|PDF/A-3b|PDF/A-3u|PDF/A-4|PDF/A-4e|PDF/A-4f)$', conformance):
            raise Error(create_invalid_value_message(conformance, "setConformance", "html-to-pdf", 'Allowed values are PDF/A-2a, PDF/A-2b, PDF/A-2u, PDF/A-3a, PDF/A-3b, PDF/A-3u, PDF/A-4, PDF/A-4e, PDF/A-4f.', "set_conformance"), 470);
        
        self.fields['conformance'] = get_utf8_string(conformance)
        return self

    def setTaggedPdf(self, value):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_tagged_pdf"""
        self.fields['tagged_pdf'] = value
        return self

    def addAttachment(self, attachment):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#add_attachment"""
        if not (os.path.isfile(attachment) and os.path.getsize(attachment)):
            raise Error(create_invalid_value_message(attachment, "addAttachment", "html-to-pdf", 'The file must exist and not be empty.', "add_attachment"), 470);
        
        self.files['attachment_{0}'.format(self.file_id)] = attachment
        self.file_id += 1
        return self

    def setPageLayout(self, layout):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_page_layout"""
        if not re.match(r'(?i)^(single-page|one-column|two-column-left|two-column-right)$', layout):
            raise Error(create_invalid_value_message(layout, "setPageLayout", "html-to-pdf", 'Allowed values are single-page, one-column, two-column-left, two-column-right.', "set_page_layout"), 470);
        
        self.fields['page_layout'] = get_utf8_string(layout)
        return self

    def setPageMode(self, mode):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_page_mode"""
        if not re.match(r'(?i)^(full-screen|thumbnails|outlines)$', mode):
            raise Error(create_invalid_value_message(mode, "setPageMode", "html-to-pdf", 'Allowed values are full-screen, thumbnails, outlines.', "set_page_mode"), 470);
        
        self.fields['page_mode'] = get_utf8_string(mode)
        return self

    def setInitialZoomType(self, zoom_type):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_initial_zoom_type"""
        if not re.match(r'(?i)^(fit-width|fit-height|fit-page)$', zoom_type):
            raise Error(create_invalid_value_message(zoom_type, "setInitialZoomType", "html-to-pdf", 'Allowed values are fit-width, fit-height, fit-page.', "set_initial_zoom_type"), 470);
        
        self.fields['initial_zoom_type'] = get_utf8_string(zoom_type)
        return self

    def setInitialPage(self, page):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_initial_page"""
        if not (int(page) > 0):
            raise Error(create_invalid_value_message(page, "setInitialPage", "html-to-pdf", 'Must be a positive integer.', "set_initial_page"), 470);
        
        self.fields['initial_page'] = page
        return self

    def setInitialZoom(self, zoom):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_initial_zoom"""
        if not (int(zoom) > 0):
            raise Error(create_invalid_value_message(zoom, "setInitialZoom", "html-to-pdf", 'Must be a positive integer.', "set_initial_zoom"), 470);
        
        self.fields['initial_zoom'] = zoom
        return self

    def setHideToolbar(self, value):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_hide_toolbar"""
        self.fields['hide_toolbar'] = value
        return self

    def setHideMenubar(self, value):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_hide_menubar"""
        self.fields['hide_menubar'] = value
        return self

    def setHideWindowUi(self, value):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_hide_window_ui"""
        self.fields['hide_window_ui'] = value
        return self

    def setFitWindow(self, value):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_fit_window"""
        self.fields['fit_window'] = value
        return self

    def setCenterWindow(self, value):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_center_window"""
        self.fields['center_window'] = value
        return self

    def setDisplayTitle(self, value):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_display_title"""
        self.fields['display_title'] = value
        return self

    def setRightToLeft(self, value):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_right_to_left"""
        self.fields['right_to_left'] = value
        return self

    def setDataString(self, data_string):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_data_string"""
        self.fields['data_string'] = get_utf8_string(data_string)
        return self

    def setDataFile(self, data_file):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_data_file"""
        self.files['data_file'] = get_utf8_string(data_file)
        return self

    def setDataFormat(self, data_format):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_data_format"""
        if not re.match(r'(?i)^(auto|json|xml|yaml|csv)$', data_format):
            raise Error(create_invalid_value_message(data_format, "setDataFormat", "html-to-pdf", 'Allowed values are auto, json, xml, yaml, csv.', "set_data_format"), 470);
        
        self.fields['data_format'] = get_utf8_string(data_format)
        return self

    def setDataEncoding(self, encoding):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_data_encoding"""
        self.fields['data_encoding'] = get_utf8_string(encoding)
        return self

    def setDataIgnoreUndefined(self, value):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_data_ignore_undefined"""
        self.fields['data_ignore_undefined'] = value
        return self

    def setDataAutoEscape(self, value):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_data_auto_escape"""
        self.fields['data_auto_escape'] = value
        return self

    def setDataTrimBlocks(self, value):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_data_trim_blocks"""
        self.fields['data_trim_blocks'] = value
        return self

    def setDataVariableMarkers(self, markers):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_data_variable_markers"""
        if not re.match(r'(?i)^(standard|square|angle)$', markers):
            raise Error(create_invalid_value_message(markers, "setDataVariableMarkers", "html-to-pdf", 'Allowed values are standard, square, angle.', "set_data_variable_markers"), 470);
        
        self.fields['data_variable_markers'] = get_utf8_string(markers)
        return self

    def setDataOptions(self, options):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_data_options"""
        self.fields['data_options'] = get_utf8_string(options)
        return self

    def setDebugLog(self, value):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_debug_log"""
        self.fields['debug_log'] = value
        return self

    def getDebugLogUrl(self):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#get_debug_log_url"""
        return self.helper.getDebugLogUrl()

    def getRemainingCreditCount(self):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#get_remaining_credit_count"""
        return self.helper.getRemainingCreditCount()

    def getConsumedCreditCount(self):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#get_consumed_credit_count"""
        return self.helper.getConsumedCreditCount()

    def getJobId(self):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#get_job_id"""
        return self.helper.getJobId()

    def getPageCount(self):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#get_page_count"""
        return self.helper.getPageCount()

    def getTotalPageCount(self):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#get_total_page_count"""
        return self.helper.getTotalPageCount()

    def getOutputSize(self):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#get_output_size"""
        return self.helper.getOutputSize()

    def getVersion(self):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#get_version"""
        return 'client {0}, API v2, converter {1}'.format(CLIENT_VERSION, self.helper.getConverterVersion())

    def setTag(self, tag):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_tag"""
        self.fields['tag'] = get_utf8_string(tag)
        return self

    def setHttpProxy(self, proxy):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_http_proxy"""
        if not re.match(r'(?i)^([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z0-9]{1,}:\d+$', proxy):
            raise Error(create_invalid_value_message(proxy, "setHttpProxy", "html-to-pdf", 'The value must have format DOMAIN_OR_IP_ADDRESS:PORT.', "set_http_proxy"), 470);
        
        self.fields['http_proxy'] = get_utf8_string(proxy)
        return self

    def setHttpsProxy(self, proxy):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_https_proxy"""
        if not re.match(r'(?i)^([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z0-9]{1,}:\d+$', proxy):
            raise Error(create_invalid_value_message(proxy, "setHttpsProxy", "html-to-pdf", 'The value must have format DOMAIN_OR_IP_ADDRESS:PORT.', "set_https_proxy"), 470);
        
        self.fields['https_proxy'] = get_utf8_string(proxy)
        return self

    def setClientCertificate(self, certificate):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_client_certificate"""
        if not (os.path.isfile(certificate) and os.path.getsize(certificate)):
            raise Error(create_invalid_value_message(certificate, "setClientCertificate", "html-to-pdf", 'The file must exist and not be empty.', "set_client_certificate"), 470);
        
        self.files['client_certificate'] = get_utf8_string(certificate)
        return self

    def setClientCertificatePassword(self, password):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_client_certificate_password"""
        self.fields['client_certificate_password'] = get_utf8_string(password)
        return self

    def setLayoutDpi(self, dpi):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_layout_dpi"""
        if not (int(dpi) >= 72 and int(dpi) <= 600):
            raise Error(create_invalid_value_message(dpi, "setLayoutDpi", "html-to-pdf", 'The accepted range is 72-600.', "set_layout_dpi"), 470);
        
        self.fields['layout_dpi'] = dpi
        return self

    def setContentAreaX(self, x):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_content_area_x"""
        if not re.match(r'(?i)^0$|^\-?[0-9]*\.?[0-9]+(pt|px|mm|cm|in)$', x):
            raise Error(create_invalid_value_message(x, "setContentAreaX", "html-to-pdf", 'The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'. It may contain a negative value.', "set_content_area_x"), 470);
        
        self.fields['content_area_x'] = get_utf8_string(x)
        return self

    def setContentAreaY(self, y):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_content_area_y"""
        if not re.match(r'(?i)^0$|^\-?[0-9]*\.?[0-9]+(pt|px|mm|cm|in)$', y):
            raise Error(create_invalid_value_message(y, "setContentAreaY", "html-to-pdf", 'The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'. It may contain a negative value.', "set_content_area_y"), 470);
        
        self.fields['content_area_y'] = get_utf8_string(y)
        return self

    def setContentAreaWidth(self, width):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_content_area_width"""
        if not re.match(r'(?i)^0$|^[0-9]*\.?[0-9]+(pt|px|mm|cm|in)$', width):
            raise Error(create_invalid_value_message(width, "setContentAreaWidth", "html-to-pdf", 'The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'.', "set_content_area_width"), 470);
        
        self.fields['content_area_width'] = get_utf8_string(width)
        return self

    def setContentAreaHeight(self, height):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_content_area_height"""
        if not re.match(r'(?i)^0$|^[0-9]*\.?[0-9]+(pt|px|mm|cm|in)$', height):
            raise Error(create_invalid_value_message(height, "setContentAreaHeight", "html-to-pdf", 'The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'.', "set_content_area_height"), 470);
        
        self.fields['content_area_height'] = get_utf8_string(height)
        return self

    def setContentArea(self, x, y, width, height):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_content_area"""
        self.setContentAreaX(x)
        self.setContentAreaY(y)
        self.setContentAreaWidth(width)
        self.setContentAreaHeight(height)
        return self

    def setContentsMatrix(self, matrix):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_contents_matrix"""
        self.fields['contents_matrix'] = get_utf8_string(matrix)
        return self

    def setHeaderMatrix(self, matrix):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_header_matrix"""
        self.fields['header_matrix'] = get_utf8_string(matrix)
        return self

    def setFooterMatrix(self, matrix):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_footer_matrix"""
        self.fields['footer_matrix'] = get_utf8_string(matrix)
        return self

    def setDisablePageHeightOptimization(self, value):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_disable_page_height_optimization"""
        self.fields['disable_page_height_optimization'] = value
        return self

    def setMainDocumentCssAnnotation(self, value):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_main_document_css_annotation"""
        self.fields['main_document_css_annotation'] = value
        return self

    def setHeaderFooterCssAnnotation(self, value):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_header_footer_css_annotation"""
        self.fields['header_footer_css_annotation'] = value
        return self

    def setMaxLoadingTime(self, max_time):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_max_loading_time"""
        if not (int(max_time) >= 10 and int(max_time) <= 30):
            raise Error(create_invalid_value_message(max_time, "setMaxLoadingTime", "html-to-pdf", 'The accepted range is 10-30.', "set_max_loading_time"), 470);
        
        self.fields['max_loading_time'] = max_time
        return self

    def setConversionConfig(self, json_string):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_conversion_config"""
        self.fields['conversion_config'] = get_utf8_string(json_string)
        return self

    def setConversionConfigFile(self, filepath):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_conversion_config_file"""
        if not (os.path.isfile(filepath) and os.path.getsize(filepath)):
            raise Error(create_invalid_value_message(filepath, "setConversionConfigFile", "html-to-pdf", 'The file must exist and not be empty.', "set_conversion_config_file"), 470);
        
        self.files['conversion_config_file'] = get_utf8_string(filepath)
        return self

    def setSubprocessReferrer(self, referrer):

        self.fields['subprocess_referrer'] = get_utf8_string(referrer)
        return self

    def setConverterUserAgent(self, agent):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_converter_user_agent"""
        self.fields['converter_user_agent'] = get_utf8_string(agent)
        return self

    def setConverterVersion(self, version):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_converter_version"""
        if not re.match(r'(?i)^(24.04|20.10|18.10|latest)$', version):
            raise Error(create_invalid_value_message(version, "setConverterVersion", "html-to-pdf", 'Allowed values are 24.04, 20.10, 18.10, latest.', "set_converter_version"), 470);
        
        self.helper.setConverterVersion(version)
        return self

    def setUseHttp(self, value):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_use_http"""
        self.helper.setUseHttp(value)
        return self

    def setClientUserAgent(self, agent):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_client_user_agent"""
        self.helper.setUserAgent(agent)
        return self

    def setUserAgent(self, agent):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_user_agent"""
        self.helper.setUserAgent(agent)
        return self

    def setProxy(self, host, port, user_name, password):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_proxy"""
        self.helper.setProxy(host, port, user_name, password)
        return self

    def setRetryCount(self, count):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#set_retry_count"""
        self.helper.setRetryCount(count)
        return self

class HtmlToImageClient:
    """Conversion from HTML to image.

    https://pdfcrowd.com/api/html-to-image-python/"""

    def __init__(self, user_name, api_key):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#__init__"""
        self.helper = ConnectionHelper(user_name, api_key)
        self.fields = {
            'input_format': 'html',
            'output_format': 'png'
        }
        self.file_id = 1
        self.files = {}
        self.raw_data = {}

    def setOutputFormat(self, output_format):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#set_output_format"""
        if not re.match(r'(?i)^(png|jpg|gif|tiff|bmp|ico|ppm|pgm|pbm|pnm|psb|pct|ras|tga|sgi|sun|webp)$', output_format):
            raise Error(create_invalid_value_message(output_format, "setOutputFormat", "html-to-image", 'Allowed values are png, jpg, gif, tiff, bmp, ico, ppm, pgm, pbm, pnm, psb, pct, ras, tga, sgi, sun, webp.', "set_output_format"), 470);
        
        self.fields['output_format'] = get_utf8_string(output_format)
        return self

    def convertUrl(self, url):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#convert_url"""
        if not re.match(r'(?i)^https?://.*$', url):
            raise Error(create_invalid_value_message(url, "convertUrl", "html-to-image", 'Supported protocols are http:// and https://.', "convert_url"), 470);
        
        self.helper.reset_input(self.fields, self.files, self.raw_data)
        self.fields['url'] = get_utf8_string(url)
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertUrlToStream(self, url, out_stream):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#convert_url_to_stream"""
        if not re.match(r'(?i)^https?://.*$', url):
            raise Error(create_invalid_value_message(url, "convertUrlToStream::url", "html-to-image", 'Supported protocols are http:// and https://.', "convert_url_to_stream"), 470);
        
        self.helper.reset_input(self.fields, self.files, self.raw_data)
        self.fields['url'] = get_utf8_string(url)
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertUrlToFile(self, url, file_path):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#convert_url_to_file"""
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "convertUrlToFile::file_path", "html-to-image", 'The string must not be empty.', "convert_url_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        succeeded = False
        try:
            self.convertUrlToStream(url,output_file)
            succeeded = True
        finally:
            if succeeded:
                output_file.close()
            else:
                try:
                    output_file.close()
                except BaseException:
                    pass
                try:
                    os.remove(file_path)
                except OSError:
                    pass

    def convertFile(self, file):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#convert_file"""
        if not (os.path.isfile(file) and os.path.getsize(file)):
            raise Error(create_invalid_value_message(file, "convertFile", "html-to-image", 'The file must exist and not be empty.', "convert_file"), 470);
        
        self.helper.reset_input(self.fields, self.files, self.raw_data)
        self.files['file'] = get_utf8_string(file)
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertFileToStream(self, file, out_stream):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#convert_file_to_stream"""
        if not (os.path.isfile(file) and os.path.getsize(file)):
            raise Error(create_invalid_value_message(file, "convertFileToStream::file", "html-to-image", 'The file must exist and not be empty.', "convert_file_to_stream"), 470);
        
        self.helper.reset_input(self.fields, self.files, self.raw_data)
        self.files['file'] = get_utf8_string(file)
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertFileToFile(self, file, file_path):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#convert_file_to_file"""
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "convertFileToFile::file_path", "html-to-image", 'The string must not be empty.', "convert_file_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        succeeded = False
        try:
            self.convertFileToStream(file,output_file)
            succeeded = True
        finally:
            if succeeded:
                output_file.close()
            else:
                try:
                    output_file.close()
                except BaseException:
                    pass
                try:
                    os.remove(file_path)
                except OSError:
                    pass

    def convertString(self, text):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#convert_string"""
        if not (text):
            raise Error(create_invalid_value_message(text, "convertString", "html-to-image", 'The string must not be empty.', "convert_string"), 470);
        
        self.helper.reset_input(self.fields, self.files, self.raw_data)
        self.fields['text'] = get_utf8_string(text)
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertStringToStream(self, text, out_stream):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#convert_string_to_stream"""
        if not (text):
            raise Error(create_invalid_value_message(text, "convertStringToStream::text", "html-to-image", 'The string must not be empty.', "convert_string_to_stream"), 470);
        
        self.helper.reset_input(self.fields, self.files, self.raw_data)
        self.fields['text'] = get_utf8_string(text)
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertStringToFile(self, text, file_path):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#convert_string_to_file"""
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "convertStringToFile::file_path", "html-to-image", 'The string must not be empty.', "convert_string_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        succeeded = False
        try:
            self.convertStringToStream(text,output_file)
            succeeded = True
        finally:
            if succeeded:
                output_file.close()
            else:
                try:
                    output_file.close()
                except BaseException:
                    pass
                try:
                    os.remove(file_path)
                except OSError:
                    pass

    def convertStream(self, in_stream):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#convert_stream"""
        self.helper.reset_input(self.fields, self.files, self.raw_data)
        self.raw_data['stream'] = in_stream.read()
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertStreamToStream(self, in_stream, out_stream):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#convert_stream_to_stream"""
        self.helper.reset_input(self.fields, self.files, self.raw_data)
        self.raw_data['stream'] = in_stream.read()
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertStreamToFile(self, in_stream, file_path):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#convert_stream_to_file"""
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "convertStreamToFile::file_path", "html-to-image", 'The string must not be empty.', "convert_stream_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        succeeded = False
        try:
            self.convertStreamToStream(in_stream,output_file)
            succeeded = True
        finally:
            if succeeded:
                output_file.close()
            else:
                try:
                    output_file.close()
                except BaseException:
                    pass
                try:
                    os.remove(file_path)
                except OSError:
                    pass

    def setZipMainFilename(self, filename):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#set_zip_main_filename"""
        self.fields['zip_main_filename'] = get_utf8_string(filename)
        return self

    def setScreenshotWidth(self, width):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#set_screenshot_width"""
        if not (int(width) >= 96 and int(width) <= 65000):
            raise Error(create_invalid_value_message(width, "setScreenshotWidth", "html-to-image", 'The accepted range is 96-65000.', "set_screenshot_width"), 470);
        
        self.fields['screenshot_width'] = width
        return self

    def setScreenshotHeight(self, height):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#set_screenshot_height"""
        if not (int(height) > 0):
            raise Error(create_invalid_value_message(height, "setScreenshotHeight", "html-to-image", 'Must be a positive integer.', "set_screenshot_height"), 470);
        
        self.fields['screenshot_height'] = height
        return self

    def setScaleFactor(self, factor):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#set_scale_factor"""
        if not (int(factor) > 0):
            raise Error(create_invalid_value_message(factor, "setScaleFactor", "html-to-image", 'Must be a positive integer.', "set_scale_factor"), 470);
        
        self.fields['scale_factor'] = factor
        return self

    def setBackgroundColor(self, color):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#set_background_color"""
        if not re.match(r'^[0-9a-fA-F]{6,8}$', color):
            raise Error(create_invalid_value_message(color, "setBackgroundColor", "html-to-image", 'The value must be in RRGGBB or RRGGBBAA hexadecimal format.', "set_background_color"), 470);
        
        self.fields['background_color'] = get_utf8_string(color)
        return self

    def setUsePrintMedia(self, value):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#set_use_print_media"""
        self.fields['use_print_media'] = value
        return self

    def setNoBackground(self, value):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#set_no_background"""
        self.fields['no_background'] = value
        return self

    def setDisableJavascript(self, value):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#set_disable_javascript"""
        self.fields['disable_javascript'] = value
        return self

    def setDisableImageLoading(self, value):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#set_disable_image_loading"""
        self.fields['disable_image_loading'] = value
        return self

    def setDisableRemoteFonts(self, value):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#set_disable_remote_fonts"""
        self.fields['disable_remote_fonts'] = value
        return self

    def setUseMobileUserAgent(self, value):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#set_use_mobile_user_agent"""
        self.fields['use_mobile_user_agent'] = value
        return self

    def setLoadIframes(self, iframes):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#set_load_iframes"""
        if not re.match(r'(?i)^(all|same-origin|none)$', iframes):
            raise Error(create_invalid_value_message(iframes, "setLoadIframes", "html-to-image", 'Allowed values are all, same-origin, none.', "set_load_iframes"), 470);
        
        self.fields['load_iframes'] = get_utf8_string(iframes)
        return self

    def setBlockAds(self, value):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#set_block_ads"""
        self.fields['block_ads'] = value
        return self

    def setDefaultEncoding(self, encoding):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#set_default_encoding"""
        self.fields['default_encoding'] = get_utf8_string(encoding)
        return self

    def setLocale(self, locale):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#set_locale"""
        self.fields['locale'] = get_utf8_string(locale)
        return self

    def setHttpAuthUserName(self, user_name):

        self.fields['http_auth_user_name'] = get_utf8_string(user_name)
        return self

    def setHttpAuthPassword(self, password):

        self.fields['http_auth_password'] = get_utf8_string(password)
        return self

    def setHttpAuth(self, user_name, password):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#set_http_auth"""
        self.setHttpAuthUserName(user_name)
        self.setHttpAuthPassword(password)
        return self

    def setCookies(self, cookies):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#set_cookies"""
        self.fields['cookies'] = get_utf8_string(cookies)
        return self

    def setVerifySslCertificates(self, value):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#set_verify_ssl_certificates"""
        self.fields['verify_ssl_certificates'] = value
        return self

    def setFailOnMainUrlError(self, fail_on_error):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#set_fail_on_main_url_error"""
        self.fields['fail_on_main_url_error'] = fail_on_error
        return self

    def setFailOnAnyUrlError(self, fail_on_error):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#set_fail_on_any_url_error"""
        self.fields['fail_on_any_url_error'] = fail_on_error
        return self

    def setNoXpdfcrowdHeader(self, value):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#set_no_xpdfcrowd_header"""
        self.fields['no_xpdfcrowd_header'] = value
        return self

    def setCustomCss(self, css):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#set_custom_css"""
        if not (css):
            raise Error(create_invalid_value_message(css, "setCustomCss", "html-to-image", 'The string must not be empty.', "set_custom_css"), 470);
        
        self.fields['custom_css'] = get_utf8_string(css)
        return self

    def setCustomJavascript(self, javascript):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#set_custom_javascript"""
        if not (javascript):
            raise Error(create_invalid_value_message(javascript, "setCustomJavascript", "html-to-image", 'The string must not be empty.', "set_custom_javascript"), 470);
        
        self.fields['custom_javascript'] = get_utf8_string(javascript)
        return self

    def setOnLoadJavascript(self, javascript):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#set_on_load_javascript"""
        if not (javascript):
            raise Error(create_invalid_value_message(javascript, "setOnLoadJavascript", "html-to-image", 'The string must not be empty.', "set_on_load_javascript"), 470);
        
        self.fields['on_load_javascript'] = get_utf8_string(javascript)
        return self

    def setCustomHttpHeader(self, header):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#set_custom_http_header"""
        if not re.match(r'^.+:.+$', header):
            raise Error(create_invalid_value_message(header, "setCustomHttpHeader", "html-to-image", 'A string containing the header name and value separated by a colon.', "set_custom_http_header"), 470);
        
        self.fields['custom_http_header'] = get_utf8_string(header)
        return self

    def setJavascriptDelay(self, delay):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#set_javascript_delay"""
        if not (int(delay) >= 0):
            raise Error(create_invalid_value_message(delay, "setJavascriptDelay", "html-to-image", 'Must be a positive integer or 0.', "set_javascript_delay"), 470);
        
        self.fields['javascript_delay'] = delay
        return self

    def setElementToConvert(self, selectors):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#set_element_to_convert"""
        if not (selectors):
            raise Error(create_invalid_value_message(selectors, "setElementToConvert", "html-to-image", 'The string must not be empty.', "set_element_to_convert"), 470);
        
        self.fields['element_to_convert'] = get_utf8_string(selectors)
        return self

    def setElementToConvertMode(self, mode):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#set_element_to_convert_mode"""
        if not re.match(r'(?i)^(cut-out|remove-siblings|hide-siblings)$', mode):
            raise Error(create_invalid_value_message(mode, "setElementToConvertMode", "html-to-image", 'Allowed values are cut-out, remove-siblings, hide-siblings.', "set_element_to_convert_mode"), 470);
        
        self.fields['element_to_convert_mode'] = get_utf8_string(mode)
        return self

    def setWaitForElement(self, selectors):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#set_wait_for_element"""
        if not (selectors):
            raise Error(create_invalid_value_message(selectors, "setWaitForElement", "html-to-image", 'The string must not be empty.', "set_wait_for_element"), 470);
        
        self.fields['wait_for_element'] = get_utf8_string(selectors)
        return self

    def setAutoDetectElementToConvert(self, value):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#set_auto_detect_element_to_convert"""
        self.fields['auto_detect_element_to_convert'] = value
        return self

    def setReadabilityEnhancements(self, enhancements):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#set_readability_enhancements"""
        if not re.match(r'(?i)^(none|readability-v1|readability-v2|readability-v3|readability-v4)$', enhancements):
            raise Error(create_invalid_value_message(enhancements, "setReadabilityEnhancements", "html-to-image", 'Allowed values are none, readability-v1, readability-v2, readability-v3, readability-v4.', "set_readability_enhancements"), 470);
        
        self.fields['readability_enhancements'] = get_utf8_string(enhancements)
        return self

    def setDataString(self, data_string):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#set_data_string"""
        self.fields['data_string'] = get_utf8_string(data_string)
        return self

    def setDataFile(self, data_file):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#set_data_file"""
        self.files['data_file'] = get_utf8_string(data_file)
        return self

    def setDataFormat(self, data_format):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#set_data_format"""
        if not re.match(r'(?i)^(auto|json|xml|yaml|csv)$', data_format):
            raise Error(create_invalid_value_message(data_format, "setDataFormat", "html-to-image", 'Allowed values are auto, json, xml, yaml, csv.', "set_data_format"), 470);
        
        self.fields['data_format'] = get_utf8_string(data_format)
        return self

    def setDataEncoding(self, encoding):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#set_data_encoding"""
        self.fields['data_encoding'] = get_utf8_string(encoding)
        return self

    def setDataIgnoreUndefined(self, value):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#set_data_ignore_undefined"""
        self.fields['data_ignore_undefined'] = value
        return self

    def setDataAutoEscape(self, value):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#set_data_auto_escape"""
        self.fields['data_auto_escape'] = value
        return self

    def setDataTrimBlocks(self, value):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#set_data_trim_blocks"""
        self.fields['data_trim_blocks'] = value
        return self

    def setDataVariableMarkers(self, markers):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#set_data_variable_markers"""
        if not re.match(r'(?i)^(standard|square|angle)$', markers):
            raise Error(create_invalid_value_message(markers, "setDataVariableMarkers", "html-to-image", 'Allowed values are standard, square, angle.', "set_data_variable_markers"), 470);
        
        self.fields['data_variable_markers'] = get_utf8_string(markers)
        return self

    def setDataOptions(self, options):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#set_data_options"""
        self.fields['data_options'] = get_utf8_string(options)
        return self

    def setDebugLog(self, value):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#set_debug_log"""
        self.fields['debug_log'] = value
        return self

    def getDebugLogUrl(self):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#get_debug_log_url"""
        return self.helper.getDebugLogUrl()

    def getRemainingCreditCount(self):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#get_remaining_credit_count"""
        return self.helper.getRemainingCreditCount()

    def getConsumedCreditCount(self):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#get_consumed_credit_count"""
        return self.helper.getConsumedCreditCount()

    def getJobId(self):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#get_job_id"""
        return self.helper.getJobId()

    def getOutputSize(self):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#get_output_size"""
        return self.helper.getOutputSize()

    def getVersion(self):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#get_version"""
        return 'client {0}, API v2, converter {1}'.format(CLIENT_VERSION, self.helper.getConverterVersion())

    def setTag(self, tag):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#set_tag"""
        self.fields['tag'] = get_utf8_string(tag)
        return self

    def setHttpProxy(self, proxy):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#set_http_proxy"""
        if not re.match(r'(?i)^([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z0-9]{1,}:\d+$', proxy):
            raise Error(create_invalid_value_message(proxy, "setHttpProxy", "html-to-image", 'The value must have format DOMAIN_OR_IP_ADDRESS:PORT.', "set_http_proxy"), 470);
        
        self.fields['http_proxy'] = get_utf8_string(proxy)
        return self

    def setHttpsProxy(self, proxy):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#set_https_proxy"""
        if not re.match(r'(?i)^([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z0-9]{1,}:\d+$', proxy):
            raise Error(create_invalid_value_message(proxy, "setHttpsProxy", "html-to-image", 'The value must have format DOMAIN_OR_IP_ADDRESS:PORT.', "set_https_proxy"), 470);
        
        self.fields['https_proxy'] = get_utf8_string(proxy)
        return self

    def setClientCertificate(self, certificate):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#set_client_certificate"""
        if not (os.path.isfile(certificate) and os.path.getsize(certificate)):
            raise Error(create_invalid_value_message(certificate, "setClientCertificate", "html-to-image", 'The file must exist and not be empty.', "set_client_certificate"), 470);
        
        self.files['client_certificate'] = get_utf8_string(certificate)
        return self

    def setClientCertificatePassword(self, password):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#set_client_certificate_password"""
        self.fields['client_certificate_password'] = get_utf8_string(password)
        return self

    def setMaxLoadingTime(self, max_time):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#set_max_loading_time"""
        if not (int(max_time) >= 10 and int(max_time) <= 30):
            raise Error(create_invalid_value_message(max_time, "setMaxLoadingTime", "html-to-image", 'The accepted range is 10-30.', "set_max_loading_time"), 470);
        
        self.fields['max_loading_time'] = max_time
        return self

    def setSubprocessReferrer(self, referrer):

        self.fields['subprocess_referrer'] = get_utf8_string(referrer)
        return self

    def setConverterUserAgent(self, agent):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#set_converter_user_agent"""
        self.fields['converter_user_agent'] = get_utf8_string(agent)
        return self

    def setConverterVersion(self, version):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#set_converter_version"""
        if not re.match(r'(?i)^(24.04|20.10|18.10|latest)$', version):
            raise Error(create_invalid_value_message(version, "setConverterVersion", "html-to-image", 'Allowed values are 24.04, 20.10, 18.10, latest.', "set_converter_version"), 470);
        
        self.helper.setConverterVersion(version)
        return self

    def setUseHttp(self, value):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#set_use_http"""
        self.helper.setUseHttp(value)
        return self

    def setClientUserAgent(self, agent):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#set_client_user_agent"""
        self.helper.setUserAgent(agent)
        return self

    def setUserAgent(self, agent):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#set_user_agent"""
        self.helper.setUserAgent(agent)
        return self

    def setProxy(self, host, port, user_name, password):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#set_proxy"""
        self.helper.setProxy(host, port, user_name, password)
        return self

    def setRetryCount(self, count):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#set_retry_count"""
        self.helper.setRetryCount(count)
        return self

class ImageToImageClient:
    """Conversion from one image format to another image format.

    https://pdfcrowd.com/api/image-to-image-python/"""

    def __init__(self, user_name, api_key):
        """https://pdfcrowd.com/api/image-to-image-python/ref/#__init__"""
        self.helper = ConnectionHelper(user_name, api_key)
        self.fields = {
            'input_format': 'image',
            'output_format': 'png'
        }
        self.file_id = 1
        self.files = {}
        self.raw_data = {}

    def convertUrl(self, url):
        """https://pdfcrowd.com/api/image-to-image-python/ref/#convert_url"""
        if not re.match(r'(?i)^https?://.*$', url):
            raise Error(create_invalid_value_message(url, "convertUrl", "image-to-image", 'Supported protocols are http:// and https://.', "convert_url"), 470);
        
        self.helper.reset_input(self.fields, self.files, self.raw_data)
        self.fields['url'] = get_utf8_string(url)
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertUrlToStream(self, url, out_stream):
        """https://pdfcrowd.com/api/image-to-image-python/ref/#convert_url_to_stream"""
        if not re.match(r'(?i)^https?://.*$', url):
            raise Error(create_invalid_value_message(url, "convertUrlToStream::url", "image-to-image", 'Supported protocols are http:// and https://.', "convert_url_to_stream"), 470);
        
        self.helper.reset_input(self.fields, self.files, self.raw_data)
        self.fields['url'] = get_utf8_string(url)
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertUrlToFile(self, url, file_path):
        """https://pdfcrowd.com/api/image-to-image-python/ref/#convert_url_to_file"""
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "convertUrlToFile::file_path", "image-to-image", 'The string must not be empty.', "convert_url_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        succeeded = False
        try:
            self.convertUrlToStream(url,output_file)
            succeeded = True
        finally:
            if succeeded:
                output_file.close()
            else:
                try:
                    output_file.close()
                except BaseException:
                    pass
                try:
                    os.remove(file_path)
                except OSError:
                    pass

    def convertFile(self, file):
        """https://pdfcrowd.com/api/image-to-image-python/ref/#convert_file"""
        if not (os.path.isfile(file) and os.path.getsize(file)):
            raise Error(create_invalid_value_message(file, "convertFile", "image-to-image", 'The file must exist and not be empty.', "convert_file"), 470);
        
        self.helper.reset_input(self.fields, self.files, self.raw_data)
        self.files['file'] = get_utf8_string(file)
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertFileToStream(self, file, out_stream):
        """https://pdfcrowd.com/api/image-to-image-python/ref/#convert_file_to_stream"""
        if not (os.path.isfile(file) and os.path.getsize(file)):
            raise Error(create_invalid_value_message(file, "convertFileToStream::file", "image-to-image", 'The file must exist and not be empty.', "convert_file_to_stream"), 470);
        
        self.helper.reset_input(self.fields, self.files, self.raw_data)
        self.files['file'] = get_utf8_string(file)
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertFileToFile(self, file, file_path):
        """https://pdfcrowd.com/api/image-to-image-python/ref/#convert_file_to_file"""
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "convertFileToFile::file_path", "image-to-image", 'The string must not be empty.', "convert_file_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        succeeded = False
        try:
            self.convertFileToStream(file,output_file)
            succeeded = True
        finally:
            if succeeded:
                output_file.close()
            else:
                try:
                    output_file.close()
                except BaseException:
                    pass
                try:
                    os.remove(file_path)
                except OSError:
                    pass

    def convertRawData(self, data):
        """https://pdfcrowd.com/api/image-to-image-python/ref/#convert_raw_data"""
        self.helper.reset_input(self.fields, self.files, self.raw_data)
        self.raw_data['file'] = data
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertRawDataToStream(self, data, out_stream):
        """https://pdfcrowd.com/api/image-to-image-python/ref/#convert_raw_data_to_stream"""
        self.helper.reset_input(self.fields, self.files, self.raw_data)
        self.raw_data['file'] = data
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertRawDataToFile(self, data, file_path):
        """https://pdfcrowd.com/api/image-to-image-python/ref/#convert_raw_data_to_file"""
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "convertRawDataToFile::file_path", "image-to-image", 'The string must not be empty.', "convert_raw_data_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        succeeded = False
        try:
            self.convertRawDataToStream(data,output_file)
            succeeded = True
        finally:
            if succeeded:
                output_file.close()
            else:
                try:
                    output_file.close()
                except BaseException:
                    pass
                try:
                    os.remove(file_path)
                except OSError:
                    pass

    def convertStream(self, in_stream):
        """https://pdfcrowd.com/api/image-to-image-python/ref/#convert_stream"""
        self.helper.reset_input(self.fields, self.files, self.raw_data)
        self.raw_data['stream'] = in_stream.read()
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertStreamToStream(self, in_stream, out_stream):
        """https://pdfcrowd.com/api/image-to-image-python/ref/#convert_stream_to_stream"""
        self.helper.reset_input(self.fields, self.files, self.raw_data)
        self.raw_data['stream'] = in_stream.read()
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertStreamToFile(self, in_stream, file_path):
        """https://pdfcrowd.com/api/image-to-image-python/ref/#convert_stream_to_file"""
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "convertStreamToFile::file_path", "image-to-image", 'The string must not be empty.', "convert_stream_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        succeeded = False
        try:
            self.convertStreamToStream(in_stream,output_file)
            succeeded = True
        finally:
            if succeeded:
                output_file.close()
            else:
                try:
                    output_file.close()
                except BaseException:
                    pass
                try:
                    os.remove(file_path)
                except OSError:
                    pass

    def setOutputFormat(self, output_format):
        """https://pdfcrowd.com/api/image-to-image-python/ref/#set_output_format"""
        if not re.match(r'(?i)^(png|jpg|gif|tiff|bmp|ico|ppm|pgm|pbm|pnm|psb|pct|ras|tga|sgi|sun|webp)$', output_format):
            raise Error(create_invalid_value_message(output_format, "setOutputFormat", "image-to-image", 'Allowed values are png, jpg, gif, tiff, bmp, ico, ppm, pgm, pbm, pnm, psb, pct, ras, tga, sgi, sun, webp.', "set_output_format"), 470);
        
        self.fields['output_format'] = get_utf8_string(output_format)
        return self

    def setResize(self, resize):
        """https://pdfcrowd.com/api/image-to-image-python/ref/#set_resize"""
        self.fields['resize'] = get_utf8_string(resize)
        return self

    def setRotate(self, rotate):
        """https://pdfcrowd.com/api/image-to-image-python/ref/#set_rotate"""
        self.fields['rotate'] = get_utf8_string(rotate)
        return self

    def setCropAreaX(self, x):
        """https://pdfcrowd.com/api/image-to-image-python/ref/#set_crop_area_x"""
        if not re.match(r'(?i)^0$|^[0-9]*\.?[0-9]+(pt|px|mm|cm|in)$', x):
            raise Error(create_invalid_value_message(x, "setCropAreaX", "image-to-image", 'The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'.', "set_crop_area_x"), 470);
        
        self.fields['crop_area_x'] = get_utf8_string(x)
        return self

    def setCropAreaY(self, y):
        """https://pdfcrowd.com/api/image-to-image-python/ref/#set_crop_area_y"""
        if not re.match(r'(?i)^0$|^[0-9]*\.?[0-9]+(pt|px|mm|cm|in)$', y):
            raise Error(create_invalid_value_message(y, "setCropAreaY", "image-to-image", 'The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'.', "set_crop_area_y"), 470);
        
        self.fields['crop_area_y'] = get_utf8_string(y)
        return self

    def setCropAreaWidth(self, width):
        """https://pdfcrowd.com/api/image-to-image-python/ref/#set_crop_area_width"""
        if not re.match(r'(?i)^0$|^[0-9]*\.?[0-9]+(pt|px|mm|cm|in)$', width):
            raise Error(create_invalid_value_message(width, "setCropAreaWidth", "image-to-image", 'The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'.', "set_crop_area_width"), 470);
        
        self.fields['crop_area_width'] = get_utf8_string(width)
        return self

    def setCropAreaHeight(self, height):
        """https://pdfcrowd.com/api/image-to-image-python/ref/#set_crop_area_height"""
        if not re.match(r'(?i)^0$|^[0-9]*\.?[0-9]+(pt|px|mm|cm|in)$', height):
            raise Error(create_invalid_value_message(height, "setCropAreaHeight", "image-to-image", 'The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'.', "set_crop_area_height"), 470);
        
        self.fields['crop_area_height'] = get_utf8_string(height)
        return self

    def setCropArea(self, x, y, width, height):
        """https://pdfcrowd.com/api/image-to-image-python/ref/#set_crop_area"""
        self.setCropAreaX(x)
        self.setCropAreaY(y)
        self.setCropAreaWidth(width)
        self.setCropAreaHeight(height)
        return self

    def setRemoveBorders(self, value):
        """https://pdfcrowd.com/api/image-to-image-python/ref/#set_remove_borders"""
        self.fields['remove_borders'] = value
        return self

    def setCanvasSize(self, size):
        """https://pdfcrowd.com/api/image-to-image-python/ref/#set_canvas_size"""
        if not re.match(r'(?i)^(A0|A1|A2|A3|A4|A5|A6|Letter)$', size):
            raise Error(create_invalid_value_message(size, "setCanvasSize", "image-to-image", 'Allowed values are A0, A1, A2, A3, A4, A5, A6, Letter.', "set_canvas_size"), 470);
        
        self.fields['canvas_size'] = get_utf8_string(size)
        return self

    def setCanvasWidth(self, width):
        """https://pdfcrowd.com/api/image-to-image-python/ref/#set_canvas_width"""
        if not re.match(r'(?i)^0$|^[0-9]*\.?[0-9]+(pt|px|mm|cm|in)$', width):
            raise Error(create_invalid_value_message(width, "setCanvasWidth", "image-to-image", 'The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'.', "set_canvas_width"), 470);
        
        self.fields['canvas_width'] = get_utf8_string(width)
        return self

    def setCanvasHeight(self, height):
        """https://pdfcrowd.com/api/image-to-image-python/ref/#set_canvas_height"""
        if not re.match(r'(?i)^0$|^[0-9]*\.?[0-9]+(pt|px|mm|cm|in)$', height):
            raise Error(create_invalid_value_message(height, "setCanvasHeight", "image-to-image", 'The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'.', "set_canvas_height"), 470);
        
        self.fields['canvas_height'] = get_utf8_string(height)
        return self

    def setCanvasDimensions(self, width, height):
        """https://pdfcrowd.com/api/image-to-image-python/ref/#set_canvas_dimensions"""
        self.setCanvasWidth(width)
        self.setCanvasHeight(height)
        return self

    def setOrientation(self, orientation):
        """https://pdfcrowd.com/api/image-to-image-python/ref/#set_orientation"""
        if not re.match(r'(?i)^(landscape|portrait)$', orientation):
            raise Error(create_invalid_value_message(orientation, "setOrientation", "image-to-image", 'Allowed values are landscape, portrait.', "set_orientation"), 470);
        
        self.fields['orientation'] = get_utf8_string(orientation)
        return self

    def setPosition(self, position):
        """https://pdfcrowd.com/api/image-to-image-python/ref/#set_position"""
        if not re.match(r'(?i)^(center|top|bottom|left|right|top-left|top-right|bottom-left|bottom-right)$', position):
            raise Error(create_invalid_value_message(position, "setPosition", "image-to-image", 'Allowed values are center, top, bottom, left, right, top-left, top-right, bottom-left, bottom-right.', "set_position"), 470);
        
        self.fields['position'] = get_utf8_string(position)
        return self

    def setPrintCanvasMode(self, mode):
        """https://pdfcrowd.com/api/image-to-image-python/ref/#set_print_canvas_mode"""
        if not re.match(r'(?i)^(default|fit|stretch)$', mode):
            raise Error(create_invalid_value_message(mode, "setPrintCanvasMode", "image-to-image", 'Allowed values are default, fit, stretch.', "set_print_canvas_mode"), 470);
        
        self.fields['print_canvas_mode'] = get_utf8_string(mode)
        return self

    def setMarginTop(self, top):
        """https://pdfcrowd.com/api/image-to-image-python/ref/#set_margin_top"""
        if not re.match(r'(?i)^0$|^[0-9]*\.?[0-9]+(pt|px|mm|cm|in)$', top):
            raise Error(create_invalid_value_message(top, "setMarginTop", "image-to-image", 'The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'.', "set_margin_top"), 470);
        
        self.fields['margin_top'] = get_utf8_string(top)
        return self

    def setMarginRight(self, right):
        """https://pdfcrowd.com/api/image-to-image-python/ref/#set_margin_right"""
        if not re.match(r'(?i)^0$|^[0-9]*\.?[0-9]+(pt|px|mm|cm|in)$', right):
            raise Error(create_invalid_value_message(right, "setMarginRight", "image-to-image", 'The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'.', "set_margin_right"), 470);
        
        self.fields['margin_right'] = get_utf8_string(right)
        return self

    def setMarginBottom(self, bottom):
        """https://pdfcrowd.com/api/image-to-image-python/ref/#set_margin_bottom"""
        if not re.match(r'(?i)^0$|^[0-9]*\.?[0-9]+(pt|px|mm|cm|in)$', bottom):
            raise Error(create_invalid_value_message(bottom, "setMarginBottom", "image-to-image", 'The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'.', "set_margin_bottom"), 470);
        
        self.fields['margin_bottom'] = get_utf8_string(bottom)
        return self

    def setMarginLeft(self, left):
        """https://pdfcrowd.com/api/image-to-image-python/ref/#set_margin_left"""
        if not re.match(r'(?i)^0$|^[0-9]*\.?[0-9]+(pt|px|mm|cm|in)$', left):
            raise Error(create_invalid_value_message(left, "setMarginLeft", "image-to-image", 'The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'.', "set_margin_left"), 470);
        
        self.fields['margin_left'] = get_utf8_string(left)
        return self

    def setMargins(self, top, right, bottom, left):
        """https://pdfcrowd.com/api/image-to-image-python/ref/#set_margins"""
        self.setMarginTop(top)
        self.setMarginRight(right)
        self.setMarginBottom(bottom)
        self.setMarginLeft(left)
        return self

    def setCanvasBackgroundColor(self, color):
        """https://pdfcrowd.com/api/image-to-image-python/ref/#set_canvas_background_color"""
        if not re.match(r'^[0-9a-fA-F]{6,8}$', color):
            raise Error(create_invalid_value_message(color, "setCanvasBackgroundColor", "image-to-image", 'The value must be in RRGGBB or RRGGBBAA hexadecimal format.', "set_canvas_background_color"), 470);
        
        self.fields['canvas_background_color'] = get_utf8_string(color)
        return self

    def setDpi(self, dpi):
        """https://pdfcrowd.com/api/image-to-image-python/ref/#set_dpi"""
        self.fields['dpi'] = dpi
        return self

    def setDebugLog(self, value):
        """https://pdfcrowd.com/api/image-to-image-python/ref/#set_debug_log"""
        self.fields['debug_log'] = value
        return self

    def getDebugLogUrl(self):
        """https://pdfcrowd.com/api/image-to-image-python/ref/#get_debug_log_url"""
        return self.helper.getDebugLogUrl()

    def getRemainingCreditCount(self):
        """https://pdfcrowd.com/api/image-to-image-python/ref/#get_remaining_credit_count"""
        return self.helper.getRemainingCreditCount()

    def getConsumedCreditCount(self):
        """https://pdfcrowd.com/api/image-to-image-python/ref/#get_consumed_credit_count"""
        return self.helper.getConsumedCreditCount()

    def getJobId(self):
        """https://pdfcrowd.com/api/image-to-image-python/ref/#get_job_id"""
        return self.helper.getJobId()

    def getOutputSize(self):
        """https://pdfcrowd.com/api/image-to-image-python/ref/#get_output_size"""
        return self.helper.getOutputSize()

    def getVersion(self):
        """https://pdfcrowd.com/api/image-to-image-python/ref/#get_version"""
        return 'client {0}, API v2, converter {1}'.format(CLIENT_VERSION, self.helper.getConverterVersion())

    def setTag(self, tag):
        """https://pdfcrowd.com/api/image-to-image-python/ref/#set_tag"""
        self.fields['tag'] = get_utf8_string(tag)
        return self

    def setHttpProxy(self, proxy):
        """https://pdfcrowd.com/api/image-to-image-python/ref/#set_http_proxy"""
        if not re.match(r'(?i)^([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z0-9]{1,}:\d+$', proxy):
            raise Error(create_invalid_value_message(proxy, "setHttpProxy", "image-to-image", 'The value must have format DOMAIN_OR_IP_ADDRESS:PORT.', "set_http_proxy"), 470);
        
        self.fields['http_proxy'] = get_utf8_string(proxy)
        return self

    def setHttpsProxy(self, proxy):
        """https://pdfcrowd.com/api/image-to-image-python/ref/#set_https_proxy"""
        if not re.match(r'(?i)^([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z0-9]{1,}:\d+$', proxy):
            raise Error(create_invalid_value_message(proxy, "setHttpsProxy", "image-to-image", 'The value must have format DOMAIN_OR_IP_ADDRESS:PORT.', "set_https_proxy"), 470);
        
        self.fields['https_proxy'] = get_utf8_string(proxy)
        return self

    def setConverterVersion(self, version):
        """https://pdfcrowd.com/api/image-to-image-python/ref/#set_converter_version"""
        if not re.match(r'(?i)^(24.04|20.10|18.10|latest)$', version):
            raise Error(create_invalid_value_message(version, "setConverterVersion", "image-to-image", 'Allowed values are 24.04, 20.10, 18.10, latest.', "set_converter_version"), 470);
        
        self.helper.setConverterVersion(version)
        return self

    def setUseHttp(self, value):
        """https://pdfcrowd.com/api/image-to-image-python/ref/#set_use_http"""
        self.helper.setUseHttp(value)
        return self

    def setClientUserAgent(self, agent):
        """https://pdfcrowd.com/api/image-to-image-python/ref/#set_client_user_agent"""
        self.helper.setUserAgent(agent)
        return self

    def setUserAgent(self, agent):
        """https://pdfcrowd.com/api/image-to-image-python/ref/#set_user_agent"""
        self.helper.setUserAgent(agent)
        return self

    def setProxy(self, host, port, user_name, password):
        """https://pdfcrowd.com/api/image-to-image-python/ref/#set_proxy"""
        self.helper.setProxy(host, port, user_name, password)
        return self

    def setRetryCount(self, count):
        """https://pdfcrowd.com/api/image-to-image-python/ref/#set_retry_count"""
        self.helper.setRetryCount(count)
        return self

class PdfToPdfClient:
    """Conversion from PDF to PDF.

    https://pdfcrowd.com/api/pdf-to-pdf-python/"""

    def __init__(self, user_name, api_key):
        """https://pdfcrowd.com/api/pdf-to-pdf-python/ref/#__init__"""
        self.helper = ConnectionHelper(user_name, api_key)
        self.fields = {
            'input_format': 'pdf',
            'output_format': 'pdf'
        }
        self.file_id = 1
        self.files = {}
        self.raw_data = {}

    def setAction(self, action):
        """https://pdfcrowd.com/api/pdf-to-pdf-python/ref/#set_action"""
        if not re.match(r'(?i)^(join|shuffle|extract|delete)$', action):
            raise Error(create_invalid_value_message(action, "setAction", "pdf-to-pdf", 'Allowed values are join, shuffle, extract, delete.', "set_action"), 470);
        
        self.fields['action'] = get_utf8_string(action)
        return self

    def convert(self):
        """https://pdfcrowd.com/api/pdf-to-pdf-python/ref/#convert"""
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertToStream(self, out_stream):
        """https://pdfcrowd.com/api/pdf-to-pdf-python/ref/#convert_to_stream"""
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertToFile(self, file_path):
        """https://pdfcrowd.com/api/pdf-to-pdf-python/ref/#convert_to_file"""
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "convertToFile", "pdf-to-pdf", 'The string must not be empty.', "convert_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        succeeded = False
        try:
            self.convertToStream(output_file)
            succeeded = True
        finally:
            if succeeded:
                output_file.close()
            else:
                try:
                    output_file.close()
                except BaseException:
                    pass
                try:
                    os.remove(file_path)
                except OSError:
                    pass

    def addPdfFile(self, file_path):
        """https://pdfcrowd.com/api/pdf-to-pdf-python/ref/#add_pdf_file"""
        if not (os.path.isfile(file_path) and os.path.getsize(file_path)):
            raise Error(create_invalid_value_message(file_path, "addPdfFile", "pdf-to-pdf", 'The file must exist and not be empty.', "add_pdf_file"), 470);
        
        self.files['f_{0}'.format(self.file_id)] = file_path
        self.file_id += 1
        return self

    def addPdfRawData(self, data):
        """https://pdfcrowd.com/api/pdf-to-pdf-python/ref/#add_pdf_raw_data"""
        if not (data and len(data) > 300 and (data[0:4] == '%PDF' or data[0:4] == b'%PDF')):
            raise Error(create_invalid_value_message("raw PDF data", "addPdfRawData", "pdf-to-pdf", 'The input data must be PDF content.', "add_pdf_raw_data"), 470);
        
        self.raw_data['f_{0}'.format(self.file_id)] = data
        self.file_id += 1
        return self

    def setInputPdfPassword(self, password):
        """https://pdfcrowd.com/api/pdf-to-pdf-python/ref/#set_input_pdf_password"""
        self.fields['input_pdf_password'] = get_utf8_string(password)
        return self

    def setPageRange(self, pages):
        """https://pdfcrowd.com/api/pdf-to-pdf-python/ref/#set_page_range"""
        if not re.match(r'^(?:\s*(?:\d+|(?:\d*\s*\-\s*\d+)|(?:\d+\s*\-\s*\d*))\s*,\s*)*\s*(?:\d+|(?:\d*\s*\-\s*\d+)|(?:\d+\s*\-\s*\d*))\s*$', pages):
            raise Error(create_invalid_value_message(pages, "setPageRange", "pdf-to-pdf", 'A comma separated list of page numbers or ranges.', "set_page_range"), 470);
        
        self.fields['page_range'] = get_utf8_string(pages)
        return self

    def setPageWatermark(self, watermark):
        """https://pdfcrowd.com/api/pdf-to-pdf-python/ref/#set_page_watermark"""
        if not (os.path.isfile(watermark) and os.path.getsize(watermark)):
            raise Error(create_invalid_value_message(watermark, "setPageWatermark", "pdf-to-pdf", 'The file must exist and not be empty.', "set_page_watermark"), 470);
        
        self.files['page_watermark'] = get_utf8_string(watermark)
        return self

    def setPageWatermarkUrl(self, url):
        """https://pdfcrowd.com/api/pdf-to-pdf-python/ref/#set_page_watermark_url"""
        if not re.match(r'(?i)^https?://.*$', url):
            raise Error(create_invalid_value_message(url, "setPageWatermarkUrl", "pdf-to-pdf", 'Supported protocols are http:// and https://.', "set_page_watermark_url"), 470);
        
        self.fields['page_watermark_url'] = get_utf8_string(url)
        return self

    def setMultipageWatermark(self, watermark):
        """https://pdfcrowd.com/api/pdf-to-pdf-python/ref/#set_multipage_watermark"""
        if not (os.path.isfile(watermark) and os.path.getsize(watermark)):
            raise Error(create_invalid_value_message(watermark, "setMultipageWatermark", "pdf-to-pdf", 'The file must exist and not be empty.', "set_multipage_watermark"), 470);
        
        self.files['multipage_watermark'] = get_utf8_string(watermark)
        return self

    def setMultipageWatermarkUrl(self, url):
        """https://pdfcrowd.com/api/pdf-to-pdf-python/ref/#set_multipage_watermark_url"""
        if not re.match(r'(?i)^https?://.*$', url):
            raise Error(create_invalid_value_message(url, "setMultipageWatermarkUrl", "pdf-to-pdf", 'Supported protocols are http:// and https://.', "set_multipage_watermark_url"), 470);
        
        self.fields['multipage_watermark_url'] = get_utf8_string(url)
        return self

    def setPageBackground(self, background):
        """https://pdfcrowd.com/api/pdf-to-pdf-python/ref/#set_page_background"""
        if not (os.path.isfile(background) and os.path.getsize(background)):
            raise Error(create_invalid_value_message(background, "setPageBackground", "pdf-to-pdf", 'The file must exist and not be empty.', "set_page_background"), 470);
        
        self.files['page_background'] = get_utf8_string(background)
        return self

    def setPageBackgroundUrl(self, url):
        """https://pdfcrowd.com/api/pdf-to-pdf-python/ref/#set_page_background_url"""
        if not re.match(r'(?i)^https?://.*$', url):
            raise Error(create_invalid_value_message(url, "setPageBackgroundUrl", "pdf-to-pdf", 'Supported protocols are http:// and https://.', "set_page_background_url"), 470);
        
        self.fields['page_background_url'] = get_utf8_string(url)
        return self

    def setMultipageBackground(self, background):
        """https://pdfcrowd.com/api/pdf-to-pdf-python/ref/#set_multipage_background"""
        if not (os.path.isfile(background) and os.path.getsize(background)):
            raise Error(create_invalid_value_message(background, "setMultipageBackground", "pdf-to-pdf", 'The file must exist and not be empty.', "set_multipage_background"), 470);
        
        self.files['multipage_background'] = get_utf8_string(background)
        return self

    def setMultipageBackgroundUrl(self, url):
        """https://pdfcrowd.com/api/pdf-to-pdf-python/ref/#set_multipage_background_url"""
        if not re.match(r'(?i)^https?://.*$', url):
            raise Error(create_invalid_value_message(url, "setMultipageBackgroundUrl", "pdf-to-pdf", 'Supported protocols are http:// and https://.', "set_multipage_background_url"), 470);
        
        self.fields['multipage_background_url'] = get_utf8_string(url)
        return self

    def setLinearize(self, value):
        """https://pdfcrowd.com/api/pdf-to-pdf-python/ref/#set_linearize"""
        self.fields['linearize'] = value
        return self

    def setEncrypt(self, value):
        """https://pdfcrowd.com/api/pdf-to-pdf-python/ref/#set_encrypt"""
        self.fields['encrypt'] = value
        return self

    def setUserPassword(self, password):
        """https://pdfcrowd.com/api/pdf-to-pdf-python/ref/#set_user_password"""
        self.fields['user_password'] = get_utf8_string(password)
        return self

    def setOwnerPassword(self, password):
        """https://pdfcrowd.com/api/pdf-to-pdf-python/ref/#set_owner_password"""
        self.fields['owner_password'] = get_utf8_string(password)
        return self

    def setNoPrint(self, value):
        """https://pdfcrowd.com/api/pdf-to-pdf-python/ref/#set_no_print"""
        self.fields['no_print'] = value
        return self

    def setNoModify(self, value):
        """https://pdfcrowd.com/api/pdf-to-pdf-python/ref/#set_no_modify"""
        self.fields['no_modify'] = value
        return self

    def setNoCopy(self, value):
        """https://pdfcrowd.com/api/pdf-to-pdf-python/ref/#set_no_copy"""
        self.fields['no_copy'] = value
        return self

    def setTitle(self, title):
        """https://pdfcrowd.com/api/pdf-to-pdf-python/ref/#set_title"""
        self.fields['title'] = get_utf8_string(title)
        return self

    def setSubject(self, subject):
        """https://pdfcrowd.com/api/pdf-to-pdf-python/ref/#set_subject"""
        self.fields['subject'] = get_utf8_string(subject)
        return self

    def setAuthor(self, author):
        """https://pdfcrowd.com/api/pdf-to-pdf-python/ref/#set_author"""
        self.fields['author'] = get_utf8_string(author)
        return self

    def setKeywords(self, keywords):
        """https://pdfcrowd.com/api/pdf-to-pdf-python/ref/#set_keywords"""
        self.fields['keywords'] = get_utf8_string(keywords)
        return self

    def setUseMetadataFrom(self, index):
        """https://pdfcrowd.com/api/pdf-to-pdf-python/ref/#set_use_metadata_from"""
        if not (int(index) >= 0):
            raise Error(create_invalid_value_message(index, "setUseMetadataFrom", "pdf-to-pdf", 'Must be a positive integer or 0.', "set_use_metadata_from"), 470);
        
        self.fields['use_metadata_from'] = index
        return self

    def addAttachment(self, attachment):
        """https://pdfcrowd.com/api/pdf-to-pdf-python/ref/#add_attachment"""
        if not (os.path.isfile(attachment) and os.path.getsize(attachment)):
            raise Error(create_invalid_value_message(attachment, "addAttachment", "pdf-to-pdf", 'The file must exist and not be empty.', "add_attachment"), 470);
        
        self.files['attachment_{0}'.format(self.file_id)] = attachment
        self.file_id += 1
        return self

    def setPageLayout(self, layout):
        """https://pdfcrowd.com/api/pdf-to-pdf-python/ref/#set_page_layout"""
        if not re.match(r'(?i)^(single-page|one-column|two-column-left|two-column-right)$', layout):
            raise Error(create_invalid_value_message(layout, "setPageLayout", "pdf-to-pdf", 'Allowed values are single-page, one-column, two-column-left, two-column-right.', "set_page_layout"), 470);
        
        self.fields['page_layout'] = get_utf8_string(layout)
        return self

    def setPageMode(self, mode):
        """https://pdfcrowd.com/api/pdf-to-pdf-python/ref/#set_page_mode"""
        if not re.match(r'(?i)^(full-screen|thumbnails|outlines)$', mode):
            raise Error(create_invalid_value_message(mode, "setPageMode", "pdf-to-pdf", 'Allowed values are full-screen, thumbnails, outlines.', "set_page_mode"), 470);
        
        self.fields['page_mode'] = get_utf8_string(mode)
        return self

    def setInitialZoomType(self, zoom_type):
        """https://pdfcrowd.com/api/pdf-to-pdf-python/ref/#set_initial_zoom_type"""
        if not re.match(r'(?i)^(fit-width|fit-height|fit-page)$', zoom_type):
            raise Error(create_invalid_value_message(zoom_type, "setInitialZoomType", "pdf-to-pdf", 'Allowed values are fit-width, fit-height, fit-page.', "set_initial_zoom_type"), 470);
        
        self.fields['initial_zoom_type'] = get_utf8_string(zoom_type)
        return self

    def setInitialPage(self, page):
        """https://pdfcrowd.com/api/pdf-to-pdf-python/ref/#set_initial_page"""
        if not (int(page) > 0):
            raise Error(create_invalid_value_message(page, "setInitialPage", "pdf-to-pdf", 'Must be a positive integer.', "set_initial_page"), 470);
        
        self.fields['initial_page'] = page
        return self

    def setInitialZoom(self, zoom):
        """https://pdfcrowd.com/api/pdf-to-pdf-python/ref/#set_initial_zoom"""
        if not (int(zoom) > 0):
            raise Error(create_invalid_value_message(zoom, "setInitialZoom", "pdf-to-pdf", 'Must be a positive integer.', "set_initial_zoom"), 470);
        
        self.fields['initial_zoom'] = zoom
        return self

    def setHideToolbar(self, value):
        """https://pdfcrowd.com/api/pdf-to-pdf-python/ref/#set_hide_toolbar"""
        self.fields['hide_toolbar'] = value
        return self

    def setHideMenubar(self, value):
        """https://pdfcrowd.com/api/pdf-to-pdf-python/ref/#set_hide_menubar"""
        self.fields['hide_menubar'] = value
        return self

    def setHideWindowUi(self, value):
        """https://pdfcrowd.com/api/pdf-to-pdf-python/ref/#set_hide_window_ui"""
        self.fields['hide_window_ui'] = value
        return self

    def setFitWindow(self, value):
        """https://pdfcrowd.com/api/pdf-to-pdf-python/ref/#set_fit_window"""
        self.fields['fit_window'] = value
        return self

    def setCenterWindow(self, value):
        """https://pdfcrowd.com/api/pdf-to-pdf-python/ref/#set_center_window"""
        self.fields['center_window'] = value
        return self

    def setDisplayTitle(self, value):
        """https://pdfcrowd.com/api/pdf-to-pdf-python/ref/#set_display_title"""
        self.fields['display_title'] = value
        return self

    def setRightToLeft(self, value):
        """https://pdfcrowd.com/api/pdf-to-pdf-python/ref/#set_right_to_left"""
        self.fields['right_to_left'] = value
        return self

    def setDebugLog(self, value):
        """https://pdfcrowd.com/api/pdf-to-pdf-python/ref/#set_debug_log"""
        self.fields['debug_log'] = value
        return self

    def getDebugLogUrl(self):
        """https://pdfcrowd.com/api/pdf-to-pdf-python/ref/#get_debug_log_url"""
        return self.helper.getDebugLogUrl()

    def getRemainingCreditCount(self):
        """https://pdfcrowd.com/api/pdf-to-pdf-python/ref/#get_remaining_credit_count"""
        return self.helper.getRemainingCreditCount()

    def getConsumedCreditCount(self):
        """https://pdfcrowd.com/api/pdf-to-pdf-python/ref/#get_consumed_credit_count"""
        return self.helper.getConsumedCreditCount()

    def getJobId(self):
        """https://pdfcrowd.com/api/pdf-to-pdf-python/ref/#get_job_id"""
        return self.helper.getJobId()

    def getPageCount(self):
        """https://pdfcrowd.com/api/pdf-to-pdf-python/ref/#get_page_count"""
        return self.helper.getPageCount()

    def getOutputSize(self):
        """https://pdfcrowd.com/api/pdf-to-pdf-python/ref/#get_output_size"""
        return self.helper.getOutputSize()

    def getVersion(self):
        """https://pdfcrowd.com/api/pdf-to-pdf-python/ref/#get_version"""
        return 'client {0}, API v2, converter {1}'.format(CLIENT_VERSION, self.helper.getConverterVersion())

    def setTag(self, tag):
        """https://pdfcrowd.com/api/pdf-to-pdf-python/ref/#set_tag"""
        self.fields['tag'] = get_utf8_string(tag)
        return self

    def setConverterVersion(self, version):
        """https://pdfcrowd.com/api/pdf-to-pdf-python/ref/#set_converter_version"""
        if not re.match(r'(?i)^(24.04|20.10|18.10|latest)$', version):
            raise Error(create_invalid_value_message(version, "setConverterVersion", "pdf-to-pdf", 'Allowed values are 24.04, 20.10, 18.10, latest.', "set_converter_version"), 470);
        
        self.helper.setConverterVersion(version)
        return self

    def setUseHttp(self, value):
        """https://pdfcrowd.com/api/pdf-to-pdf-python/ref/#set_use_http"""
        self.helper.setUseHttp(value)
        return self

    def setClientUserAgent(self, agent):
        """https://pdfcrowd.com/api/pdf-to-pdf-python/ref/#set_client_user_agent"""
        self.helper.setUserAgent(agent)
        return self

    def setUserAgent(self, agent):
        """https://pdfcrowd.com/api/pdf-to-pdf-python/ref/#set_user_agent"""
        self.helper.setUserAgent(agent)
        return self

    def setProxy(self, host, port, user_name, password):
        """https://pdfcrowd.com/api/pdf-to-pdf-python/ref/#set_proxy"""
        self.helper.setProxy(host, port, user_name, password)
        return self

    def setRetryCount(self, count):
        """https://pdfcrowd.com/api/pdf-to-pdf-python/ref/#set_retry_count"""
        self.helper.setRetryCount(count)
        return self

class ImageToPdfClient:
    """Conversion from an image to PDF.

    https://pdfcrowd.com/api/image-to-pdf-python/"""

    def __init__(self, user_name, api_key):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#__init__"""
        self.helper = ConnectionHelper(user_name, api_key)
        self.fields = {
            'input_format': 'image',
            'output_format': 'pdf'
        }
        self.file_id = 1
        self.files = {}
        self.raw_data = {}

    def convertUrl(self, url):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#convert_url"""
        if not re.match(r'(?i)^https?://.*$', url):
            raise Error(create_invalid_value_message(url, "convertUrl", "image-to-pdf", 'Supported protocols are http:// and https://.', "convert_url"), 470);
        
        self.helper.reset_input(self.fields, self.files, self.raw_data)
        self.fields['url'] = get_utf8_string(url)
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertUrlToStream(self, url, out_stream):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#convert_url_to_stream"""
        if not re.match(r'(?i)^https?://.*$', url):
            raise Error(create_invalid_value_message(url, "convertUrlToStream::url", "image-to-pdf", 'Supported protocols are http:// and https://.', "convert_url_to_stream"), 470);
        
        self.helper.reset_input(self.fields, self.files, self.raw_data)
        self.fields['url'] = get_utf8_string(url)
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertUrlToFile(self, url, file_path):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#convert_url_to_file"""
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "convertUrlToFile::file_path", "image-to-pdf", 'The string must not be empty.', "convert_url_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        succeeded = False
        try:
            self.convertUrlToStream(url,output_file)
            succeeded = True
        finally:
            if succeeded:
                output_file.close()
            else:
                try:
                    output_file.close()
                except BaseException:
                    pass
                try:
                    os.remove(file_path)
                except OSError:
                    pass

    def convertFile(self, file):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#convert_file"""
        if not (os.path.isfile(file) and os.path.getsize(file)):
            raise Error(create_invalid_value_message(file, "convertFile", "image-to-pdf", 'The file must exist and not be empty.', "convert_file"), 470);
        
        self.helper.reset_input(self.fields, self.files, self.raw_data)
        self.files['file'] = get_utf8_string(file)
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertFileToStream(self, file, out_stream):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#convert_file_to_stream"""
        if not (os.path.isfile(file) and os.path.getsize(file)):
            raise Error(create_invalid_value_message(file, "convertFileToStream::file", "image-to-pdf", 'The file must exist and not be empty.', "convert_file_to_stream"), 470);
        
        self.helper.reset_input(self.fields, self.files, self.raw_data)
        self.files['file'] = get_utf8_string(file)
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertFileToFile(self, file, file_path):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#convert_file_to_file"""
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "convertFileToFile::file_path", "image-to-pdf", 'The string must not be empty.', "convert_file_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        succeeded = False
        try:
            self.convertFileToStream(file,output_file)
            succeeded = True
        finally:
            if succeeded:
                output_file.close()
            else:
                try:
                    output_file.close()
                except BaseException:
                    pass
                try:
                    os.remove(file_path)
                except OSError:
                    pass

    def convertRawData(self, data):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#convert_raw_data"""
        self.helper.reset_input(self.fields, self.files, self.raw_data)
        self.raw_data['file'] = data
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertRawDataToStream(self, data, out_stream):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#convert_raw_data_to_stream"""
        self.helper.reset_input(self.fields, self.files, self.raw_data)
        self.raw_data['file'] = data
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertRawDataToFile(self, data, file_path):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#convert_raw_data_to_file"""
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "convertRawDataToFile::file_path", "image-to-pdf", 'The string must not be empty.', "convert_raw_data_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        succeeded = False
        try:
            self.convertRawDataToStream(data,output_file)
            succeeded = True
        finally:
            if succeeded:
                output_file.close()
            else:
                try:
                    output_file.close()
                except BaseException:
                    pass
                try:
                    os.remove(file_path)
                except OSError:
                    pass

    def convertStream(self, in_stream):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#convert_stream"""
        self.helper.reset_input(self.fields, self.files, self.raw_data)
        self.raw_data['stream'] = in_stream.read()
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertStreamToStream(self, in_stream, out_stream):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#convert_stream_to_stream"""
        self.helper.reset_input(self.fields, self.files, self.raw_data)
        self.raw_data['stream'] = in_stream.read()
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertStreamToFile(self, in_stream, file_path):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#convert_stream_to_file"""
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "convertStreamToFile::file_path", "image-to-pdf", 'The string must not be empty.', "convert_stream_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        succeeded = False
        try:
            self.convertStreamToStream(in_stream,output_file)
            succeeded = True
        finally:
            if succeeded:
                output_file.close()
            else:
                try:
                    output_file.close()
                except BaseException:
                    pass
                try:
                    os.remove(file_path)
                except OSError:
                    pass

    def setResize(self, resize):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#set_resize"""
        self.fields['resize'] = get_utf8_string(resize)
        return self

    def setRotate(self, rotate):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#set_rotate"""
        self.fields['rotate'] = get_utf8_string(rotate)
        return self

    def setCropAreaX(self, x):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#set_crop_area_x"""
        if not re.match(r'(?i)^0$|^[0-9]*\.?[0-9]+(pt|px|mm|cm|in)$', x):
            raise Error(create_invalid_value_message(x, "setCropAreaX", "image-to-pdf", 'The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'.', "set_crop_area_x"), 470);
        
        self.fields['crop_area_x'] = get_utf8_string(x)
        return self

    def setCropAreaY(self, y):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#set_crop_area_y"""
        if not re.match(r'(?i)^0$|^[0-9]*\.?[0-9]+(pt|px|mm|cm|in)$', y):
            raise Error(create_invalid_value_message(y, "setCropAreaY", "image-to-pdf", 'The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'.', "set_crop_area_y"), 470);
        
        self.fields['crop_area_y'] = get_utf8_string(y)
        return self

    def setCropAreaWidth(self, width):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#set_crop_area_width"""
        if not re.match(r'(?i)^0$|^[0-9]*\.?[0-9]+(pt|px|mm|cm|in)$', width):
            raise Error(create_invalid_value_message(width, "setCropAreaWidth", "image-to-pdf", 'The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'.', "set_crop_area_width"), 470);
        
        self.fields['crop_area_width'] = get_utf8_string(width)
        return self

    def setCropAreaHeight(self, height):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#set_crop_area_height"""
        if not re.match(r'(?i)^0$|^[0-9]*\.?[0-9]+(pt|px|mm|cm|in)$', height):
            raise Error(create_invalid_value_message(height, "setCropAreaHeight", "image-to-pdf", 'The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'.', "set_crop_area_height"), 470);
        
        self.fields['crop_area_height'] = get_utf8_string(height)
        return self

    def setCropArea(self, x, y, width, height):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#set_crop_area"""
        self.setCropAreaX(x)
        self.setCropAreaY(y)
        self.setCropAreaWidth(width)
        self.setCropAreaHeight(height)
        return self

    def setRemoveBorders(self, value):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#set_remove_borders"""
        self.fields['remove_borders'] = value
        return self

    def setPageSize(self, size):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#set_page_size"""
        if not re.match(r'(?i)^(A0|A1|A2|A3|A4|A5|A6|Letter)$', size):
            raise Error(create_invalid_value_message(size, "setPageSize", "image-to-pdf", 'Allowed values are A0, A1, A2, A3, A4, A5, A6, Letter.', "set_page_size"), 470);
        
        self.fields['page_size'] = get_utf8_string(size)
        return self

    def setPageWidth(self, width):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#set_page_width"""
        if not re.match(r'(?i)^0$|^[0-9]*\.?[0-9]+(pt|px|mm|cm|in)$', width):
            raise Error(create_invalid_value_message(width, "setPageWidth", "image-to-pdf", 'The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'.', "set_page_width"), 470);
        
        self.fields['page_width'] = get_utf8_string(width)
        return self

    def setPageHeight(self, height):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#set_page_height"""
        if not re.match(r'(?i)^0$|^[0-9]*\.?[0-9]+(pt|px|mm|cm|in)$', height):
            raise Error(create_invalid_value_message(height, "setPageHeight", "image-to-pdf", 'The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'.', "set_page_height"), 470);
        
        self.fields['page_height'] = get_utf8_string(height)
        return self

    def setPageDimensions(self, width, height):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#set_page_dimensions"""
        self.setPageWidth(width)
        self.setPageHeight(height)
        return self

    def setOrientation(self, orientation):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#set_orientation"""
        if not re.match(r'(?i)^(landscape|portrait)$', orientation):
            raise Error(create_invalid_value_message(orientation, "setOrientation", "image-to-pdf", 'Allowed values are landscape, portrait.', "set_orientation"), 470);
        
        self.fields['orientation'] = get_utf8_string(orientation)
        return self

    def setPosition(self, position):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#set_position"""
        if not re.match(r'(?i)^(center|top|bottom|left|right|top-left|top-right|bottom-left|bottom-right)$', position):
            raise Error(create_invalid_value_message(position, "setPosition", "image-to-pdf", 'Allowed values are center, top, bottom, left, right, top-left, top-right, bottom-left, bottom-right.', "set_position"), 470);
        
        self.fields['position'] = get_utf8_string(position)
        return self

    def setPrintPageMode(self, mode):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#set_print_page_mode"""
        if not re.match(r'(?i)^(default|fit|stretch)$', mode):
            raise Error(create_invalid_value_message(mode, "setPrintPageMode", "image-to-pdf", 'Allowed values are default, fit, stretch.', "set_print_page_mode"), 470);
        
        self.fields['print_page_mode'] = get_utf8_string(mode)
        return self

    def setMarginTop(self, top):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#set_margin_top"""
        if not re.match(r'(?i)^0$|^[0-9]*\.?[0-9]+(pt|px|mm|cm|in)$', top):
            raise Error(create_invalid_value_message(top, "setMarginTop", "image-to-pdf", 'The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'.', "set_margin_top"), 470);
        
        self.fields['margin_top'] = get_utf8_string(top)
        return self

    def setMarginRight(self, right):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#set_margin_right"""
        if not re.match(r'(?i)^0$|^[0-9]*\.?[0-9]+(pt|px|mm|cm|in)$', right):
            raise Error(create_invalid_value_message(right, "setMarginRight", "image-to-pdf", 'The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'.', "set_margin_right"), 470);
        
        self.fields['margin_right'] = get_utf8_string(right)
        return self

    def setMarginBottom(self, bottom):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#set_margin_bottom"""
        if not re.match(r'(?i)^0$|^[0-9]*\.?[0-9]+(pt|px|mm|cm|in)$', bottom):
            raise Error(create_invalid_value_message(bottom, "setMarginBottom", "image-to-pdf", 'The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'.', "set_margin_bottom"), 470);
        
        self.fields['margin_bottom'] = get_utf8_string(bottom)
        return self

    def setMarginLeft(self, left):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#set_margin_left"""
        if not re.match(r'(?i)^0$|^[0-9]*\.?[0-9]+(pt|px|mm|cm|in)$', left):
            raise Error(create_invalid_value_message(left, "setMarginLeft", "image-to-pdf", 'The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'.', "set_margin_left"), 470);
        
        self.fields['margin_left'] = get_utf8_string(left)
        return self

    def setPageMargins(self, top, right, bottom, left):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#set_page_margins"""
        self.setMarginTop(top)
        self.setMarginRight(right)
        self.setMarginBottom(bottom)
        self.setMarginLeft(left)
        return self

    def setPageBackgroundColor(self, color):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#set_page_background_color"""
        if not re.match(r'^[0-9a-fA-F]{6,8}$', color):
            raise Error(create_invalid_value_message(color, "setPageBackgroundColor", "image-to-pdf", 'The value must be in RRGGBB or RRGGBBAA hexadecimal format.', "set_page_background_color"), 470);
        
        self.fields['page_background_color'] = get_utf8_string(color)
        return self

    def setDpi(self, dpi):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#set_dpi"""
        self.fields['dpi'] = dpi
        return self

    def setPageWatermark(self, watermark):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#set_page_watermark"""
        if not (os.path.isfile(watermark) and os.path.getsize(watermark)):
            raise Error(create_invalid_value_message(watermark, "setPageWatermark", "image-to-pdf", 'The file must exist and not be empty.', "set_page_watermark"), 470);
        
        self.files['page_watermark'] = get_utf8_string(watermark)
        return self

    def setPageWatermarkUrl(self, url):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#set_page_watermark_url"""
        if not re.match(r'(?i)^https?://.*$', url):
            raise Error(create_invalid_value_message(url, "setPageWatermarkUrl", "image-to-pdf", 'Supported protocols are http:// and https://.', "set_page_watermark_url"), 470);
        
        self.fields['page_watermark_url'] = get_utf8_string(url)
        return self

    def setMultipageWatermark(self, watermark):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#set_multipage_watermark"""
        if not (os.path.isfile(watermark) and os.path.getsize(watermark)):
            raise Error(create_invalid_value_message(watermark, "setMultipageWatermark", "image-to-pdf", 'The file must exist and not be empty.', "set_multipage_watermark"), 470);
        
        self.files['multipage_watermark'] = get_utf8_string(watermark)
        return self

    def setMultipageWatermarkUrl(self, url):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#set_multipage_watermark_url"""
        if not re.match(r'(?i)^https?://.*$', url):
            raise Error(create_invalid_value_message(url, "setMultipageWatermarkUrl", "image-to-pdf", 'Supported protocols are http:// and https://.', "set_multipage_watermark_url"), 470);
        
        self.fields['multipage_watermark_url'] = get_utf8_string(url)
        return self

    def setPageBackground(self, background):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#set_page_background"""
        if not (os.path.isfile(background) and os.path.getsize(background)):
            raise Error(create_invalid_value_message(background, "setPageBackground", "image-to-pdf", 'The file must exist and not be empty.', "set_page_background"), 470);
        
        self.files['page_background'] = get_utf8_string(background)
        return self

    def setPageBackgroundUrl(self, url):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#set_page_background_url"""
        if not re.match(r'(?i)^https?://.*$', url):
            raise Error(create_invalid_value_message(url, "setPageBackgroundUrl", "image-to-pdf", 'Supported protocols are http:// and https://.', "set_page_background_url"), 470);
        
        self.fields['page_background_url'] = get_utf8_string(url)
        return self

    def setMultipageBackground(self, background):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#set_multipage_background"""
        if not (os.path.isfile(background) and os.path.getsize(background)):
            raise Error(create_invalid_value_message(background, "setMultipageBackground", "image-to-pdf", 'The file must exist and not be empty.', "set_multipage_background"), 470);
        
        self.files['multipage_background'] = get_utf8_string(background)
        return self

    def setMultipageBackgroundUrl(self, url):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#set_multipage_background_url"""
        if not re.match(r'(?i)^https?://.*$', url):
            raise Error(create_invalid_value_message(url, "setMultipageBackgroundUrl", "image-to-pdf", 'Supported protocols are http:// and https://.', "set_multipage_background_url"), 470);
        
        self.fields['multipage_background_url'] = get_utf8_string(url)
        return self

    def setLinearize(self, value):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#set_linearize"""
        self.fields['linearize'] = value
        return self

    def setEncrypt(self, value):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#set_encrypt"""
        self.fields['encrypt'] = value
        return self

    def setUserPassword(self, password):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#set_user_password"""
        self.fields['user_password'] = get_utf8_string(password)
        return self

    def setOwnerPassword(self, password):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#set_owner_password"""
        self.fields['owner_password'] = get_utf8_string(password)
        return self

    def setNoPrint(self, value):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#set_no_print"""
        self.fields['no_print'] = value
        return self

    def setNoModify(self, value):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#set_no_modify"""
        self.fields['no_modify'] = value
        return self

    def setNoCopy(self, value):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#set_no_copy"""
        self.fields['no_copy'] = value
        return self

    def setTitle(self, title):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#set_title"""
        self.fields['title'] = get_utf8_string(title)
        return self

    def setSubject(self, subject):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#set_subject"""
        self.fields['subject'] = get_utf8_string(subject)
        return self

    def setAuthor(self, author):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#set_author"""
        self.fields['author'] = get_utf8_string(author)
        return self

    def setKeywords(self, keywords):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#set_keywords"""
        self.fields['keywords'] = get_utf8_string(keywords)
        return self

    def addAttachment(self, attachment):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#add_attachment"""
        if not (os.path.isfile(attachment) and os.path.getsize(attachment)):
            raise Error(create_invalid_value_message(attachment, "addAttachment", "image-to-pdf", 'The file must exist and not be empty.', "add_attachment"), 470);
        
        self.files['attachment_{0}'.format(self.file_id)] = attachment
        self.file_id += 1
        return self

    def setPageLayout(self, layout):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#set_page_layout"""
        if not re.match(r'(?i)^(single-page|one-column|two-column-left|two-column-right)$', layout):
            raise Error(create_invalid_value_message(layout, "setPageLayout", "image-to-pdf", 'Allowed values are single-page, one-column, two-column-left, two-column-right.', "set_page_layout"), 470);
        
        self.fields['page_layout'] = get_utf8_string(layout)
        return self

    def setPageMode(self, mode):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#set_page_mode"""
        if not re.match(r'(?i)^(full-screen|thumbnails|outlines)$', mode):
            raise Error(create_invalid_value_message(mode, "setPageMode", "image-to-pdf", 'Allowed values are full-screen, thumbnails, outlines.', "set_page_mode"), 470);
        
        self.fields['page_mode'] = get_utf8_string(mode)
        return self

    def setInitialZoomType(self, zoom_type):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#set_initial_zoom_type"""
        if not re.match(r'(?i)^(fit-width|fit-height|fit-page)$', zoom_type):
            raise Error(create_invalid_value_message(zoom_type, "setInitialZoomType", "image-to-pdf", 'Allowed values are fit-width, fit-height, fit-page.', "set_initial_zoom_type"), 470);
        
        self.fields['initial_zoom_type'] = get_utf8_string(zoom_type)
        return self

    def setInitialPage(self, page):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#set_initial_page"""
        if not (int(page) > 0):
            raise Error(create_invalid_value_message(page, "setInitialPage", "image-to-pdf", 'Must be a positive integer.', "set_initial_page"), 470);
        
        self.fields['initial_page'] = page
        return self

    def setInitialZoom(self, zoom):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#set_initial_zoom"""
        if not (int(zoom) > 0):
            raise Error(create_invalid_value_message(zoom, "setInitialZoom", "image-to-pdf", 'Must be a positive integer.', "set_initial_zoom"), 470);
        
        self.fields['initial_zoom'] = zoom
        return self

    def setHideToolbar(self, value):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#set_hide_toolbar"""
        self.fields['hide_toolbar'] = value
        return self

    def setHideMenubar(self, value):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#set_hide_menubar"""
        self.fields['hide_menubar'] = value
        return self

    def setHideWindowUi(self, value):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#set_hide_window_ui"""
        self.fields['hide_window_ui'] = value
        return self

    def setFitWindow(self, value):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#set_fit_window"""
        self.fields['fit_window'] = value
        return self

    def setCenterWindow(self, value):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#set_center_window"""
        self.fields['center_window'] = value
        return self

    def setDisplayTitle(self, value):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#set_display_title"""
        self.fields['display_title'] = value
        return self

    def setDebugLog(self, value):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#set_debug_log"""
        self.fields['debug_log'] = value
        return self

    def getDebugLogUrl(self):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#get_debug_log_url"""
        return self.helper.getDebugLogUrl()

    def getRemainingCreditCount(self):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#get_remaining_credit_count"""
        return self.helper.getRemainingCreditCount()

    def getConsumedCreditCount(self):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#get_consumed_credit_count"""
        return self.helper.getConsumedCreditCount()

    def getJobId(self):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#get_job_id"""
        return self.helper.getJobId()

    def getOutputSize(self):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#get_output_size"""
        return self.helper.getOutputSize()

    def getVersion(self):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#get_version"""
        return 'client {0}, API v2, converter {1}'.format(CLIENT_VERSION, self.helper.getConverterVersion())

    def setTag(self, tag):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#set_tag"""
        self.fields['tag'] = get_utf8_string(tag)
        return self

    def setHttpProxy(self, proxy):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#set_http_proxy"""
        if not re.match(r'(?i)^([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z0-9]{1,}:\d+$', proxy):
            raise Error(create_invalid_value_message(proxy, "setHttpProxy", "image-to-pdf", 'The value must have format DOMAIN_OR_IP_ADDRESS:PORT.', "set_http_proxy"), 470);
        
        self.fields['http_proxy'] = get_utf8_string(proxy)
        return self

    def setHttpsProxy(self, proxy):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#set_https_proxy"""
        if not re.match(r'(?i)^([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z0-9]{1,}:\d+$', proxy):
            raise Error(create_invalid_value_message(proxy, "setHttpsProxy", "image-to-pdf", 'The value must have format DOMAIN_OR_IP_ADDRESS:PORT.', "set_https_proxy"), 470);
        
        self.fields['https_proxy'] = get_utf8_string(proxy)
        return self

    def setConverterVersion(self, version):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#set_converter_version"""
        if not re.match(r'(?i)^(24.04|20.10|18.10|latest)$', version):
            raise Error(create_invalid_value_message(version, "setConverterVersion", "image-to-pdf", 'Allowed values are 24.04, 20.10, 18.10, latest.', "set_converter_version"), 470);
        
        self.helper.setConverterVersion(version)
        return self

    def setUseHttp(self, value):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#set_use_http"""
        self.helper.setUseHttp(value)
        return self

    def setClientUserAgent(self, agent):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#set_client_user_agent"""
        self.helper.setUserAgent(agent)
        return self

    def setUserAgent(self, agent):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#set_user_agent"""
        self.helper.setUserAgent(agent)
        return self

    def setProxy(self, host, port, user_name, password):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#set_proxy"""
        self.helper.setProxy(host, port, user_name, password)
        return self

    def setRetryCount(self, count):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#set_retry_count"""
        self.helper.setRetryCount(count)
        return self

class PdfToHtmlClient:
    """Conversion from PDF to HTML.

    https://pdfcrowd.com/api/pdf-to-html-python/"""

    def __init__(self, user_name, api_key):
        """https://pdfcrowd.com/api/pdf-to-html-python/ref/#__init__"""
        self.helper = ConnectionHelper(user_name, api_key)
        self.fields = {
            'input_format': 'pdf',
            'output_format': 'html'
        }
        self.file_id = 1
        self.files = {}
        self.raw_data = {}

    def convertUrl(self, url):
        """https://pdfcrowd.com/api/pdf-to-html-python/ref/#convert_url"""
        if not re.match(r'(?i)^https?://.*$', url):
            raise Error(create_invalid_value_message(url, "convertUrl", "pdf-to-html", 'Supported protocols are http:// and https://.', "convert_url"), 470);
        
        self.helper.reset_input(self.fields, self.files, self.raw_data)
        self.fields['url'] = get_utf8_string(url)
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertUrlToStream(self, url, out_stream):
        """https://pdfcrowd.com/api/pdf-to-html-python/ref/#convert_url_to_stream"""
        if not re.match(r'(?i)^https?://.*$', url):
            raise Error(create_invalid_value_message(url, "convertUrlToStream::url", "pdf-to-html", 'Supported protocols are http:// and https://.', "convert_url_to_stream"), 470);
        
        self.helper.reset_input(self.fields, self.files, self.raw_data)
        self.fields['url'] = get_utf8_string(url)
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertUrlToFile(self, url, file_path):
        """https://pdfcrowd.com/api/pdf-to-html-python/ref/#convert_url_to_file"""
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "convertUrlToFile::file_path", "pdf-to-html", 'The string must not be empty.', "convert_url_to_file"), 470);
        
        if not (self._isOutputTypeValid(file_path)):
            raise Error(create_invalid_value_message(file_path, "convertUrlToFile::file_path", "pdf-to-html", 'The converter generates an HTML or ZIP file. If ZIP file is generated, the file path must have a ZIP or zip extension.', "convert_url_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        succeeded = False
        try:
            self.convertUrlToStream(url,output_file)
            succeeded = True
        finally:
            if succeeded:
                output_file.close()
            else:
                try:
                    output_file.close()
                except BaseException:
                    pass
                try:
                    os.remove(file_path)
                except OSError:
                    pass

    def convertFile(self, file):
        """https://pdfcrowd.com/api/pdf-to-html-python/ref/#convert_file"""
        if not (os.path.isfile(file) and os.path.getsize(file)):
            raise Error(create_invalid_value_message(file, "convertFile", "pdf-to-html", 'The file must exist and not be empty.', "convert_file"), 470);
        
        self.helper.reset_input(self.fields, self.files, self.raw_data)
        self.files['file'] = get_utf8_string(file)
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertFileToStream(self, file, out_stream):
        """https://pdfcrowd.com/api/pdf-to-html-python/ref/#convert_file_to_stream"""
        if not (os.path.isfile(file) and os.path.getsize(file)):
            raise Error(create_invalid_value_message(file, "convertFileToStream::file", "pdf-to-html", 'The file must exist and not be empty.', "convert_file_to_stream"), 470);
        
        self.helper.reset_input(self.fields, self.files, self.raw_data)
        self.files['file'] = get_utf8_string(file)
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertFileToFile(self, file, file_path):
        """https://pdfcrowd.com/api/pdf-to-html-python/ref/#convert_file_to_file"""
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "convertFileToFile::file_path", "pdf-to-html", 'The string must not be empty.', "convert_file_to_file"), 470);
        
        if not (self._isOutputTypeValid(file_path)):
            raise Error(create_invalid_value_message(file_path, "convertFileToFile::file_path", "pdf-to-html", 'The converter generates an HTML or ZIP file. If ZIP file is generated, the file path must have a ZIP or zip extension.', "convert_file_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        succeeded = False
        try:
            self.convertFileToStream(file,output_file)
            succeeded = True
        finally:
            if succeeded:
                output_file.close()
            else:
                try:
                    output_file.close()
                except BaseException:
                    pass
                try:
                    os.remove(file_path)
                except OSError:
                    pass

    def convertRawData(self, data):
        """https://pdfcrowd.com/api/pdf-to-html-python/ref/#convert_raw_data"""
        self.helper.reset_input(self.fields, self.files, self.raw_data)
        self.raw_data['file'] = data
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertRawDataToStream(self, data, out_stream):
        """https://pdfcrowd.com/api/pdf-to-html-python/ref/#convert_raw_data_to_stream"""
        self.helper.reset_input(self.fields, self.files, self.raw_data)
        self.raw_data['file'] = data
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertRawDataToFile(self, data, file_path):
        """https://pdfcrowd.com/api/pdf-to-html-python/ref/#convert_raw_data_to_file"""
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "convertRawDataToFile::file_path", "pdf-to-html", 'The string must not be empty.', "convert_raw_data_to_file"), 470);
        
        if not (self._isOutputTypeValid(file_path)):
            raise Error(create_invalid_value_message(file_path, "convertRawDataToFile::file_path", "pdf-to-html", 'The converter generates an HTML or ZIP file. If ZIP file is generated, the file path must have a ZIP or zip extension.', "convert_raw_data_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        succeeded = False
        try:
            self.convertRawDataToStream(data,output_file)
            succeeded = True
        finally:
            if succeeded:
                output_file.close()
            else:
                try:
                    output_file.close()
                except BaseException:
                    pass
                try:
                    os.remove(file_path)
                except OSError:
                    pass

    def convertStream(self, in_stream):
        """https://pdfcrowd.com/api/pdf-to-html-python/ref/#convert_stream"""
        self.helper.reset_input(self.fields, self.files, self.raw_data)
        self.raw_data['stream'] = in_stream.read()
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertStreamToStream(self, in_stream, out_stream):
        """https://pdfcrowd.com/api/pdf-to-html-python/ref/#convert_stream_to_stream"""
        self.helper.reset_input(self.fields, self.files, self.raw_data)
        self.raw_data['stream'] = in_stream.read()
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertStreamToFile(self, in_stream, file_path):
        """https://pdfcrowd.com/api/pdf-to-html-python/ref/#convert_stream_to_file"""
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "convertStreamToFile::file_path", "pdf-to-html", 'The string must not be empty.', "convert_stream_to_file"), 470);
        
        if not (self._isOutputTypeValid(file_path)):
            raise Error(create_invalid_value_message(file_path, "convertStreamToFile::file_path", "pdf-to-html", 'The converter generates an HTML or ZIP file. If ZIP file is generated, the file path must have a ZIP or zip extension.', "convert_stream_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        succeeded = False
        try:
            self.convertStreamToStream(in_stream,output_file)
            succeeded = True
        finally:
            if succeeded:
                output_file.close()
            else:
                try:
                    output_file.close()
                except BaseException:
                    pass
                try:
                    os.remove(file_path)
                except OSError:
                    pass

    def setPdfPassword(self, password):
        """https://pdfcrowd.com/api/pdf-to-html-python/ref/#set_pdf_password"""
        self.fields['pdf_password'] = get_utf8_string(password)
        return self

    def setScaleFactor(self, factor):
        """https://pdfcrowd.com/api/pdf-to-html-python/ref/#set_scale_factor"""
        if not (int(factor) > 0):
            raise Error(create_invalid_value_message(factor, "setScaleFactor", "pdf-to-html", 'Must be a positive integer.', "set_scale_factor"), 470);
        
        self.fields['scale_factor'] = factor
        return self

    def setPrintPageRange(self, pages):
        """https://pdfcrowd.com/api/pdf-to-html-python/ref/#set_print_page_range"""
        if not re.match(r'^(?:\s*(?:\d+|(?:\d*\s*\-\s*\d+)|(?:\d+\s*\-\s*\d*))\s*,\s*)*\s*(?:\d+|(?:\d*\s*\-\s*\d+)|(?:\d+\s*\-\s*\d*))\s*$', pages):
            raise Error(create_invalid_value_message(pages, "setPrintPageRange", "pdf-to-html", 'A comma separated list of page numbers or ranges.', "set_print_page_range"), 470);
        
        self.fields['print_page_range'] = get_utf8_string(pages)
        return self

    def setDpi(self, dpi):
        """https://pdfcrowd.com/api/pdf-to-html-python/ref/#set_dpi"""
        self.fields['dpi'] = dpi
        return self

    def setImageMode(self, mode):
        """https://pdfcrowd.com/api/pdf-to-html-python/ref/#set_image_mode"""
        if not re.match(r'(?i)^(embed|separate|none)$', mode):
            raise Error(create_invalid_value_message(mode, "setImageMode", "pdf-to-html", 'Allowed values are embed, separate, none.', "set_image_mode"), 470);
        
        self.fields['image_mode'] = get_utf8_string(mode)
        return self

    def setImageFormat(self, image_format):
        """https://pdfcrowd.com/api/pdf-to-html-python/ref/#set_image_format"""
        if not re.match(r'(?i)^(png|jpg|svg)$', image_format):
            raise Error(create_invalid_value_message(image_format, "setImageFormat", "pdf-to-html", 'Allowed values are png, jpg, svg.', "set_image_format"), 470);
        
        self.fields['image_format'] = get_utf8_string(image_format)
        return self

    def setCssMode(self, mode):
        """https://pdfcrowd.com/api/pdf-to-html-python/ref/#set_css_mode"""
        if not re.match(r'(?i)^(embed|separate)$', mode):
            raise Error(create_invalid_value_message(mode, "setCssMode", "pdf-to-html", 'Allowed values are embed, separate.', "set_css_mode"), 470);
        
        self.fields['css_mode'] = get_utf8_string(mode)
        return self

    def setFontMode(self, mode):
        """https://pdfcrowd.com/api/pdf-to-html-python/ref/#set_font_mode"""
        if not re.match(r'(?i)^(embed|separate)$', mode):
            raise Error(create_invalid_value_message(mode, "setFontMode", "pdf-to-html", 'Allowed values are embed, separate.', "set_font_mode"), 470);
        
        self.fields['font_mode'] = get_utf8_string(mode)
        return self

    def setType3Mode(self, mode):
        """https://pdfcrowd.com/api/pdf-to-html-python/ref/#set_type3_mode"""
        if not re.match(r'(?i)^(raster|convert)$', mode):
            raise Error(create_invalid_value_message(mode, "setType3Mode", "pdf-to-html", 'Allowed values are raster, convert.', "set_type3_mode"), 470);
        
        self.fields['type3_mode'] = get_utf8_string(mode)
        return self

    def setSplitLigatures(self, value):
        """https://pdfcrowd.com/api/pdf-to-html-python/ref/#set_split_ligatures"""
        self.fields['split_ligatures'] = value
        return self

    def setCustomCss(self, css):
        """https://pdfcrowd.com/api/pdf-to-html-python/ref/#set_custom_css"""
        if not (css):
            raise Error(create_invalid_value_message(css, "setCustomCss", "pdf-to-html", 'The string must not be empty.', "set_custom_css"), 470);
        
        self.fields['custom_css'] = get_utf8_string(css)
        return self

    def setHtmlNamespace(self, prefix):
        """https://pdfcrowd.com/api/pdf-to-html-python/ref/#set_html_namespace"""
        if not re.match(r'(?i)^[a-z_][a-z0-9_:-]*$', prefix):
            raise Error(create_invalid_value_message(prefix, "setHtmlNamespace", "pdf-to-html", 'Start with a letter or underscore, and use only letters, numbers, hyphens, underscores, or colons.', "set_html_namespace"), 470);
        
        self.fields['html_namespace'] = get_utf8_string(prefix)
        return self

    def isZippedOutput(self):
        """https://pdfcrowd.com/api/pdf-to-html-python/ref/#is_zipped_output"""
        return self.fields.get('image_mode') == 'separate' or self.fields.get('css_mode') == 'separate' or self.fields.get('font_mode') == 'separate' or self.fields.get('force_zip') == True

    def setForceZip(self, value):
        """https://pdfcrowd.com/api/pdf-to-html-python/ref/#set_force_zip"""
        self.fields['force_zip'] = value
        return self

    def setTitle(self, title):
        """https://pdfcrowd.com/api/pdf-to-html-python/ref/#set_title"""
        self.fields['title'] = get_utf8_string(title)
        return self

    def setSubject(self, subject):
        """https://pdfcrowd.com/api/pdf-to-html-python/ref/#set_subject"""
        self.fields['subject'] = get_utf8_string(subject)
        return self

    def setAuthor(self, author):
        """https://pdfcrowd.com/api/pdf-to-html-python/ref/#set_author"""
        self.fields['author'] = get_utf8_string(author)
        return self

    def setKeywords(self, keywords):
        """https://pdfcrowd.com/api/pdf-to-html-python/ref/#set_keywords"""
        self.fields['keywords'] = get_utf8_string(keywords)
        return self

    def setDebugLog(self, value):
        """https://pdfcrowd.com/api/pdf-to-html-python/ref/#set_debug_log"""
        self.fields['debug_log'] = value
        return self

    def getDebugLogUrl(self):
        """https://pdfcrowd.com/api/pdf-to-html-python/ref/#get_debug_log_url"""
        return self.helper.getDebugLogUrl()

    def getRemainingCreditCount(self):
        """https://pdfcrowd.com/api/pdf-to-html-python/ref/#get_remaining_credit_count"""
        return self.helper.getRemainingCreditCount()

    def getConsumedCreditCount(self):
        """https://pdfcrowd.com/api/pdf-to-html-python/ref/#get_consumed_credit_count"""
        return self.helper.getConsumedCreditCount()

    def getJobId(self):
        """https://pdfcrowd.com/api/pdf-to-html-python/ref/#get_job_id"""
        return self.helper.getJobId()

    def getPageCount(self):
        """https://pdfcrowd.com/api/pdf-to-html-python/ref/#get_page_count"""
        return self.helper.getPageCount()

    def getOutputSize(self):
        """https://pdfcrowd.com/api/pdf-to-html-python/ref/#get_output_size"""
        return self.helper.getOutputSize()

    def getVersion(self):
        """https://pdfcrowd.com/api/pdf-to-html-python/ref/#get_version"""
        return 'client {0}, API v2, converter {1}'.format(CLIENT_VERSION, self.helper.getConverterVersion())

    def setTag(self, tag):
        """https://pdfcrowd.com/api/pdf-to-html-python/ref/#set_tag"""
        self.fields['tag'] = get_utf8_string(tag)
        return self

    def setHttpProxy(self, proxy):
        """https://pdfcrowd.com/api/pdf-to-html-python/ref/#set_http_proxy"""
        if not re.match(r'(?i)^([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z0-9]{1,}:\d+$', proxy):
            raise Error(create_invalid_value_message(proxy, "setHttpProxy", "pdf-to-html", 'The value must have format DOMAIN_OR_IP_ADDRESS:PORT.', "set_http_proxy"), 470);
        
        self.fields['http_proxy'] = get_utf8_string(proxy)
        return self

    def setHttpsProxy(self, proxy):
        """https://pdfcrowd.com/api/pdf-to-html-python/ref/#set_https_proxy"""
        if not re.match(r'(?i)^([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z0-9]{1,}:\d+$', proxy):
            raise Error(create_invalid_value_message(proxy, "setHttpsProxy", "pdf-to-html", 'The value must have format DOMAIN_OR_IP_ADDRESS:PORT.', "set_https_proxy"), 470);
        
        self.fields['https_proxy'] = get_utf8_string(proxy)
        return self

    def setConverterVersion(self, version):
        """https://pdfcrowd.com/api/pdf-to-html-python/ref/#set_converter_version"""
        if not re.match(r'(?i)^(24.04|20.10|18.10|latest)$', version):
            raise Error(create_invalid_value_message(version, "setConverterVersion", "pdf-to-html", 'Allowed values are 24.04, 20.10, 18.10, latest.', "set_converter_version"), 470);
        
        self.helper.setConverterVersion(version)
        return self

    def setUseHttp(self, value):
        """https://pdfcrowd.com/api/pdf-to-html-python/ref/#set_use_http"""
        self.helper.setUseHttp(value)
        return self

    def setClientUserAgent(self, agent):
        """https://pdfcrowd.com/api/pdf-to-html-python/ref/#set_client_user_agent"""
        self.helper.setUserAgent(agent)
        return self

    def setUserAgent(self, agent):
        """https://pdfcrowd.com/api/pdf-to-html-python/ref/#set_user_agent"""
        self.helper.setUserAgent(agent)
        return self

    def setProxy(self, host, port, user_name, password):
        """https://pdfcrowd.com/api/pdf-to-html-python/ref/#set_proxy"""
        self.helper.setProxy(host, port, user_name, password)
        return self

    def setRetryCount(self, count):
        """https://pdfcrowd.com/api/pdf-to-html-python/ref/#set_retry_count"""
        self.helper.setRetryCount(count)
        return self

    def _isOutputTypeValid(self, file_path):
        extension = os.path.splitext(file_path)[1].lower()
        return (extension == '.zip') == self.isZippedOutput()
class PdfToTextClient:
    """Conversion from PDF to text.

    https://pdfcrowd.com/api/pdf-to-text-python/"""

    def __init__(self, user_name, api_key):
        """https://pdfcrowd.com/api/pdf-to-text-python/ref/#__init__"""
        self.helper = ConnectionHelper(user_name, api_key)
        self.fields = {
            'input_format': 'pdf',
            'output_format': 'txt'
        }
        self.file_id = 1
        self.files = {}
        self.raw_data = {}

    def convertUrl(self, url):
        """https://pdfcrowd.com/api/pdf-to-text-python/ref/#convert_url"""
        if not re.match(r'(?i)^https?://.*$', url):
            raise Error(create_invalid_value_message(url, "convertUrl", "pdf-to-text", 'Supported protocols are http:// and https://.', "convert_url"), 470);
        
        self.helper.reset_input(self.fields, self.files, self.raw_data)
        self.fields['url'] = get_utf8_string(url)
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertUrlToStream(self, url, out_stream):
        """https://pdfcrowd.com/api/pdf-to-text-python/ref/#convert_url_to_stream"""
        if not re.match(r'(?i)^https?://.*$', url):
            raise Error(create_invalid_value_message(url, "convertUrlToStream::url", "pdf-to-text", 'Supported protocols are http:// and https://.', "convert_url_to_stream"), 470);
        
        self.helper.reset_input(self.fields, self.files, self.raw_data)
        self.fields['url'] = get_utf8_string(url)
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertUrlToFile(self, url, file_path):
        """https://pdfcrowd.com/api/pdf-to-text-python/ref/#convert_url_to_file"""
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "convertUrlToFile::file_path", "pdf-to-text", 'The string must not be empty.', "convert_url_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        succeeded = False
        try:
            self.convertUrlToStream(url,output_file)
            succeeded = True
        finally:
            if succeeded:
                output_file.close()
            else:
                try:
                    output_file.close()
                except BaseException:
                    pass
                try:
                    os.remove(file_path)
                except OSError:
                    pass

    def convertFile(self, file):
        """https://pdfcrowd.com/api/pdf-to-text-python/ref/#convert_file"""
        if not (os.path.isfile(file) and os.path.getsize(file)):
            raise Error(create_invalid_value_message(file, "convertFile", "pdf-to-text", 'The file must exist and not be empty.', "convert_file"), 470);
        
        self.helper.reset_input(self.fields, self.files, self.raw_data)
        self.files['file'] = get_utf8_string(file)
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertFileToStream(self, file, out_stream):
        """https://pdfcrowd.com/api/pdf-to-text-python/ref/#convert_file_to_stream"""
        if not (os.path.isfile(file) and os.path.getsize(file)):
            raise Error(create_invalid_value_message(file, "convertFileToStream::file", "pdf-to-text", 'The file must exist and not be empty.', "convert_file_to_stream"), 470);
        
        self.helper.reset_input(self.fields, self.files, self.raw_data)
        self.files['file'] = get_utf8_string(file)
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertFileToFile(self, file, file_path):
        """https://pdfcrowd.com/api/pdf-to-text-python/ref/#convert_file_to_file"""
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "convertFileToFile::file_path", "pdf-to-text", 'The string must not be empty.', "convert_file_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        succeeded = False
        try:
            self.convertFileToStream(file,output_file)
            succeeded = True
        finally:
            if succeeded:
                output_file.close()
            else:
                try:
                    output_file.close()
                except BaseException:
                    pass
                try:
                    os.remove(file_path)
                except OSError:
                    pass

    def convertRawData(self, data):
        """https://pdfcrowd.com/api/pdf-to-text-python/ref/#convert_raw_data"""
        self.helper.reset_input(self.fields, self.files, self.raw_data)
        self.raw_data['file'] = data
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertRawDataToStream(self, data, out_stream):
        """https://pdfcrowd.com/api/pdf-to-text-python/ref/#convert_raw_data_to_stream"""
        self.helper.reset_input(self.fields, self.files, self.raw_data)
        self.raw_data['file'] = data
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertRawDataToFile(self, data, file_path):
        """https://pdfcrowd.com/api/pdf-to-text-python/ref/#convert_raw_data_to_file"""
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "convertRawDataToFile::file_path", "pdf-to-text", 'The string must not be empty.', "convert_raw_data_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        succeeded = False
        try:
            self.convertRawDataToStream(data,output_file)
            succeeded = True
        finally:
            if succeeded:
                output_file.close()
            else:
                try:
                    output_file.close()
                except BaseException:
                    pass
                try:
                    os.remove(file_path)
                except OSError:
                    pass

    def convertStream(self, in_stream):
        """https://pdfcrowd.com/api/pdf-to-text-python/ref/#convert_stream"""
        self.helper.reset_input(self.fields, self.files, self.raw_data)
        self.raw_data['stream'] = in_stream.read()
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertStreamToStream(self, in_stream, out_stream):
        """https://pdfcrowd.com/api/pdf-to-text-python/ref/#convert_stream_to_stream"""
        self.helper.reset_input(self.fields, self.files, self.raw_data)
        self.raw_data['stream'] = in_stream.read()
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertStreamToFile(self, in_stream, file_path):
        """https://pdfcrowd.com/api/pdf-to-text-python/ref/#convert_stream_to_file"""
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "convertStreamToFile::file_path", "pdf-to-text", 'The string must not be empty.', "convert_stream_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        succeeded = False
        try:
            self.convertStreamToStream(in_stream,output_file)
            succeeded = True
        finally:
            if succeeded:
                output_file.close()
            else:
                try:
                    output_file.close()
                except BaseException:
                    pass
                try:
                    os.remove(file_path)
                except OSError:
                    pass

    def setPdfPassword(self, password):
        """https://pdfcrowd.com/api/pdf-to-text-python/ref/#set_pdf_password"""
        self.fields['pdf_password'] = get_utf8_string(password)
        return self

    def setPrintPageRange(self, pages):
        """https://pdfcrowd.com/api/pdf-to-text-python/ref/#set_print_page_range"""
        if not re.match(r'^(?:\s*(?:\d+|(?:\d*\s*\-\s*\d+)|(?:\d+\s*\-\s*\d*))\s*,\s*)*\s*(?:\d+|(?:\d*\s*\-\s*\d+)|(?:\d+\s*\-\s*\d*))\s*$', pages):
            raise Error(create_invalid_value_message(pages, "setPrintPageRange", "pdf-to-text", 'A comma separated list of page numbers or ranges.', "set_print_page_range"), 470);
        
        self.fields['print_page_range'] = get_utf8_string(pages)
        return self

    def setNoLayout(self, value):
        """https://pdfcrowd.com/api/pdf-to-text-python/ref/#set_no_layout"""
        self.fields['no_layout'] = value
        return self

    def setEol(self, eol):
        """https://pdfcrowd.com/api/pdf-to-text-python/ref/#set_eol"""
        if not re.match(r'(?i)^(unix|dos|mac)$', eol):
            raise Error(create_invalid_value_message(eol, "setEol", "pdf-to-text", 'Allowed values are unix, dos, mac.', "set_eol"), 470);
        
        self.fields['eol'] = get_utf8_string(eol)
        return self

    def setPageBreakMode(self, mode):
        """https://pdfcrowd.com/api/pdf-to-text-python/ref/#set_page_break_mode"""
        if not re.match(r'(?i)^(none|default|custom)$', mode):
            raise Error(create_invalid_value_message(mode, "setPageBreakMode", "pdf-to-text", 'Allowed values are none, default, custom.', "set_page_break_mode"), 470);
        
        self.fields['page_break_mode'] = get_utf8_string(mode)
        return self

    def setCustomPageBreak(self, page_break):
        """https://pdfcrowd.com/api/pdf-to-text-python/ref/#set_custom_page_break"""
        self.fields['custom_page_break'] = get_utf8_string(page_break)
        return self

    def setParagraphMode(self, mode):
        """https://pdfcrowd.com/api/pdf-to-text-python/ref/#set_paragraph_mode"""
        if not re.match(r'(?i)^(none|bounding-box|characters)$', mode):
            raise Error(create_invalid_value_message(mode, "setParagraphMode", "pdf-to-text", 'Allowed values are none, bounding-box, characters.', "set_paragraph_mode"), 470);
        
        self.fields['paragraph_mode'] = get_utf8_string(mode)
        return self

    def setLineSpacingThreshold(self, threshold):
        """https://pdfcrowd.com/api/pdf-to-text-python/ref/#set_line_spacing_threshold"""
        if not re.match(r'(?i)^0$|^[0-9]+%$', threshold):
            raise Error(create_invalid_value_message(threshold, "setLineSpacingThreshold", "pdf-to-text", 'The value must be a positive integer percentage.', "set_line_spacing_threshold"), 470);
        
        self.fields['line_spacing_threshold'] = get_utf8_string(threshold)
        return self

    def setRemoveHyphenation(self, value):
        """https://pdfcrowd.com/api/pdf-to-text-python/ref/#set_remove_hyphenation"""
        self.fields['remove_hyphenation'] = value
        return self

    def setRemoveEmptyLines(self, value):
        """https://pdfcrowd.com/api/pdf-to-text-python/ref/#set_remove_empty_lines"""
        self.fields['remove_empty_lines'] = value
        return self

    def setCropAreaX(self, x):
        """https://pdfcrowd.com/api/pdf-to-text-python/ref/#set_crop_area_x"""
        if not (int(x) >= 0):
            raise Error(create_invalid_value_message(x, "setCropAreaX", "pdf-to-text", 'Must be a positive integer or 0.', "set_crop_area_x"), 470);
        
        self.fields['crop_area_x'] = x
        return self

    def setCropAreaY(self, y):
        """https://pdfcrowd.com/api/pdf-to-text-python/ref/#set_crop_area_y"""
        if not (int(y) >= 0):
            raise Error(create_invalid_value_message(y, "setCropAreaY", "pdf-to-text", 'Must be a positive integer or 0.', "set_crop_area_y"), 470);
        
        self.fields['crop_area_y'] = y
        return self

    def setCropAreaWidth(self, width):
        """https://pdfcrowd.com/api/pdf-to-text-python/ref/#set_crop_area_width"""
        if not (int(width) >= 0):
            raise Error(create_invalid_value_message(width, "setCropAreaWidth", "pdf-to-text", 'Must be a positive integer or 0.', "set_crop_area_width"), 470);
        
        self.fields['crop_area_width'] = width
        return self

    def setCropAreaHeight(self, height):
        """https://pdfcrowd.com/api/pdf-to-text-python/ref/#set_crop_area_height"""
        if not (int(height) >= 0):
            raise Error(create_invalid_value_message(height, "setCropAreaHeight", "pdf-to-text", 'Must be a positive integer or 0.', "set_crop_area_height"), 470);
        
        self.fields['crop_area_height'] = height
        return self

    def setCropArea(self, x, y, width, height):
        """https://pdfcrowd.com/api/pdf-to-text-python/ref/#set_crop_area"""
        self.setCropAreaX(x)
        self.setCropAreaY(y)
        self.setCropAreaWidth(width)
        self.setCropAreaHeight(height)
        return self

    def setDebugLog(self, value):
        """https://pdfcrowd.com/api/pdf-to-text-python/ref/#set_debug_log"""
        self.fields['debug_log'] = value
        return self

    def getDebugLogUrl(self):
        """https://pdfcrowd.com/api/pdf-to-text-python/ref/#get_debug_log_url"""
        return self.helper.getDebugLogUrl()

    def getRemainingCreditCount(self):
        """https://pdfcrowd.com/api/pdf-to-text-python/ref/#get_remaining_credit_count"""
        return self.helper.getRemainingCreditCount()

    def getConsumedCreditCount(self):
        """https://pdfcrowd.com/api/pdf-to-text-python/ref/#get_consumed_credit_count"""
        return self.helper.getConsumedCreditCount()

    def getJobId(self):
        """https://pdfcrowd.com/api/pdf-to-text-python/ref/#get_job_id"""
        return self.helper.getJobId()

    def getPageCount(self):
        """https://pdfcrowd.com/api/pdf-to-text-python/ref/#get_page_count"""
        return self.helper.getPageCount()

    def getOutputSize(self):
        """https://pdfcrowd.com/api/pdf-to-text-python/ref/#get_output_size"""
        return self.helper.getOutputSize()

    def getVersion(self):
        """https://pdfcrowd.com/api/pdf-to-text-python/ref/#get_version"""
        return 'client {0}, API v2, converter {1}'.format(CLIENT_VERSION, self.helper.getConverterVersion())

    def setTag(self, tag):
        """https://pdfcrowd.com/api/pdf-to-text-python/ref/#set_tag"""
        self.fields['tag'] = get_utf8_string(tag)
        return self

    def setHttpProxy(self, proxy):
        """https://pdfcrowd.com/api/pdf-to-text-python/ref/#set_http_proxy"""
        if not re.match(r'(?i)^([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z0-9]{1,}:\d+$', proxy):
            raise Error(create_invalid_value_message(proxy, "setHttpProxy", "pdf-to-text", 'The value must have format DOMAIN_OR_IP_ADDRESS:PORT.', "set_http_proxy"), 470);
        
        self.fields['http_proxy'] = get_utf8_string(proxy)
        return self

    def setHttpsProxy(self, proxy):
        """https://pdfcrowd.com/api/pdf-to-text-python/ref/#set_https_proxy"""
        if not re.match(r'(?i)^([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z0-9]{1,}:\d+$', proxy):
            raise Error(create_invalid_value_message(proxy, "setHttpsProxy", "pdf-to-text", 'The value must have format DOMAIN_OR_IP_ADDRESS:PORT.', "set_https_proxy"), 470);
        
        self.fields['https_proxy'] = get_utf8_string(proxy)
        return self

    def setUseHttp(self, value):
        """https://pdfcrowd.com/api/pdf-to-text-python/ref/#set_use_http"""
        self.helper.setUseHttp(value)
        return self

    def setClientUserAgent(self, agent):
        """https://pdfcrowd.com/api/pdf-to-text-python/ref/#set_client_user_agent"""
        self.helper.setUserAgent(agent)
        return self

    def setUserAgent(self, agent):
        """https://pdfcrowd.com/api/pdf-to-text-python/ref/#set_user_agent"""
        self.helper.setUserAgent(agent)
        return self

    def setProxy(self, host, port, user_name, password):
        """https://pdfcrowd.com/api/pdf-to-text-python/ref/#set_proxy"""
        self.helper.setProxy(host, port, user_name, password)
        return self

    def setRetryCount(self, count):
        """https://pdfcrowd.com/api/pdf-to-text-python/ref/#set_retry_count"""
        self.helper.setRetryCount(count)
        return self

class PdfToImageClient:
    """Conversion from PDF to image.

    https://pdfcrowd.com/api/pdf-to-image-python/"""

    def __init__(self, user_name, api_key):
        """https://pdfcrowd.com/api/pdf-to-image-python/ref/#__init__"""
        self.helper = ConnectionHelper(user_name, api_key)
        self.fields = {
            'input_format': 'pdf',
            'output_format': 'png'
        }
        self.file_id = 1
        self.files = {}
        self.raw_data = {}

    def convertUrl(self, url):
        """https://pdfcrowd.com/api/pdf-to-image-python/ref/#convert_url"""
        if not re.match(r'(?i)^https?://.*$', url):
            raise Error(create_invalid_value_message(url, "convertUrl", "pdf-to-image", 'Supported protocols are http:// and https://.', "convert_url"), 470);
        
        self.helper.reset_input(self.fields, self.files, self.raw_data)
        self.fields['url'] = get_utf8_string(url)
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertUrlToStream(self, url, out_stream):
        """https://pdfcrowd.com/api/pdf-to-image-python/ref/#convert_url_to_stream"""
        if not re.match(r'(?i)^https?://.*$', url):
            raise Error(create_invalid_value_message(url, "convertUrlToStream::url", "pdf-to-image", 'Supported protocols are http:// and https://.', "convert_url_to_stream"), 470);
        
        self.helper.reset_input(self.fields, self.files, self.raw_data)
        self.fields['url'] = get_utf8_string(url)
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertUrlToFile(self, url, file_path):
        """https://pdfcrowd.com/api/pdf-to-image-python/ref/#convert_url_to_file"""
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "convertUrlToFile::file_path", "pdf-to-image", 'The string must not be empty.', "convert_url_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        succeeded = False
        try:
            self.convertUrlToStream(url,output_file)
            succeeded = True
        finally:
            if succeeded:
                output_file.close()
            else:
                try:
                    output_file.close()
                except BaseException:
                    pass
                try:
                    os.remove(file_path)
                except OSError:
                    pass

    def convertFile(self, file):
        """https://pdfcrowd.com/api/pdf-to-image-python/ref/#convert_file"""
        if not (os.path.isfile(file) and os.path.getsize(file)):
            raise Error(create_invalid_value_message(file, "convertFile", "pdf-to-image", 'The file must exist and not be empty.', "convert_file"), 470);
        
        self.helper.reset_input(self.fields, self.files, self.raw_data)
        self.files['file'] = get_utf8_string(file)
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertFileToStream(self, file, out_stream):
        """https://pdfcrowd.com/api/pdf-to-image-python/ref/#convert_file_to_stream"""
        if not (os.path.isfile(file) and os.path.getsize(file)):
            raise Error(create_invalid_value_message(file, "convertFileToStream::file", "pdf-to-image", 'The file must exist and not be empty.', "convert_file_to_stream"), 470);
        
        self.helper.reset_input(self.fields, self.files, self.raw_data)
        self.files['file'] = get_utf8_string(file)
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertFileToFile(self, file, file_path):
        """https://pdfcrowd.com/api/pdf-to-image-python/ref/#convert_file_to_file"""
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "convertFileToFile::file_path", "pdf-to-image", 'The string must not be empty.', "convert_file_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        succeeded = False
        try:
            self.convertFileToStream(file,output_file)
            succeeded = True
        finally:
            if succeeded:
                output_file.close()
            else:
                try:
                    output_file.close()
                except BaseException:
                    pass
                try:
                    os.remove(file_path)
                except OSError:
                    pass

    def convertRawData(self, data):
        """https://pdfcrowd.com/api/pdf-to-image-python/ref/#convert_raw_data"""
        self.helper.reset_input(self.fields, self.files, self.raw_data)
        self.raw_data['file'] = data
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertRawDataToStream(self, data, out_stream):
        """https://pdfcrowd.com/api/pdf-to-image-python/ref/#convert_raw_data_to_stream"""
        self.helper.reset_input(self.fields, self.files, self.raw_data)
        self.raw_data['file'] = data
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertRawDataToFile(self, data, file_path):
        """https://pdfcrowd.com/api/pdf-to-image-python/ref/#convert_raw_data_to_file"""
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "convertRawDataToFile::file_path", "pdf-to-image", 'The string must not be empty.', "convert_raw_data_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        succeeded = False
        try:
            self.convertRawDataToStream(data,output_file)
            succeeded = True
        finally:
            if succeeded:
                output_file.close()
            else:
                try:
                    output_file.close()
                except BaseException:
                    pass
                try:
                    os.remove(file_path)
                except OSError:
                    pass

    def convertStream(self, in_stream):
        """https://pdfcrowd.com/api/pdf-to-image-python/ref/#convert_stream"""
        self.helper.reset_input(self.fields, self.files, self.raw_data)
        self.raw_data['stream'] = in_stream.read()
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertStreamToStream(self, in_stream, out_stream):
        """https://pdfcrowd.com/api/pdf-to-image-python/ref/#convert_stream_to_stream"""
        self.helper.reset_input(self.fields, self.files, self.raw_data)
        self.raw_data['stream'] = in_stream.read()
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertStreamToFile(self, in_stream, file_path):
        """https://pdfcrowd.com/api/pdf-to-image-python/ref/#convert_stream_to_file"""
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "convertStreamToFile::file_path", "pdf-to-image", 'The string must not be empty.', "convert_stream_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        succeeded = False
        try:
            self.convertStreamToStream(in_stream,output_file)
            succeeded = True
        finally:
            if succeeded:
                output_file.close()
            else:
                try:
                    output_file.close()
                except BaseException:
                    pass
                try:
                    os.remove(file_path)
                except OSError:
                    pass

    def setOutputFormat(self, output_format):
        """https://pdfcrowd.com/api/pdf-to-image-python/ref/#set_output_format"""
        if not re.match(r'(?i)^(png|jpg|gif|tiff|bmp|ico|ppm|pgm|pbm|pnm|psb|pct|ras|tga|sgi|sun|webp)$', output_format):
            raise Error(create_invalid_value_message(output_format, "setOutputFormat", "pdf-to-image", 'Allowed values are png, jpg, gif, tiff, bmp, ico, ppm, pgm, pbm, pnm, psb, pct, ras, tga, sgi, sun, webp.', "set_output_format"), 470);
        
        self.fields['output_format'] = get_utf8_string(output_format)
        return self

    def setPdfPassword(self, password):
        """https://pdfcrowd.com/api/pdf-to-image-python/ref/#set_pdf_password"""
        self.fields['pdf_password'] = get_utf8_string(password)
        return self

    def setPrintPageRange(self, pages):
        """https://pdfcrowd.com/api/pdf-to-image-python/ref/#set_print_page_range"""
        if not re.match(r'^(?:\s*(?:\d+|(?:\d*\s*\-\s*\d+)|(?:\d+\s*\-\s*\d*))\s*,\s*)*\s*(?:\d+|(?:\d*\s*\-\s*\d+)|(?:\d+\s*\-\s*\d*))\s*$', pages):
            raise Error(create_invalid_value_message(pages, "setPrintPageRange", "pdf-to-image", 'A comma separated list of page numbers or ranges.', "set_print_page_range"), 470);
        
        self.fields['print_page_range'] = get_utf8_string(pages)
        return self

    def setDpi(self, dpi):
        """https://pdfcrowd.com/api/pdf-to-image-python/ref/#set_dpi"""
        self.fields['dpi'] = dpi
        return self

    def isZippedOutput(self):
        """https://pdfcrowd.com/api/pdf-to-image-python/ref/#is_zipped_output"""
        return self.fields.get('force_zip') == True or self.getPageCount() > 1

    def setForceZip(self, value):
        """https://pdfcrowd.com/api/pdf-to-image-python/ref/#set_force_zip"""
        self.fields['force_zip'] = value
        return self

    def setUseCropbox(self, value):
        """https://pdfcrowd.com/api/pdf-to-image-python/ref/#set_use_cropbox"""
        self.fields['use_cropbox'] = value
        return self

    def setCropAreaX(self, x):
        """https://pdfcrowd.com/api/pdf-to-image-python/ref/#set_crop_area_x"""
        if not (int(x) >= 0):
            raise Error(create_invalid_value_message(x, "setCropAreaX", "pdf-to-image", 'Must be a positive integer or 0.', "set_crop_area_x"), 470);
        
        self.fields['crop_area_x'] = x
        return self

    def setCropAreaY(self, y):
        """https://pdfcrowd.com/api/pdf-to-image-python/ref/#set_crop_area_y"""
        if not (int(y) >= 0):
            raise Error(create_invalid_value_message(y, "setCropAreaY", "pdf-to-image", 'Must be a positive integer or 0.', "set_crop_area_y"), 470);
        
        self.fields['crop_area_y'] = y
        return self

    def setCropAreaWidth(self, width):
        """https://pdfcrowd.com/api/pdf-to-image-python/ref/#set_crop_area_width"""
        if not (int(width) >= 0):
            raise Error(create_invalid_value_message(width, "setCropAreaWidth", "pdf-to-image", 'Must be a positive integer or 0.', "set_crop_area_width"), 470);
        
        self.fields['crop_area_width'] = width
        return self

    def setCropAreaHeight(self, height):
        """https://pdfcrowd.com/api/pdf-to-image-python/ref/#set_crop_area_height"""
        if not (int(height) >= 0):
            raise Error(create_invalid_value_message(height, "setCropAreaHeight", "pdf-to-image", 'Must be a positive integer or 0.', "set_crop_area_height"), 470);
        
        self.fields['crop_area_height'] = height
        return self

    def setCropArea(self, x, y, width, height):
        """https://pdfcrowd.com/api/pdf-to-image-python/ref/#set_crop_area"""
        self.setCropAreaX(x)
        self.setCropAreaY(y)
        self.setCropAreaWidth(width)
        self.setCropAreaHeight(height)
        return self

    def setUseGrayscale(self, value):
        """https://pdfcrowd.com/api/pdf-to-image-python/ref/#set_use_grayscale"""
        self.fields['use_grayscale'] = value
        return self

    def setDebugLog(self, value):
        """https://pdfcrowd.com/api/pdf-to-image-python/ref/#set_debug_log"""
        self.fields['debug_log'] = value
        return self

    def getDebugLogUrl(self):
        """https://pdfcrowd.com/api/pdf-to-image-python/ref/#get_debug_log_url"""
        return self.helper.getDebugLogUrl()

    def getRemainingCreditCount(self):
        """https://pdfcrowd.com/api/pdf-to-image-python/ref/#get_remaining_credit_count"""
        return self.helper.getRemainingCreditCount()

    def getConsumedCreditCount(self):
        """https://pdfcrowd.com/api/pdf-to-image-python/ref/#get_consumed_credit_count"""
        return self.helper.getConsumedCreditCount()

    def getJobId(self):
        """https://pdfcrowd.com/api/pdf-to-image-python/ref/#get_job_id"""
        return self.helper.getJobId()

    def getPageCount(self):
        """https://pdfcrowd.com/api/pdf-to-image-python/ref/#get_page_count"""
        return self.helper.getPageCount()

    def getOutputSize(self):
        """https://pdfcrowd.com/api/pdf-to-image-python/ref/#get_output_size"""
        return self.helper.getOutputSize()

    def getVersion(self):
        """https://pdfcrowd.com/api/pdf-to-image-python/ref/#get_version"""
        return 'client {0}, API v2, converter {1}'.format(CLIENT_VERSION, self.helper.getConverterVersion())

    def setTag(self, tag):
        """https://pdfcrowd.com/api/pdf-to-image-python/ref/#set_tag"""
        self.fields['tag'] = get_utf8_string(tag)
        return self

    def setHttpProxy(self, proxy):
        """https://pdfcrowd.com/api/pdf-to-image-python/ref/#set_http_proxy"""
        if not re.match(r'(?i)^([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z0-9]{1,}:\d+$', proxy):
            raise Error(create_invalid_value_message(proxy, "setHttpProxy", "pdf-to-image", 'The value must have format DOMAIN_OR_IP_ADDRESS:PORT.', "set_http_proxy"), 470);
        
        self.fields['http_proxy'] = get_utf8_string(proxy)
        return self

    def setHttpsProxy(self, proxy):
        """https://pdfcrowd.com/api/pdf-to-image-python/ref/#set_https_proxy"""
        if not re.match(r'(?i)^([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z0-9]{1,}:\d+$', proxy):
            raise Error(create_invalid_value_message(proxy, "setHttpsProxy", "pdf-to-image", 'The value must have format DOMAIN_OR_IP_ADDRESS:PORT.', "set_https_proxy"), 470);
        
        self.fields['https_proxy'] = get_utf8_string(proxy)
        return self

    def setUseHttp(self, value):
        """https://pdfcrowd.com/api/pdf-to-image-python/ref/#set_use_http"""
        self.helper.setUseHttp(value)
        return self

    def setClientUserAgent(self, agent):
        """https://pdfcrowd.com/api/pdf-to-image-python/ref/#set_client_user_agent"""
        self.helper.setUserAgent(agent)
        return self

    def setUserAgent(self, agent):
        """https://pdfcrowd.com/api/pdf-to-image-python/ref/#set_user_agent"""
        self.helper.setUserAgent(agent)
        return self

    def setProxy(self, host, port, user_name, password):
        """https://pdfcrowd.com/api/pdf-to-image-python/ref/#set_proxy"""
        self.helper.setProxy(host, port, user_name, password)
        return self

    def setRetryCount(self, count):
        """https://pdfcrowd.com/api/pdf-to-image-python/ref/#set_retry_count"""
        self.helper.setRetryCount(count)
        return self

