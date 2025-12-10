# Copyright (C) 2009-2018 pdfcrowd.com
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
import argparse
import sys
import os
import ssl
import time
import warnings

__version__ = '6.5.4'

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
CLIENT_VERSION = '6.5.4'

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
        if val:
            yield key, str(val)

def add_file_field(name, file_name, data, body, mime_type = None):
    # file field
    head = []
    head.append('--' + MULTIPART_BOUNDARY)
    head.append('Content-Disposition: form-data; name="{}"; filename="{}"'.format(name, file_name))
    if not mime_type:
        mime_type = 'application/octet-stream'
    head.append('Content-Type: {}'.format(mime_type))
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
        self.setUserAgent('pdfcrowd_python_client/6.5.4 (https://pdfcrowd.com)')

        self.retry_count = 1
        self.converter_version = '24.04'

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
        conv_selector = '/convert/{}/'.format(self.converter_version)
        if self.proxy_host:
            conn = self._create_connection(self.proxy_host, self.proxy_port)
            conn.putrequest('POST', 'http://{}:{}{}'.format(
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
            self.credits = int(response.getheader('X-Pdfcrowd-Remaining-Credits', 999999))
            self.consumed_credits = int(response.getheader('X-Pdfcrowd-Consumed-Credits', 0))
            self.job_id = response.getheader('X-Pdfcrowd-Job-Id', '')
            self.page_count = int(response.getheader('X-Pdfcrowd-Pages', 0))
            self.total_page_count = int(response.getheader('X-Pdfcrowd-Total-Pages', 0))
            self.output_size = int(response.getheader('X-Pdfcrowd-Output-Size', 0))

            if response.status > 299:
                raise Error(response.read(), response.status)

            if out_stream:
                while True:
                    data = response.read(16384)
                    if data:
                        out_stream.write(data)
                    else:
                        break
                return out_stream

            return response.read()
        except httplib.HTTPException as err:
            raise Error(str(err))
        except ssl.SSLError as err:
            raise Error("400.356 - There was a problem connecting to PDFCrowd servers over HTTPS:\n" +
                        "{} ({})".format(err.reason, err.errno) +
                        "\nYou can still use the API over HTTP, you just need to add the following line right after PDFCrowd client initialization:\nclient.setUseHttp(True)",
                        0)
        except socket.gaierror as err:
            raise Error(str(err))
        except socket.error as err:
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
        
        self.fields['url'] = get_utf8_string(url)
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertUrlToStream(self, url, out_stream):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#convert_url_to_stream"""
        if not re.match(r'(?i)^https?://.*$', url):
            raise Error(create_invalid_value_message(url, "convertUrlToStream::url", "html-to-pdf", 'Supported protocols are http:// and https://.', "convert_url_to_stream"), 470);
        
        self.fields['url'] = get_utf8_string(url)
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertUrlToFile(self, url, file_path):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#convert_url_to_file"""
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "convertUrlToFile::file_path", "html-to-pdf", 'The string must not be empty.', "convert_url_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        try:
            self.convertUrlToStream(url, output_file)
            output_file.close()
        except Error:
            output_file.close()
            os.remove(file_path)
            raise

    def convertFile(self, file):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#convert_file"""
        if not (os.path.isfile(file) and os.path.getsize(file)):
            raise Error(create_invalid_value_message(file, "convertFile", "html-to-pdf", 'The file must exist and not be empty.', "convert_file"), 470);
        
        self.files['file'] = get_utf8_string(file)
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertFileToStream(self, file, out_stream):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#convert_file_to_stream"""
        if not (os.path.isfile(file) and os.path.getsize(file)):
            raise Error(create_invalid_value_message(file, "convertFileToStream::file", "html-to-pdf", 'The file must exist and not be empty.', "convert_file_to_stream"), 470);
        
        self.files['file'] = get_utf8_string(file)
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertFileToFile(self, file, file_path):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#convert_file_to_file"""
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "convertFileToFile::file_path", "html-to-pdf", 'The string must not be empty.', "convert_file_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        try:
            self.convertFileToStream(file, output_file)
            output_file.close()
        except Error:
            output_file.close()
            os.remove(file_path)
            raise

    def convertString(self, text):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#convert_string"""
        if not (text):
            raise Error(create_invalid_value_message(text, "convertString", "html-to-pdf", 'The string must not be empty.', "convert_string"), 470);
        
        self.fields['text'] = get_utf8_string(text)
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertStringToStream(self, text, out_stream):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#convert_string_to_stream"""
        if not (text):
            raise Error(create_invalid_value_message(text, "convertStringToStream::text", "html-to-pdf", 'The string must not be empty.', "convert_string_to_stream"), 470);
        
        self.fields['text'] = get_utf8_string(text)
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertStringToFile(self, text, file_path):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#convert_string_to_file"""
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "convertStringToFile::file_path", "html-to-pdf", 'The string must not be empty.', "convert_string_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        try:
            self.convertStringToStream(text, output_file)
            output_file.close()
        except Error:
            output_file.close()
            os.remove(file_path)
            raise

    def convertStream(self, in_stream):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#convert_stream"""
        self.raw_data['stream'] = in_stream.read()
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertStreamToStream(self, in_stream, out_stream):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#convert_stream_to_stream"""
        self.raw_data['stream'] = in_stream.read()
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertStreamToFile(self, in_stream, file_path):
        """https://pdfcrowd.com/api/html-to-pdf-python/ref/#convert_stream_to_file"""
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "convertStreamToFile::file_path", "html-to-pdf", 'The string must not be empty.', "convert_stream_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        try:
            self.convertStreamToStream(in_stream, output_file)
            output_file.close()
        except Error:
            output_file.close()
            os.remove(file_path)
            raise

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
        return 'client {}, API v2, converter {}'.format(CLIENT_VERSION, self.helper.getConverterVersion())

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
        
        self.fields['url'] = get_utf8_string(url)
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertUrlToStream(self, url, out_stream):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#convert_url_to_stream"""
        if not re.match(r'(?i)^https?://.*$', url):
            raise Error(create_invalid_value_message(url, "convertUrlToStream::url", "html-to-image", 'Supported protocols are http:// and https://.', "convert_url_to_stream"), 470);
        
        self.fields['url'] = get_utf8_string(url)
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertUrlToFile(self, url, file_path):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#convert_url_to_file"""
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "convertUrlToFile::file_path", "html-to-image", 'The string must not be empty.', "convert_url_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        try:
            self.convertUrlToStream(url, output_file)
            output_file.close()
        except Error:
            output_file.close()
            os.remove(file_path)
            raise

    def convertFile(self, file):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#convert_file"""
        if not (os.path.isfile(file) and os.path.getsize(file)):
            raise Error(create_invalid_value_message(file, "convertFile", "html-to-image", 'The file must exist and not be empty.', "convert_file"), 470);
        
        self.files['file'] = get_utf8_string(file)
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertFileToStream(self, file, out_stream):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#convert_file_to_stream"""
        if not (os.path.isfile(file) and os.path.getsize(file)):
            raise Error(create_invalid_value_message(file, "convertFileToStream::file", "html-to-image", 'The file must exist and not be empty.', "convert_file_to_stream"), 470);
        
        self.files['file'] = get_utf8_string(file)
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertFileToFile(self, file, file_path):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#convert_file_to_file"""
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "convertFileToFile::file_path", "html-to-image", 'The string must not be empty.', "convert_file_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        try:
            self.convertFileToStream(file, output_file)
            output_file.close()
        except Error:
            output_file.close()
            os.remove(file_path)
            raise

    def convertString(self, text):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#convert_string"""
        if not (text):
            raise Error(create_invalid_value_message(text, "convertString", "html-to-image", 'The string must not be empty.', "convert_string"), 470);
        
        self.fields['text'] = get_utf8_string(text)
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertStringToStream(self, text, out_stream):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#convert_string_to_stream"""
        if not (text):
            raise Error(create_invalid_value_message(text, "convertStringToStream::text", "html-to-image", 'The string must not be empty.', "convert_string_to_stream"), 470);
        
        self.fields['text'] = get_utf8_string(text)
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertStringToFile(self, text, file_path):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#convert_string_to_file"""
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "convertStringToFile::file_path", "html-to-image", 'The string must not be empty.', "convert_string_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        try:
            self.convertStringToStream(text, output_file)
            output_file.close()
        except Error:
            output_file.close()
            os.remove(file_path)
            raise

    def convertStream(self, in_stream):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#convert_stream"""
        self.raw_data['stream'] = in_stream.read()
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertStreamToStream(self, in_stream, out_stream):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#convert_stream_to_stream"""
        self.raw_data['stream'] = in_stream.read()
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertStreamToFile(self, in_stream, file_path):
        """https://pdfcrowd.com/api/html-to-image-python/ref/#convert_stream_to_file"""
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "convertStreamToFile::file_path", "html-to-image", 'The string must not be empty.', "convert_stream_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        try:
            self.convertStreamToStream(in_stream, output_file)
            output_file.close()
        except Error:
            output_file.close()
            os.remove(file_path)
            raise

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
        return 'client {}, API v2, converter {}'.format(CLIENT_VERSION, self.helper.getConverterVersion())

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
        
        self.fields['url'] = get_utf8_string(url)
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertUrlToStream(self, url, out_stream):
        """https://pdfcrowd.com/api/image-to-image-python/ref/#convert_url_to_stream"""
        if not re.match(r'(?i)^https?://.*$', url):
            raise Error(create_invalid_value_message(url, "convertUrlToStream::url", "image-to-image", 'Supported protocols are http:// and https://.', "convert_url_to_stream"), 470);
        
        self.fields['url'] = get_utf8_string(url)
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertUrlToFile(self, url, file_path):
        """https://pdfcrowd.com/api/image-to-image-python/ref/#convert_url_to_file"""
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "convertUrlToFile::file_path", "image-to-image", 'The string must not be empty.', "convert_url_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        try:
            self.convertUrlToStream(url, output_file)
            output_file.close()
        except Error:
            output_file.close()
            os.remove(file_path)
            raise

    def convertFile(self, file):
        """https://pdfcrowd.com/api/image-to-image-python/ref/#convert_file"""
        if not (os.path.isfile(file) and os.path.getsize(file)):
            raise Error(create_invalid_value_message(file, "convertFile", "image-to-image", 'The file must exist and not be empty.', "convert_file"), 470);
        
        self.files['file'] = get_utf8_string(file)
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertFileToStream(self, file, out_stream):
        """https://pdfcrowd.com/api/image-to-image-python/ref/#convert_file_to_stream"""
        if not (os.path.isfile(file) and os.path.getsize(file)):
            raise Error(create_invalid_value_message(file, "convertFileToStream::file", "image-to-image", 'The file must exist and not be empty.', "convert_file_to_stream"), 470);
        
        self.files['file'] = get_utf8_string(file)
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertFileToFile(self, file, file_path):
        """https://pdfcrowd.com/api/image-to-image-python/ref/#convert_file_to_file"""
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "convertFileToFile::file_path", "image-to-image", 'The string must not be empty.', "convert_file_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        try:
            self.convertFileToStream(file, output_file)
            output_file.close()
        except Error:
            output_file.close()
            os.remove(file_path)
            raise

    def convertRawData(self, data):
        """https://pdfcrowd.com/api/image-to-image-python/ref/#convert_raw_data"""
        self.raw_data['file'] = data
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertRawDataToStream(self, data, out_stream):
        """https://pdfcrowd.com/api/image-to-image-python/ref/#convert_raw_data_to_stream"""
        self.raw_data['file'] = data
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertRawDataToFile(self, data, file_path):
        """https://pdfcrowd.com/api/image-to-image-python/ref/#convert_raw_data_to_file"""
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "convertRawDataToFile::file_path", "image-to-image", 'The string must not be empty.', "convert_raw_data_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        try:
            self.convertRawDataToStream(data, output_file)
            output_file.close()
        except Error:
            output_file.close()
            os.remove(file_path)
            raise

    def convertStream(self, in_stream):
        """https://pdfcrowd.com/api/image-to-image-python/ref/#convert_stream"""
        self.raw_data['stream'] = in_stream.read()
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertStreamToStream(self, in_stream, out_stream):
        """https://pdfcrowd.com/api/image-to-image-python/ref/#convert_stream_to_stream"""
        self.raw_data['stream'] = in_stream.read()
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertStreamToFile(self, in_stream, file_path):
        """https://pdfcrowd.com/api/image-to-image-python/ref/#convert_stream_to_file"""
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "convertStreamToFile::file_path", "image-to-image", 'The string must not be empty.', "convert_stream_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        try:
            self.convertStreamToStream(in_stream, output_file)
            output_file.close()
        except Error:
            output_file.close()
            os.remove(file_path)
            raise

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
        return 'client {}, API v2, converter {}'.format(CLIENT_VERSION, self.helper.getConverterVersion())

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
        self.convertToStream(output_file)
        output_file.close()

    def addPdfFile(self, file_path):
        """https://pdfcrowd.com/api/pdf-to-pdf-python/ref/#add_pdf_file"""
        if not (os.path.isfile(file_path) and os.path.getsize(file_path)):
            raise Error(create_invalid_value_message(file_path, "addPdfFile", "pdf-to-pdf", 'The file must exist and not be empty.', "add_pdf_file"), 470);
        
        self.files['f_{}'.format(self.file_id)] = file_path
        self.file_id += 1
        return self

    def addPdfRawData(self, data):
        """https://pdfcrowd.com/api/pdf-to-pdf-python/ref/#add_pdf_raw_data"""
        if not (data and len(data) > 300 and (data[0:4] == '%PDF' or data[0:4] == u'%PDF' or data[0:4] == b'%PDF')):
            raise Error(create_invalid_value_message("raw PDF data", "addPdfRawData", "pdf-to-pdf", 'The input data must be PDF content.', "add_pdf_raw_data"), 470);
        
        self.raw_data['f_{}'.format(self.file_id)] = data
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
        return 'client {}, API v2, converter {}'.format(CLIENT_VERSION, self.helper.getConverterVersion())

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
        
        self.fields['url'] = get_utf8_string(url)
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertUrlToStream(self, url, out_stream):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#convert_url_to_stream"""
        if not re.match(r'(?i)^https?://.*$', url):
            raise Error(create_invalid_value_message(url, "convertUrlToStream::url", "image-to-pdf", 'Supported protocols are http:// and https://.', "convert_url_to_stream"), 470);
        
        self.fields['url'] = get_utf8_string(url)
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertUrlToFile(self, url, file_path):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#convert_url_to_file"""
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "convertUrlToFile::file_path", "image-to-pdf", 'The string must not be empty.', "convert_url_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        try:
            self.convertUrlToStream(url, output_file)
            output_file.close()
        except Error:
            output_file.close()
            os.remove(file_path)
            raise

    def convertFile(self, file):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#convert_file"""
        if not (os.path.isfile(file) and os.path.getsize(file)):
            raise Error(create_invalid_value_message(file, "convertFile", "image-to-pdf", 'The file must exist and not be empty.', "convert_file"), 470);
        
        self.files['file'] = get_utf8_string(file)
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertFileToStream(self, file, out_stream):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#convert_file_to_stream"""
        if not (os.path.isfile(file) and os.path.getsize(file)):
            raise Error(create_invalid_value_message(file, "convertFileToStream::file", "image-to-pdf", 'The file must exist and not be empty.', "convert_file_to_stream"), 470);
        
        self.files['file'] = get_utf8_string(file)
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertFileToFile(self, file, file_path):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#convert_file_to_file"""
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "convertFileToFile::file_path", "image-to-pdf", 'The string must not be empty.', "convert_file_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        try:
            self.convertFileToStream(file, output_file)
            output_file.close()
        except Error:
            output_file.close()
            os.remove(file_path)
            raise

    def convertRawData(self, data):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#convert_raw_data"""
        self.raw_data['file'] = data
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertRawDataToStream(self, data, out_stream):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#convert_raw_data_to_stream"""
        self.raw_data['file'] = data
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertRawDataToFile(self, data, file_path):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#convert_raw_data_to_file"""
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "convertRawDataToFile::file_path", "image-to-pdf", 'The string must not be empty.', "convert_raw_data_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        try:
            self.convertRawDataToStream(data, output_file)
            output_file.close()
        except Error:
            output_file.close()
            os.remove(file_path)
            raise

    def convertStream(self, in_stream):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#convert_stream"""
        self.raw_data['stream'] = in_stream.read()
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertStreamToStream(self, in_stream, out_stream):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#convert_stream_to_stream"""
        self.raw_data['stream'] = in_stream.read()
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertStreamToFile(self, in_stream, file_path):
        """https://pdfcrowd.com/api/image-to-pdf-python/ref/#convert_stream_to_file"""
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "convertStreamToFile::file_path", "image-to-pdf", 'The string must not be empty.', "convert_stream_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        try:
            self.convertStreamToStream(in_stream, output_file)
            output_file.close()
        except Error:
            output_file.close()
            os.remove(file_path)
            raise

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
        return 'client {}, API v2, converter {}'.format(CLIENT_VERSION, self.helper.getConverterVersion())

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
        
        self.fields['url'] = get_utf8_string(url)
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertUrlToStream(self, url, out_stream):
        """https://pdfcrowd.com/api/pdf-to-html-python/ref/#convert_url_to_stream"""
        if not re.match(r'(?i)^https?://.*$', url):
            raise Error(create_invalid_value_message(url, "convertUrlToStream::url", "pdf-to-html", 'Supported protocols are http:// and https://.', "convert_url_to_stream"), 470);
        
        self.fields['url'] = get_utf8_string(url)
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertUrlToFile(self, url, file_path):
        """https://pdfcrowd.com/api/pdf-to-html-python/ref/#convert_url_to_file"""
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "convertUrlToFile::file_path", "pdf-to-html", 'The string must not be empty.', "convert_url_to_file"), 470);
        
        if not (self._isOutputTypeValid(file_path)):
            raise Error(create_invalid_value_message(file_path, "convertUrlToFile::file_path", "pdf-to-html", 'The converter generates an HTML or ZIP file. If ZIP file is generated, the file path must have a ZIP or zip extension.', "convert_url_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        try:
            self.convertUrlToStream(url, output_file)
            output_file.close()
        except Error:
            output_file.close()
            os.remove(file_path)
            raise

    def convertFile(self, file):
        """https://pdfcrowd.com/api/pdf-to-html-python/ref/#convert_file"""
        if not (os.path.isfile(file) and os.path.getsize(file)):
            raise Error(create_invalid_value_message(file, "convertFile", "pdf-to-html", 'The file must exist and not be empty.', "convert_file"), 470);
        
        self.files['file'] = get_utf8_string(file)
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertFileToStream(self, file, out_stream):
        """https://pdfcrowd.com/api/pdf-to-html-python/ref/#convert_file_to_stream"""
        if not (os.path.isfile(file) and os.path.getsize(file)):
            raise Error(create_invalid_value_message(file, "convertFileToStream::file", "pdf-to-html", 'The file must exist and not be empty.', "convert_file_to_stream"), 470);
        
        self.files['file'] = get_utf8_string(file)
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertFileToFile(self, file, file_path):
        """https://pdfcrowd.com/api/pdf-to-html-python/ref/#convert_file_to_file"""
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "convertFileToFile::file_path", "pdf-to-html", 'The string must not be empty.', "convert_file_to_file"), 470);
        
        if not (self._isOutputTypeValid(file_path)):
            raise Error(create_invalid_value_message(file_path, "convertFileToFile::file_path", "pdf-to-html", 'The converter generates an HTML or ZIP file. If ZIP file is generated, the file path must have a ZIP or zip extension.', "convert_file_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        try:
            self.convertFileToStream(file, output_file)
            output_file.close()
        except Error:
            output_file.close()
            os.remove(file_path)
            raise

    def convertRawData(self, data):
        """https://pdfcrowd.com/api/pdf-to-html-python/ref/#convert_raw_data"""
        self.raw_data['file'] = data
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertRawDataToStream(self, data, out_stream):
        """https://pdfcrowd.com/api/pdf-to-html-python/ref/#convert_raw_data_to_stream"""
        self.raw_data['file'] = data
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertRawDataToFile(self, data, file_path):
        """https://pdfcrowd.com/api/pdf-to-html-python/ref/#convert_raw_data_to_file"""
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "convertRawDataToFile::file_path", "pdf-to-html", 'The string must not be empty.', "convert_raw_data_to_file"), 470);
        
        if not (self._isOutputTypeValid(file_path)):
            raise Error(create_invalid_value_message(file_path, "convertRawDataToFile::file_path", "pdf-to-html", 'The converter generates an HTML or ZIP file. If ZIP file is generated, the file path must have a ZIP or zip extension.', "convert_raw_data_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        try:
            self.convertRawDataToStream(data, output_file)
            output_file.close()
        except Error:
            output_file.close()
            os.remove(file_path)
            raise

    def convertStream(self, in_stream):
        """https://pdfcrowd.com/api/pdf-to-html-python/ref/#convert_stream"""
        self.raw_data['stream'] = in_stream.read()
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertStreamToStream(self, in_stream, out_stream):
        """https://pdfcrowd.com/api/pdf-to-html-python/ref/#convert_stream_to_stream"""
        self.raw_data['stream'] = in_stream.read()
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertStreamToFile(self, in_stream, file_path):
        """https://pdfcrowd.com/api/pdf-to-html-python/ref/#convert_stream_to_file"""
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "convertStreamToFile::file_path", "pdf-to-html", 'The string must not be empty.', "convert_stream_to_file"), 470);
        
        if not (self._isOutputTypeValid(file_path)):
            raise Error(create_invalid_value_message(file_path, "convertStreamToFile::file_path", "pdf-to-html", 'The converter generates an HTML or ZIP file. If ZIP file is generated, the file path must have a ZIP or zip extension.', "convert_stream_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        try:
            self.convertStreamToStream(in_stream, output_file)
            output_file.close()
        except Error:
            output_file.close()
            os.remove(file_path)
            raise

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
        return 'client {}, API v2, converter {}'.format(CLIENT_VERSION, self.helper.getConverterVersion())

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
        
        self.fields['url'] = get_utf8_string(url)
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertUrlToStream(self, url, out_stream):
        """https://pdfcrowd.com/api/pdf-to-text-python/ref/#convert_url_to_stream"""
        if not re.match(r'(?i)^https?://.*$', url):
            raise Error(create_invalid_value_message(url, "convertUrlToStream::url", "pdf-to-text", 'Supported protocols are http:// and https://.', "convert_url_to_stream"), 470);
        
        self.fields['url'] = get_utf8_string(url)
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertUrlToFile(self, url, file_path):
        """https://pdfcrowd.com/api/pdf-to-text-python/ref/#convert_url_to_file"""
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "convertUrlToFile::file_path", "pdf-to-text", 'The string must not be empty.', "convert_url_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        try:
            self.convertUrlToStream(url, output_file)
            output_file.close()
        except Error:
            output_file.close()
            os.remove(file_path)
            raise

    def convertFile(self, file):
        """https://pdfcrowd.com/api/pdf-to-text-python/ref/#convert_file"""
        if not (os.path.isfile(file) and os.path.getsize(file)):
            raise Error(create_invalid_value_message(file, "convertFile", "pdf-to-text", 'The file must exist and not be empty.', "convert_file"), 470);
        
        self.files['file'] = get_utf8_string(file)
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertFileToStream(self, file, out_stream):
        """https://pdfcrowd.com/api/pdf-to-text-python/ref/#convert_file_to_stream"""
        if not (os.path.isfile(file) and os.path.getsize(file)):
            raise Error(create_invalid_value_message(file, "convertFileToStream::file", "pdf-to-text", 'The file must exist and not be empty.', "convert_file_to_stream"), 470);
        
        self.files['file'] = get_utf8_string(file)
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertFileToFile(self, file, file_path):
        """https://pdfcrowd.com/api/pdf-to-text-python/ref/#convert_file_to_file"""
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "convertFileToFile::file_path", "pdf-to-text", 'The string must not be empty.', "convert_file_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        try:
            self.convertFileToStream(file, output_file)
            output_file.close()
        except Error:
            output_file.close()
            os.remove(file_path)
            raise

    def convertRawData(self, data):
        """https://pdfcrowd.com/api/pdf-to-text-python/ref/#convert_raw_data"""
        self.raw_data['file'] = data
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertRawDataToStream(self, data, out_stream):
        """https://pdfcrowd.com/api/pdf-to-text-python/ref/#convert_raw_data_to_stream"""
        self.raw_data['file'] = data
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertRawDataToFile(self, data, file_path):
        """https://pdfcrowd.com/api/pdf-to-text-python/ref/#convert_raw_data_to_file"""
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "convertRawDataToFile::file_path", "pdf-to-text", 'The string must not be empty.', "convert_raw_data_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        try:
            self.convertRawDataToStream(data, output_file)
            output_file.close()
        except Error:
            output_file.close()
            os.remove(file_path)
            raise

    def convertStream(self, in_stream):
        """https://pdfcrowd.com/api/pdf-to-text-python/ref/#convert_stream"""
        self.raw_data['stream'] = in_stream.read()
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertStreamToStream(self, in_stream, out_stream):
        """https://pdfcrowd.com/api/pdf-to-text-python/ref/#convert_stream_to_stream"""
        self.raw_data['stream'] = in_stream.read()
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertStreamToFile(self, in_stream, file_path):
        """https://pdfcrowd.com/api/pdf-to-text-python/ref/#convert_stream_to_file"""
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "convertStreamToFile::file_path", "pdf-to-text", 'The string must not be empty.', "convert_stream_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        try:
            self.convertStreamToStream(in_stream, output_file)
            output_file.close()
        except Error:
            output_file.close()
            os.remove(file_path)
            raise

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
        return 'client {}, API v2, converter {}'.format(CLIENT_VERSION, self.helper.getConverterVersion())

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
        
        self.fields['url'] = get_utf8_string(url)
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertUrlToStream(self, url, out_stream):
        """https://pdfcrowd.com/api/pdf-to-image-python/ref/#convert_url_to_stream"""
        if not re.match(r'(?i)^https?://.*$', url):
            raise Error(create_invalid_value_message(url, "convertUrlToStream::url", "pdf-to-image", 'Supported protocols are http:// and https://.', "convert_url_to_stream"), 470);
        
        self.fields['url'] = get_utf8_string(url)
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertUrlToFile(self, url, file_path):
        """https://pdfcrowd.com/api/pdf-to-image-python/ref/#convert_url_to_file"""
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "convertUrlToFile::file_path", "pdf-to-image", 'The string must not be empty.', "convert_url_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        try:
            self.convertUrlToStream(url, output_file)
            output_file.close()
        except Error:
            output_file.close()
            os.remove(file_path)
            raise

    def convertFile(self, file):
        """https://pdfcrowd.com/api/pdf-to-image-python/ref/#convert_file"""
        if not (os.path.isfile(file) and os.path.getsize(file)):
            raise Error(create_invalid_value_message(file, "convertFile", "pdf-to-image", 'The file must exist and not be empty.', "convert_file"), 470);
        
        self.files['file'] = get_utf8_string(file)
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertFileToStream(self, file, out_stream):
        """https://pdfcrowd.com/api/pdf-to-image-python/ref/#convert_file_to_stream"""
        if not (os.path.isfile(file) and os.path.getsize(file)):
            raise Error(create_invalid_value_message(file, "convertFileToStream::file", "pdf-to-image", 'The file must exist and not be empty.', "convert_file_to_stream"), 470);
        
        self.files['file'] = get_utf8_string(file)
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertFileToFile(self, file, file_path):
        """https://pdfcrowd.com/api/pdf-to-image-python/ref/#convert_file_to_file"""
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "convertFileToFile::file_path", "pdf-to-image", 'The string must not be empty.', "convert_file_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        try:
            self.convertFileToStream(file, output_file)
            output_file.close()
        except Error:
            output_file.close()
            os.remove(file_path)
            raise

    def convertRawData(self, data):
        """https://pdfcrowd.com/api/pdf-to-image-python/ref/#convert_raw_data"""
        self.raw_data['file'] = data
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertRawDataToStream(self, data, out_stream):
        """https://pdfcrowd.com/api/pdf-to-image-python/ref/#convert_raw_data_to_stream"""
        self.raw_data['file'] = data
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertRawDataToFile(self, data, file_path):
        """https://pdfcrowd.com/api/pdf-to-image-python/ref/#convert_raw_data_to_file"""
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "convertRawDataToFile::file_path", "pdf-to-image", 'The string must not be empty.', "convert_raw_data_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        try:
            self.convertRawDataToStream(data, output_file)
            output_file.close()
        except Error:
            output_file.close()
            os.remove(file_path)
            raise

    def convertStream(self, in_stream):
        """https://pdfcrowd.com/api/pdf-to-image-python/ref/#convert_stream"""
        self.raw_data['stream'] = in_stream.read()
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertStreamToStream(self, in_stream, out_stream):
        """https://pdfcrowd.com/api/pdf-to-image-python/ref/#convert_stream_to_stream"""
        self.raw_data['stream'] = in_stream.read()
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertStreamToFile(self, in_stream, file_path):
        """https://pdfcrowd.com/api/pdf-to-image-python/ref/#convert_stream_to_file"""
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "convertStreamToFile::file_path", "pdf-to-image", 'The string must not be empty.', "convert_stream_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        try:
            self.convertStreamToStream(in_stream, output_file)
            output_file.close()
        except Error:
            output_file.close()
            os.remove(file_path)
            raise

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
        return 'client {}, API v2, converter {}'.format(CLIENT_VERSION, self.helper.getConverterVersion())

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


def main(argv, converter_known = False):
    def show_help():
        print("""
usage: pdfcrowd.py <converter> [options] [args]
help: pdfcrowd.py help <converter>

available converters:
  html2pdf - Conversion from HTML to PDF.
  html2image - Conversion from HTML to image.
  image2image - Conversion from one image format to another image format.
  pdf2pdf - Conversion from PDF to PDF.
  image2pdf - Conversion from an image to PDF.
  pdf2html - Conversion from PDF to HTML.
  pdf2text - Conversion from PDF to text.
  pdf2image - Conversion from PDF to image.
        """)

    def term_error(message):
        sys.stderr.write(message + '\n')
        sys.exit(1)

    def add_generic_args(parser, nsource = 1):
        parser.add_argument('source',
                            help = "Source to be converted. It can be URL, path to a local file or '-' to use stdin as an input text." if nsource == 1 else "Input files used for a conversion.",
                            nargs = nsource)
        parser.add_argument('-user-name', help = 'Your user name at pdfcrowd.com.')
        parser.add_argument('-api-key', help = 'Your API key at pdfcrowd.com.')

    if not len(argv):
        show_help()
        sys.exit()

    help_wanted = False

    converter = argv[0]

    if len(argv) == 1:
        if argv[0] == 'help':
            show_help()
            sys.exit()
        help_wanted = True
    elif argv[0] == 'help':
        converter = argv[1]
        help_wanted = True

    parser = None
    usage = '%(prog)s'
    if not converter_known:
        usage += ' ' + converter
    usage += ' [options] source'
    epilog = 'produced by: www.pdfcrowd.com'
    multi_args = {}

    if converter == 'html2pdf':
        converter_name = 'HtmlToPdfClient'

        parser = argparse.ArgumentParser(usage = usage,
                                         description = 'Conversion from HTML to PDF.',
                                         add_help = False,
                                         epilog = epilog)

        add_generic_args(parser)

        parser.add_argument('-zip-main-filename',
                            help = 'Set the file name of the main HTML document stored in the input archive. Use this when your ZIP/TAR archive contains multiple HTML files and you need to specify which one to convert. If not specified, the first HTML file found in the archive is automatically used for conversion. The file name.')
        parser.add_argument('-page-size',
                            help = 'Set the output page size using standard formats (A4, Letter, A3, etc.). Use A4 for international documents, Letter for US-based content, or larger sizes like A3 for posters and presentations. Allowed values are A0, A1, A2, A3, A4, A5, A6, Letter. Default is A4.')
        parser.add_argument('-page-width',
                            help = 'Set custom page dimensions when standard sizes don\'t fit your needs. Useful for banners, receipts, custom forms, or when matching specific printing equipment. The safe maximum is 200in - larger sizes may fail to open in some PDF viewers. For standard sizes like A4 or Letter, use the predefined page size option instead. The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'. Default is 8.27in.')
        parser.add_argument('-page-height',
                            help = 'Set custom page height for specific formats like receipts, banners, or legal documents. Set to "-1" for a single-page PDF that expands to fit all content vertically - ideal for web pages, infographics, or documents where page breaks are undesirable. The safe maximum is 200in otherwise some viewers cannot open the PDF. For standard sizes, use the predefined page size option instead. The value must be -1 or specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'. Default is 11.7in.')
        multi_args['page_dimensions'] = 2
        parser.add_argument('-page-dimensions',
                            help = 'Set both page width and height simultaneously for custom page sizes. Use this when you need non-standard dimensions like banners, receipts, or custom forms that don\'t match A4, Letter, or other predefined sizes. Provide width and height with units (e.g., "210mm", "8.5in"). Maximum safe value is 200in for each dimension - larger sizes may fail to open in some PDF viewers. PAGE_DIMENSIONS must contain 2 values separated by a semicolon. Set custom page dimensions when standard sizes don\'t fit your needs. Useful for banners, receipts, custom forms, or when matching specific printing equipment. The safe maximum is 200in - larger sizes may fail to open in some PDF viewers. For standard sizes like A4 or Letter, use the predefined page size option instead. The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'. Set custom page height for specific formats like receipts, banners, or legal documents. Set to "-1" for a single-page PDF that expands to fit all content vertically - ideal for web pages, infographics, or documents where page breaks are undesirable. The safe maximum is 200in otherwise some viewers cannot open the PDF. For standard sizes, use the predefined page size option instead. The value must be -1 or specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'.')
        parser.add_argument('-orientation',
                            help = 'Set the output page orientation to portrait or landscape. Use landscape for wide content like spreadsheets, charts, or dashboards. Use portrait for standard documents and text-heavy content. Allowed values are landscape, portrait. Default is portrait.')
        parser.add_argument('-margin-top',
                            help = 'Control white space at the top of the page. Increase for header space, formal documents, or annotation room (e.g., 1in or more). Decrease to maximize content area or fit more content (e.g., 5mm to 10mm). Default 0.4in balances readability with space efficiency. Set to 0 for full-bleed designs. Affects where content starts and where headers appear. The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'. Default is 0.4in.')
        parser.add_argument('-margin-right',
                            help = 'Control white space on the right edge of the page. Increase for binding/hole-punch clearance or note-taking space (e.g., 1in or more). Decrease to fit wider content (e.g., 5mm to 10mm). Default 0.4in balances readability with space efficiency. Set to 0 for full-bleed designs. Affects where content wraps and text line length. The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'. Default is 0.4in.')
        parser.add_argument('-margin-bottom',
                            help = 'Control white space at the bottom of the page. Increase for footer space, page numbers, or formal documents (e.g., 1in or more). Decrease to fit more content per page (e.g., 5mm to 10mm). Default 0.4in balances readability with space efficiency. Set to 0 for full-bleed designs. Affects where content ends and where footers appear. The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'. Default is 0.4in.')
        parser.add_argument('-margin-left',
                            help = 'Control white space on the left edge of the page. Increase for binding/hole-punch clearance or note-taking space (e.g., 1in or more). Decrease to fit wider content (e.g., 5mm to 10mm). Default 0.4in balances readability with space efficiency. Set to 0 for full-bleed designs. Affects where content starts horizontally and text line length. The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'. Default is 0.4in.')
        parser.add_argument('-no-margins',
                            action = 'store_true',
                            help = 'Disable all page margins to use the entire page area. Use this for full-bleed designs where content should extend to the page edges, such as posters, certificates, or branded materials. Combine with custom CSS to ensure your content fills the page properly.')
        multi_args['page_margins'] = 4
        parser.add_argument('-page-margins',
                            help = 'Set all four page margins (top, right, bottom, left) simultaneously for consistent spacing. Use this when you need uniform margins for binding, formal documents, or when applying the same spacing to all edges at once. Provide margin values with units (e.g., "1in", "25mm"). Use larger values (1in+) for binding clearance or annotations, smaller values (5-10mm) to maximize content area. Set to "0" for full-bleed designs. PAGE_MARGINS must contain 4 values separated by a semicolon. Control white space at the top of the page. Increase for header space, formal documents, or annotation room (e.g., 1in or more). Decrease to maximize content area or fit more content (e.g., 5mm to 10mm). Default 0.4in balances readability with space efficiency. Set to 0 for full-bleed designs. Affects where content starts and where headers appear. Control white space on the right edge of the page. Increase for binding/hole-punch clearance or note-taking space (e.g., 1in or more). Decrease to fit wider content (e.g., 5mm to 10mm). Default 0.4in balances readability with space efficiency. Set to 0 for full-bleed designs. Affects where content wraps and text line length. Control white space at the bottom of the page. Increase for footer space, page numbers, or formal documents (e.g., 1in or more). Decrease to fit more content per page (e.g., 5mm to 10mm). Default 0.4in balances readability with space efficiency. Set to 0 for full-bleed designs. Affects where content ends and where footers appear. Control white space on the left edge of the page. Increase for binding/hole-punch clearance or note-taking space (e.g., 1in or more). Decrease to fit wider content (e.g., 5mm to 10mm). Default 0.4in balances readability with space efficiency. Set to 0 for full-bleed designs. Affects where content starts horizontally and text line length. All values the value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'.')
        parser.add_argument('-print-page-range',
                            help = 'Set the page range to print when you only need specific pages from the conversion. Use this to extract individual pages (e.g., "2"), specific ranges (e.g., "3-7"), or combinations (e.g., "1,4-6,last"). Ideal for creating excerpts from long documents or excluding cover pages from batch processing. A comma separated list of page numbers or ranges. Special strings may be used, such as \'odd\', \'even\' and \'last\'.')
        parser.add_argument('-content-viewport-width',
                            help = 'Set the viewport width for formatting the HTML content when generating a PDF. Use this to control how responsive designs render - prevent mobile styles from applying when you want desktop layout, or ensure content appears at the right width. Specify a viewport width to control content rendering, ensuring it mimics the appearance on various devices or matches specific design requirements. The width of the viewport. The value must be \'balanced\', \'small\', \'medium\', \'large\', \'extra-large\', or a number in the range 96-65000px. Default is medium.')
        parser.add_argument('-content-viewport-height',
                            help = 'Set the viewport height for formatting the HTML content when generating a PDF. Specify a viewport height to enforce loading of lazy-loaded images and affect vertical positioning of absolutely positioned elements within the content. The viewport height. The value must be \'auto\', \'large\', or a number. Default is auto.')
        parser.add_argument('-content-fit-mode',
                            help = 'Specify the mode for fitting the HTML content to the print area by upscaling or downscaling it. Use this to prevent content from being cut off at page edges or to enable smart scaling of oversized content. The fitting mode. Allowed values are auto, smart-scaling, no-scaling, viewport-width, content-width, single-page, single-page-ratio. Default is auto.')
        parser.add_argument('-remove-blank-pages',
                            help = 'Specify which blank pages to exclude from the output document to create cleaner PDFs. Use "trailing" to remove empty pages at the end caused by page break issues. Use "all" to remove blank pages throughout the document when converting content with formatting quirks. Helps eliminate unwanted white pages from the final output. The empty page behavior. Allowed values are trailing, all, none. Default is trailing.')
        parser.add_argument('-header-url',
                            help = 'Load an HTML code from the specified URL and use it as the page header. The following classes can be used in the HTML. The content of the respective elements will be expanded as follows: pdfcrowd-page-count - the total page count of printed pages pdfcrowd-page-number - the current page number pdfcrowd-source-url - the source URL of the converted document pdfcrowd-source-title - the title of the converted document The following attributes can be used: data-pdfcrowd-number-format - specifies the type of the used numerals. Allowed values: arabic - Arabic numerals, they are used by default roman - Roman numerals eastern-arabic - Eastern Arabic numerals bengali - Bengali numerals devanagari - Devanagari numerals thai - Thai numerals east-asia - Chinese, Vietnamese, Japanese and Korean numerals chinese-formal - Chinese formal numerals Example: <span class=\'pdfcrowd-page-number\' data-pdfcrowd-number-format=\'roman\'></span> data-pdfcrowd-placement - specifies where to place the source URL. Allowed values: The URL is inserted to the content Example: <span class=\'pdfcrowd-source-url\'></span> will produce <span>http://example.com</span> href - the URL is set to the href attribute Example: <a class=\'pdfcrowd-source-url\' data-pdfcrowd-placement=\'href\'>Link to source</a> will produce <a href=\'http://example.com\'>Link to source</a> href-and-content - the URL is set to the href attribute and to the content Example: <a class=\'pdfcrowd-source-url\' data-pdfcrowd-placement=\'href-and-content\'></a> will produce <a href=\'http://example.com\'>http://example.com</a> Supported protocols are http:// and https://.')
        parser.add_argument('-header-html',
                            help = 'Set the HTML header content with custom styling and dynamic page numbers. Use this to add page numbers, document titles, author names, dates, or company branding to the top of every page. Supports full HTML/CSS for complete design control. Use special CSS classes like pdfcrowd-page-number and pdfcrowd-page-count for dynamic content. Ideal for reports, invoices, and professional documents. The following classes can be used in the HTML. The content of the respective elements will be expanded as follows: pdfcrowd-page-count - the total page count of printed pages pdfcrowd-page-number - the current page number pdfcrowd-source-url - the source URL of the converted document pdfcrowd-source-title - the title of the converted document The following attributes can be used: data-pdfcrowd-number-format - specifies the type of the used numerals. Allowed values: arabic - Arabic numerals, they are used by default roman - Roman numerals eastern-arabic - Eastern Arabic numerals bengali - Bengali numerals devanagari - Devanagari numerals thai - Thai numerals east-asia - Chinese, Vietnamese, Japanese and Korean numerals chinese-formal - Chinese formal numerals Example: <span class=\'pdfcrowd-page-number\' data-pdfcrowd-number-format=\'roman\'></span> data-pdfcrowd-placement - specifies where to place the source URL. Allowed values: The URL is inserted to the content Example: <span class=\'pdfcrowd-source-url\'></span> will produce <span>http://example.com</span> href - the URL is set to the href attribute Example: <a class=\'pdfcrowd-source-url\' data-pdfcrowd-placement=\'href\'>Link to source</a> will produce <a href=\'http://example.com\'>Link to source</a> href-and-content - the URL is set to the href attribute and to the content Example: <a class=\'pdfcrowd-source-url\' data-pdfcrowd-placement=\'href-and-content\'></a> will produce <a href=\'http://example.com\'>http://example.com</a> The string must not be empty.')
        parser.add_argument('-header-height',
                            help = 'Set the header height to allocate space for header content and prevent overlap with main content. Increase this if your header text is getting cut off or overlapping with page content. Must be large enough to accommodate your header HTML including any multi-line text or images. The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'. Default is 0.5in.')
        parser.add_argument('-zip-header-filename',
                            help = 'Set the file name of the header HTML document stored in the input archive. Use this method if the input archive contains multiple HTML documents. The file name.')
        parser.add_argument('-footer-url',
                            help = 'Load an HTML code from the specified URL and use it as the page footer. The following classes can be used in the HTML. The content of the respective elements will be expanded as follows: pdfcrowd-page-count - the total page count of printed pages pdfcrowd-page-number - the current page number pdfcrowd-source-url - the source URL of the converted document pdfcrowd-source-title - the title of the converted document The following attributes can be used: data-pdfcrowd-number-format - specifies the type of the used numerals. Allowed values: arabic - Arabic numerals, they are used by default roman - Roman numerals eastern-arabic - Eastern Arabic numerals bengali - Bengali numerals devanagari - Devanagari numerals thai - Thai numerals east-asia - Chinese, Vietnamese, Japanese and Korean numerals chinese-formal - Chinese formal numerals Example: <span class=\'pdfcrowd-page-number\' data-pdfcrowd-number-format=\'roman\'></span> data-pdfcrowd-placement - specifies where to place the source URL. Allowed values: The URL is inserted to the content Example: <span class=\'pdfcrowd-source-url\'></span> will produce <span>http://example.com</span> href - the URL is set to the href attribute Example: <a class=\'pdfcrowd-source-url\' data-pdfcrowd-placement=\'href\'>Link to source</a> will produce <a href=\'http://example.com\'>Link to source</a> href-and-content - the URL is set to the href attribute and to the content Example: <a class=\'pdfcrowd-source-url\' data-pdfcrowd-placement=\'href-and-content\'></a> will produce <a href=\'http://example.com\'>http://example.com</a> Supported protocols are http:// and https://.')
        parser.add_argument('-footer-html',
                            help = 'Set the HTML footer content with custom styling and dynamic page numbers. Use this to add page numbers, copyright notices, document dates, or company information to the bottom of every page. Supports full HTML/CSS for complete design control. Use special CSS classes like pdfcrowd-page-number and pdfcrowd-page-count for dynamic content. Ideal for contracts, reports, and official documents. The following classes can be used in the HTML. The content of the respective elements will be expanded as follows: pdfcrowd-page-count - the total page count of printed pages pdfcrowd-page-number - the current page number pdfcrowd-source-url - the source URL of the converted document pdfcrowd-source-title - the title of the converted document The following attributes can be used: data-pdfcrowd-number-format - specifies the type of the used numerals. Allowed values: arabic - Arabic numerals, they are used by default roman - Roman numerals eastern-arabic - Eastern Arabic numerals bengali - Bengali numerals devanagari - Devanagari numerals thai - Thai numerals east-asia - Chinese, Vietnamese, Japanese and Korean numerals chinese-formal - Chinese formal numerals Example: <span class=\'pdfcrowd-page-number\' data-pdfcrowd-number-format=\'roman\'></span> data-pdfcrowd-placement - specifies where to place the source URL. Allowed values: The URL is inserted to the content Example: <span class=\'pdfcrowd-source-url\'></span> will produce <span>http://example.com</span> href - the URL is set to the href attribute Example: <a class=\'pdfcrowd-source-url\' data-pdfcrowd-placement=\'href\'>Link to source</a> will produce <a href=\'http://example.com\'>Link to source</a> href-and-content - the URL is set to the href attribute and to the content Example: <a class=\'pdfcrowd-source-url\' data-pdfcrowd-placement=\'href-and-content\'></a> will produce <a href=\'http://example.com\'>http://example.com</a> The string must not be empty.')
        parser.add_argument('-footer-height',
                            help = 'Set the footer height to allocate space for footer content and prevent overlap with main content. Increase this if your footer text is getting cut off or overlapping with page content. Must be large enough to accommodate your footer HTML including any multi-line text or images. The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'. Default is 0.5in.')
        parser.add_argument('-zip-footer-filename',
                            help = 'Set the file name of the footer HTML document stored in the input archive. Use this method if the input archive contains multiple HTML documents. The file name.')
        parser.add_argument('-no-header-footer-horizontal-margins',
                            action = 'store_true',
                            help = 'Disable horizontal page margins for header and footer. The header/footer contents width will be equal to the physical page width.')
        parser.add_argument('-exclude-header-on-pages',
                            help = 'The page header content is not printed on the specified pages. To remove the entire header area, use the conversion config. List of physical page numbers. Negative numbers count backwards from the last page: -1 is the last page, -2 is the last but one page, and so on. A comma separated list of page numbers.')
        parser.add_argument('-exclude-footer-on-pages',
                            help = 'The page footer content is not printed on the specified pages. To remove the entire footer area, use the conversion config. List of physical page numbers. Negative numbers count backwards from the last page: -1 is the last page, -2 is the last but one page, and so on. A comma separated list of page numbers.')
        parser.add_argument('-header-footer-scale-factor',
                            help = 'Set the scaling factor (zoom) for the header and footer. The percentage value. The accepted range is 10-500. Default is 100.')
        parser.add_argument('-page-numbering-offset',
                            help = 'Set the numbering offset for page numbers in header/footer HTML to continue page numbering from a previous document. Use this when generating document sections separately - for example, if you have already generated pages 1-10, set offset to 10. The next section will then start numbering at page 11. Essential for multi-part reports or book chapters. Integer specifying page offset.')
        parser.add_argument('-page-watermark',
                            help = 'Apply the first page of a watermark PDF to every page of the output PDF. Use this to add transparent overlays like "DRAFT" stamps, security markings, or branding elements that appear on top of content. Ideal for confidential document marking or adding protective overlays. The file path to a local file. The file must exist and not be empty.')
        parser.add_argument('-page-watermark-url',
                            help = 'Load a file from the specified URL and apply the file as a watermark to each page of the output PDF. A watermark can be either a PDF or an image. If a multi-page file (PDF or TIFF) is used, the first page is used as the watermark. Supported protocols are http:// and https://.')
        parser.add_argument('-multipage-watermark',
                            help = 'Apply each page of a watermark PDF to the corresponding page of the output PDF. Use this for page-specific watermarks where different pages need different overlays - for example, different approval stamps per department. If the watermark has fewer pages than the output, the last watermark page is repeated for remaining pages. The file path to a local file. The file must exist and not be empty.')
        parser.add_argument('-multipage-watermark-url',
                            help = 'Load a file from the specified URL and apply each page of the file as a watermark to the corresponding page of the output PDF. A watermark can be either a PDF or an image. Supported protocols are http:// and https://.')
        parser.add_argument('-page-background',
                            help = 'Apply the first page of a background PDF to every page of the output PDF. Use this to add letterheads, branded templates, or decorative backgrounds that appear behind your content. Backgrounds appear beneath content, while watermarks layer on top. Perfect for adding company letterheads to reports or applying branded templates to dynamically generated content. The file path to a local file. The file must exist and not be empty.')
        parser.add_argument('-page-background-url',
                            help = 'Load a file from the specified URL and apply the file as a background to each page of the output PDF. A background can be either a PDF or an image. If a multi-page file (PDF or TIFF) is used, the first page is used as the background. Supported protocols are http:// and https://.')
        parser.add_argument('-multipage-background',
                            help = 'Apply each page of a background PDF to the corresponding page of the output PDF. Use this for page-specific backgrounds where each page needs a different template - for example, different letterheads for front and back pages. If the background has fewer pages than the output, the last background page is repeated for remaining pages. The file path to a local file. The file must exist and not be empty.')
        parser.add_argument('-multipage-background-url',
                            help = 'Load a file from the specified URL and apply each page of the file as a background to the corresponding page of the output PDF. A background can be either a PDF or an image. Supported protocols are http:// and https://.')
        parser.add_argument('-page-background-color',
                            help = 'Set a solid background color for all pages, filling the entire page area including margins. Useful for creating branded PDFs with corporate colors, highlighting draft documents, or improving readability with off-white backgrounds. Supports transparency with RGBA format - use semi-transparent colors for subtle effects without obscuring content. Format as RGB (FF0000) or RGBA (FF000080) hexadecimal. The value must be in RRGGBB or RRGGBBAA hexadecimal format.')
        parser.add_argument('-use-print-media',
                            action = 'store_true',
                            help = 'Use the print version of the page if available via @media print CSS rules. Enable this when converting websites that have print-optimized styles. Many sites hide navigation, ads, and sidebars in print mode. Produces cleaner PDFs by using the design the website creator intended for printing.')
        parser.add_argument('-no-background',
                            action = 'store_true',
                            help = 'Do not print the background graphics to create printer-friendly PDFs. Use this when documents will be physically printed to save ink costs and improve readability. Removes background colors, images, and patterns while preserving text and foreground content. Particularly useful for documents with dark backgrounds or decorative elements.')
        parser.add_argument('-disable-javascript',
                            action = 'store_true',
                            help = 'Do not execute JavaScript during conversion. Use this to improve conversion speed when JavaScript is not needed, prevent dynamic content changes, or avoid security risks from untrusted scripts. Note that disabling JavaScript means lazy-loaded images and AJAX content will not load.')
        parser.add_argument('-disable-image-loading',
                            action = 'store_true',
                            help = 'Do not load images during conversion to create text-only PDFs. Use this to significantly speed up conversion, reduce file size, or create accessible text-focused documents. Ideal for converting documentation where images are not needed, reducing bandwidth usage, or creating lightweight PDFs for email distribution.')
        parser.add_argument('-disable-remote-fonts',
                            action = 'store_true',
                            help = 'Disable loading fonts from remote sources. Use this to speed up conversion by avoiding font download delays, ensure consistent rendering with system fonts, or work around font loading failures. Note that text will fall back to system fonts, which may change the document\'s appearance.')
        parser.add_argument('-use-mobile-user-agent',
                            action = 'store_true',
                            help = 'Use a mobile user agent when making requests to the source URL.')
        parser.add_argument('-load-iframes',
                            help = 'Specifies how iframes are handled during conversion. Use "all" to include all embedded content (videos, maps, widgets). Use "same-origin" to include only content from the same domain for security purposes. Use "none" to exclude all iframes for faster conversion and to avoid third-party content issues. Disabling iframes can significantly improve performance and reliability. Allowed values are all, same-origin, none. Default is all.')
        parser.add_argument('-block-ads',
                            action = 'store_true',
                            help = 'Automatically block common advertising networks and tracking scripts during conversion, producing cleaner PDFs with faster conversion times. Filters out third-party ad content, analytics beacons, and ad network resources. Ideal for converting news sites, blogs, or any ad-heavy content where ads distract from the main message. May occasionally block legitimate third-party content - disable if critical third-party resources are missing.')
        parser.add_argument('-default-encoding',
                            help = 'Specify the character encoding when the HTML lacks proper charset declaration or has incorrect encoding. Prevents garbled text for non-English content, especially legacy pages without UTF-8 encoding. Set to "utf-8" for modern content, "iso-8859-1" for Western European legacy pages, or other encodings for specific regional content. Only needed when auto-detection fails and you see corrupted characters in the output. The text encoding of the HTML content. Default is auto detect.')
        parser.add_argument('-locale',
                            help = 'Set the locale for the conversion to control regional formatting of dates, times, and numbers. Use this when converting content for specific regions - for example, set to "en-US" for MM/DD/YYYY dates and comma thousand separators, or "de-DE" for DD.MM.YYYY dates and period thousand separators. Essential for financial reports, invoices, or localized content. The locale code according to ISO 639. Default is en-US.')
        parser.add_argument('-http-auth-user-name',
                            help = argparse.SUPPRESS
)
        parser.add_argument('-http-auth-password',
                            help = argparse.SUPPRESS
)
        multi_args['http_auth'] = 2
        parser.add_argument('-http-auth',
                            help = 'Set credentials to access HTTP basic authentication protected websites. Use this when converting content behind HTTP authentication, such as development servers, staging environments, or password-protected documentation. Provide both username and password to authenticate requests. Essential for converting internal resources or protected content. HTTP_AUTH must contain 2 values separated by a semicolon. Set the HTTP authentication user name. Required to access protected web pages or staging environments. Set the HTTP authentication password. Required to access protected web pages or staging environments.')
        parser.add_argument('-cookies',
                            help = 'Set HTTP cookies to be included in all requests made by the converter to access authenticated or session-based content. Use this when converting pages that require login, maintain user sessions, or personalize content based on cookies. Essential for converting member-only areas, dashboards, or any content behind cookie-based authentication. Format as semicolon-separated name=value pairs. The cookie string.')
        parser.add_argument('-verify-ssl-certificates',
                            action = 'store_true',
                            help = 'Enforce SSL certificate validation for secure connections, preventing conversions from sites with invalid certificates. Enable when converting from production sites with valid certificates to ensure security. When disabled, allows conversion from any HTTPS site regardless of certificate validity - including development servers with self-signed certificates, internal corporate sites with expired certificates, or local testing environments.')
        parser.add_argument('-fail-on-main-url-error',
                            action = 'store_true',
                            help = 'Abort the conversion if the HTTP status code of the main URL is greater than or equal to 400 (client/server errors). Use this in automated workflows to catch broken URLs or authentication failures early rather than producing invalid PDFs. Ensures your system does not silently generate error page PDFs when source content is unavailable.')
        parser.add_argument('-fail-on-any-url-error',
                            action = 'store_true',
                            help = 'Abort the conversion if any sub-request (images, stylesheets, scripts) fails with HTTP 400+ errors. Use this for strict quality control when all assets must load successfully.')
        parser.add_argument('-no-xpdfcrowd-header',
                            action = 'store_true',
                            help = 'Do not send the X-Pdfcrowd HTTP header in HTTP requests made by the converter. Use this if your target server blocks or logs requests with this header, or for privacy when you do not want sites to know you are using PDFCrowd. Some security systems may block requests with non-standard headers.')
        parser.add_argument('-css-page-rule-mode',
                            help = 'Specifies behavior in the presence of CSS @page rules to control which settings take precedence. Use "default" to prioritize API settings over CSS rules, ensuring consistent output regardless of input HTML. Use "mode2" to respect CSS @page rules for print-optimized HTML. This solves conflicts when CSS tries to override your API page setup. The page rule mode. Allowed values are default, mode1, mode2. Default is default.')
        parser.add_argument('-custom-css',
                            help = 'Apply custom CSS to the input HTML document to modify the visual appearance and layout of your content dynamically. Use this to override default styles, adjust spacing, change fonts, or fix layout issues without modifying the source HTML. Use !important in your CSS rules to prioritize and override conflicting styles. A string containing valid CSS. The string must not be empty.')
        parser.add_argument('-custom-javascript',
                            help = 'Run a custom JavaScript after the document is loaded and ready to print. Use this to modify page content before conversion, remove unwanted elements, or trigger specific page states. The script is intended for post-load DOM manipulation (add/remove elements, update CSS, ...). In addition to the standard browser APIs, the custom JavaScript code can use helper functions from our JavaScript library. A string containing a JavaScript code. The string must not be empty.')
        parser.add_argument('-on-load-javascript',
                            help = 'Run a custom JavaScript right after the document is loaded. The script is intended for early DOM manipulation (add/remove elements, update CSS, ...). In addition to the standard browser APIs, the custom JavaScript code can use helper functions from our JavaScript library. A string containing a JavaScript code. The string must not be empty.')
        parser.add_argument('-custom-http-header',
                            help = 'Set a custom HTTP header to be included in all requests made by the converter. Use this to pass authentication tokens to protected sites, add tracking headers for analytics, or provide API keys for accessing private content. Essential when converting content from APIs or internal systems that require special headers for access control. A string containing the header name and value separated by a colon.')
        parser.add_argument('-javascript-delay',
                            help = 'Wait the specified number of milliseconds to finish all JavaScript after the document is loaded. Use this to ensure lazy-loaded images, AJAX content, or animations complete before conversion. Your license defines the maximum wait time by "Max Delay" parameter. The number of milliseconds to wait. Must be a positive integer or 0. Default is 200.')
        parser.add_argument('-element-to-convert',
                            help = 'Convert only the specified element from the main document and its children. Use this to extract specific portions of a page (like article content) while excluding navigation, headers, footers, or sidebars. The element is specified by one or more CSS selectors. If the element is not found, the conversion fails. If multiple elements are found, the first one is used. One or more CSS selectors separated by commas. The string must not be empty.')
        parser.add_argument('-element-to-convert-mode',
                            help = 'Control how CSS styles are applied when converting only part of a page. The "cut-out" option extracts the element into a new document root, which may break CSS selectors like "body > div". The "remove-siblings" option keeps the element in its original DOM position but deletes other elements, preserving descendant selectors. The "hide-siblings" option keeps all elements but hides non-selected ones with display:none, preserving all CSS context. Allowed values are cut-out, remove-siblings, hide-siblings. Default is cut-out.')
        parser.add_argument('-wait-for-element',
                            help = 'Wait for the specified element in a source document. Use this when specific dynamic content must be ready before conversion, avoiding unnecessary delays from a fixed JavaScript delay. The element is specified by one or more CSS selectors. The element is searched for in the main document and all iframes. If the element is not found, the conversion fails. Your license defines the maximum wait time by the "Max Delay" parameter. One or more CSS selectors separated by commas. The string must not be empty.')
        parser.add_argument('-auto-detect-element-to-convert',
                            action = 'store_true',
                            help = 'The main HTML element for conversion is detected automatically. Use this when you want to extract article or main content without knowing the exact CSS selector, automatically excluding navigation and sidebars.')
        parser.add_argument('-readability-enhancements',
                            help = 'Automatically enhance the input HTML to improve readability by removing clutter and reformatting content. Use this when converting web pages with excessive navigation, ads, or sidebars that distract from the main content. Different versions (v1-v4) use progressively aggressive algorithms - start with "v1" and increase if more cleanup is needed. Ideal for converting blog posts, articles, or documentation into clean PDFs. Allowed values are none, readability-v1, readability-v2, readability-v3, readability-v4. Default is none.')
        parser.add_argument('-viewport-width',
                            help = 'Set the viewport width in pixels. The accepted range is 96-65000.')
        parser.add_argument('-viewport-height',
                            help = 'Set the viewport height in pixels. Must be a positive integer.')
        multi_args['viewport'] = 2
        parser.add_argument('-viewport',
                            help = 'Set the viewport size. Use to control responsive design rendering. Deprecated - use content_viewport_width and content_viewport_height instead. VIEWPORT must contain 2 values separated by a semicolon. Set the viewport width in pixels. The accepted range is 96-65000. Set the viewport height in pixels. Must be a positive integer.')
        parser.add_argument('-rendering-mode',
                            help = 'Set the rendering mode of the page, allowing control over how content is displayed. The rendering mode. Allowed values are default, viewport.')
        parser.add_argument('-smart-scaling-mode',
                            help = 'Specify the scaling mode used for fitting the HTML contents to the print area. The smart scaling mode. Allowed values are default, disabled, viewport-fit, content-fit, single-page-fit, single-page-fit-ex, mode1.')
        parser.add_argument('-scale-factor',
                            help = 'Set the scaling factor (zoom) for the main page area to fit content better. Use values below 100%% to shrink oversized content that is getting cut off at page edges. Use values above 100%% to enlarge small content for better readability. Common use cases include shrinking wide tables to fit (70-80%%), or enlarging mobile-optimized layouts for desktop PDFs (120-150%%). The percentage value. The accepted range is 10-500. Default is 100.')
        parser.add_argument('-jpeg-quality',
                            help = 'Set the quality of embedded JPEG images to balance file size and visual quality. Use 100%% for archival documents or when image quality is critical. Use 70-85%% for web distribution to significantly reduce file size with minimal visible quality loss. Use lower values (50-60%%) only when file size is more important than image clarity. Common artifacts below 60%% include blockiness and color banding. The percentage value. The accepted range is 1-100. Default is 100.')
        parser.add_argument('-convert-images-to-jpeg',
                            help = 'Specify which image types will be converted to JPEG to reduce PDF file size. Use "opaque" to convert only non-transparent images (safe for most documents). Use "all" to convert everything including transparent images (transparent areas become white). Use "none" to preserve original image formats. Ideal for reducing file size when distributing large image-heavy PDFs via email or web. The image category. Allowed values are none, opaque, all. Default is none.')
        parser.add_argument('-image-dpi',
                            help = 'Set the DPI of images in PDF to control resolution and file size. Use 300 DPI for professional printing, 150 DPI for everyday documents, 96 DPI for screen-only viewing, or 72 DPI for web distribution. Lower DPI creates smaller files but reduces image quality. Use 0 to preserve original image resolution. Note that this only downscales - it will not upscale low-resolution images. The DPI value. Must be a positive integer or 0.')
        parser.add_argument('-enable-pdf-forms',
                            action = 'store_true',
                            help = 'Convert HTML forms to fillable PDF forms that users can complete in PDF readers. Use this to create interactive PDFs from HTML forms. Ideal for creating fillable applications, surveys, or order forms that work offline. Details can be found in the blog post.')
        parser.add_argument('-linearize',
                            action = 'store_true',
                            help = 'Create linearized PDF. This is also known as Fast Web View. Use this to optimize PDFs for progressive download, allowing users to start viewing the first page while the rest downloads.')
        parser.add_argument('-encrypt',
                            action = 'store_true',
                            help = 'Encrypt the PDF to prevent search engines from indexing the contents and add an extra layer of security. Use this for confidential documents, internal reports, or any content you do not want appearing in search results. Combine with a password to require authentication for viewing, or just use encryption alone to prevent indexing while keeping the PDF publicly readable.')
        parser.add_argument('-user-password',
                            help = 'Protect the PDF with a user password to restrict who can open and view the document. Recipients must enter this password to view the PDF. Use this for confidential documents, sensitive data, or content distribution where you want to control access. Combine with permission flags to restrict what users can do after opening. The user password.')
        parser.add_argument('-owner-password',
                            help = 'Protect the PDF with an owner password for administrative control. This password allows changing permissions, passwords, and document restrictions - like a master key. Use different user and owner passwords to give recipients restricted access while retaining full control. The owner password should be kept confidential and different from the user password. The owner password.')
        parser.add_argument('-no-print',
                            action = 'store_true',
                            help = 'Disallow printing of the output PDF to protect sensitive content. Use this for confidential documents, copyrighted materials, or preview versions you want to restrict.')
        parser.add_argument('-no-modify',
                            action = 'store_true',
                            help = 'Disallow modification of the output PDF to maintain document integrity. Use this for official documents, contracts, or records that should not be altered after creation. Prevents recipients from editing content, adding annotations, or extracting pages.')
        parser.add_argument('-no-copy',
                            action = 'store_true',
                            help = 'Disallow text and graphics extraction from the output PDF to protect copyrighted content. Use this for ebooks, proprietary documents, or materials where you want to prevent easy copying and redistribution.')
        parser.add_argument('-title',
                            help = 'Set the title of the PDF that appears in PDF reader title bars and document properties. Use descriptive titles for better organization and searchability in document management systems. This metadata helps users identify documents when multiple PDFs are open and improves accessibility for screen readers. The title.')
        parser.add_argument('-subject',
                            help = 'Set the subject of the PDF to categorize or summarize the document content. Use this to add searchable metadata for document management systems, improve organization in large PDF libraries, or provide context about the document\'s purpose. Appears in PDF properties dialog. The subject.')
        parser.add_argument('-author',
                            help = 'Set the author of the PDF for attribution and document tracking. Use this to identify who created the document, important for official documents, reports, or publications. This metadata appears in PDF properties and helps with document management and version control. The author.')
        parser.add_argument('-keywords',
                            help = 'Associate keywords with the document to improve searchability in document management systems. Use relevant terms that describe the content, making it easier to find documents later. Separate multiple keywords with commas. Particularly useful for large document repositories or DAM systems. The string with the keywords.')
        parser.add_argument('-extract-meta-tags',
                            action = 'store_true',
                            help = 'Extract meta tags (author, keywords and description) from the input HTML and automatically populate PDF metadata. Use this when converting web pages that already have proper HTML meta tags, saving you from manually setting title, author, and keywords. Ideal for automated conversion workflows where source HTML is well-structured.')
        parser.add_argument('-page-layout',
                            help = 'Control how pages appear when the PDF opens in viewers that respect these preferences. "single-page" for focused reading one page at a time. "one-column" for continuous scrolling like a web page. "two-column-left" for book-like layouts with odd pages on left (international standard). "two-column-right" for magazines with odd pages on right. Allowed values are single-page, one-column, two-column-left, two-column-right.')
        parser.add_argument('-page-mode',
                            help = 'Control the initial display mode when the PDF opens. "full-screen" for presentations and kiosk displays where you want an immersive experience. "thumbnails" for long documents where visual page navigation is helpful. "outlines" for structured documents with bookmarks/table of contents. Allowed values are full-screen, thumbnails, outlines.')
        parser.add_argument('-initial-zoom-type',
                            help = 'Control how the PDF is initially zoomed when opened. Allowed values are fit-width, fit-height, fit-page.')
        parser.add_argument('-initial-page',
                            help = 'Display the specified page when the document is opened. Must be a positive integer.')
        parser.add_argument('-initial-zoom',
                            help = 'Specify the initial page zoom in percents when the document is opened. Must be a positive integer.')
        parser.add_argument('-hide-toolbar',
                            action = 'store_true',
                            help = 'Hide the viewer\'s toolbar when the PDF is opened to provide a cleaner, more focused reading experience. Use this for presentations, kiosk displays, or immersive reading where you want minimal UI distractions.')
        parser.add_argument('-hide-menubar',
                            action = 'store_true',
                            help = 'Hide the viewer\'s menu bar when the PDF is opened for a cleaner interface. Use this for kiosk mode, presentations, or embedded PDFs where you want to minimize UI elements.')
        parser.add_argument('-hide-window-ui',
                            action = 'store_true',
                            help = 'Hide user interface elements like scroll bars and navigation controls when the PDF opens. Use this for presentation mode, digital signage, or embedded PDFs where you want the most minimal interface possible. Combines with other UI hiding options for full-screen immersive viewing.')
        parser.add_argument('-fit-window',
                            action = 'store_true',
                            help = 'Resize the PDF viewer window to fit the size of the first displayed page when opened. Use this to ensure the PDF opens at an appropriate size rather than filling the entire screen. Particularly useful for small documents, forms, or certificates that look better at actual size.')
        parser.add_argument('-center-window',
                            action = 'store_true',
                            help = 'Position the PDF viewer window in the center of the screen when opened. Use this with window resizing to create a professional, centered display for forms, certificates, or small documents. Improves the initial viewing experience by avoiding corner-positioned windows.')
        parser.add_argument('-display-title',
                            action = 'store_true',
                            help = 'Display the title of the HTML document in the PDF viewer\'s title bar instead of the filename. Use this to show more descriptive titles when PDFs are opened - particularly useful when the filename is cryptic or auto-generated. Improves user experience by showing meaningful document names.')
        parser.add_argument('-right-to-left',
                            action = 'store_true',
                            help = 'Set the predominant reading order for text to right-to-left. This option has no direct effect on the document\'s contents or page numbering but can be used to determine the relative positioning of pages when displayed side by side or printed n-up.')
        parser.add_argument('-data-string',
                            help = 'Set the input data for template rendering. The data format can be JSON, XML, YAML or CSV. The input data string.')
        parser.add_argument('-data-file',
                            help = 'Load the input data for template rendering from the specified file. The data format can be JSON, XML, YAML or CSV. The file path to a local file containing the input data.')
        parser.add_argument('-data-format',
                            help = 'Specify the input data format. Use "auto" for automatic detection or explicitly set to JSON, XML, YAML, or CSV when format is known. The data format. Allowed values are auto, json, xml, yaml, csv. Default is auto.')
        parser.add_argument('-data-encoding',
                            help = 'Set the encoding of the data file set by setDataFile. The data file encoding. Default is utf-8.')
        parser.add_argument('-data-ignore-undefined',
                            action = 'store_true',
                            help = 'Ignore undefined variables in the HTML template. The default mode is strict so any undefined variable causes the conversion to fail. You can use {%% if variable is defined %%} to check if the variable is defined.')
        parser.add_argument('-data-auto-escape',
                            action = 'store_true',
                            help = 'Auto escape HTML symbols in the input data before placing them into the output.')
        parser.add_argument('-data-trim-blocks',
                            action = 'store_true',
                            help = 'Auto trim whitespace around each template command block.')
        parser.add_argument('-data-options',
                            help = 'Set the advanced data options:csv_delimiter - The CSV data delimiter, the default is ,.xml_remove_root - Remove the root XML element from the input data.data_root - The name of the root element inserted into the input data without a root node (e.g. CSV), the default is data. Comma separated list of options.')
        parser.add_argument('-debug-log',
                            action = 'store_true',
                            help = 'Turn on debug logging to troubleshoot conversion issues. Details about the conversion process, including resource loading, rendering steps, and error messages are stored in the debug log. Use this when conversions fail or produce unexpected results.')
        parser.add_argument('-tag',
                            help = 'Tag the conversion with a custom value for tracking and analytics. Use this to categorize conversions by customer ID, document type, or business unit. The tag appears in conversion statistics. A value longer than 32 characters is cut off. A string with the custom tag.')
        parser.add_argument('-http-proxy',
                            help = 'A proxy server used by the conversion process for accessing the source URLs with HTTP scheme. This can help circumvent regional restrictions or provide limited access to your intranet. The value must have format DOMAIN_OR_IP_ADDRESS:PORT.')
        parser.add_argument('-https-proxy',
                            help = 'A proxy server used by the conversion process for accessing the source URLs with HTTPS scheme. This can help circumvent regional restrictions or provide limited access to your intranet. The value must have format DOMAIN_OR_IP_ADDRESS:PORT.')
        parser.add_argument('-client-certificate',
                            help = 'A client certificate to authenticate the converter on your web server. The certificate is used for two-way SSL/TLS authentication (mutual TLS) and adds extra security. Use this when converting content from servers that require client certificate authentication for access. The file must be in PKCS12 format. The file must exist and not be empty.')
        parser.add_argument('-client-certificate-password',
                            help = 'A password for the PKCS12 file with a client certificate if the certificate file is password-protected.')
        parser.add_argument('-layout-dpi',
                            help = 'Set the internal DPI resolution used for positioning of PDF contents. It can help in situations where there are small inaccuracies in the PDF. It is recommended to use values that are a multiple of 72, such as 288 or 360. The DPI value. The accepted range is 72-600. Default is 300.')
        parser.add_argument('-content-area-x',
                            help = 'Set the top left X coordinate of the content area. It is relative to the top left X coordinate of the print area. The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'. It may contain a negative value. Default is 0in.')
        parser.add_argument('-content-area-y',
                            help = 'Set the top left Y coordinate of the content area. It is relative to the top left Y coordinate of the print area. The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'. It may contain a negative value. Default is 0in.')
        parser.add_argument('-content-area-width',
                            help = 'Set the width of the content area. It should be at least 1 inch. The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'. Default is The width of the print area..')
        parser.add_argument('-content-area-height',
                            help = 'Set the height of the content area. It should be at least 1 inch. The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'. Default is The height of the print area..')
        multi_args['content_area'] = 4
        parser.add_argument('-content-area',
                            help = 'Set the content area position and size. The content area enables you to specify a web page area to be converted. CONTENT_AREA must contain 4 values separated by a semicolon. Set the top left X coordinate of the content area. It is relative to the top left X coordinate of the print area. The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'. It may contain a negative value. Set the top left Y coordinate of the content area. It is relative to the top left Y coordinate of the print area. The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'. It may contain a negative value. Set the width of the content area. It should be at least 1 inch. The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'. Set the height of the content area. It should be at least 1 inch. The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'.')
        parser.add_argument('-contents-matrix',
                            help = 'A 2D transformation matrix applied to the main contents on each page. The origin [0,0] is located at the top-left corner of the contents. The resolution is 72 dpi. A comma separated string of matrix elements: "scaleX,skewX,transX,skewY,scaleY,transY" Default is 1,0,0,0,1,0.')
        parser.add_argument('-header-matrix',
                            help = 'A 2D transformation matrix applied to the page header contents. The origin [0,0] is located at the top-left corner of the header. The resolution is 72 dpi. A comma separated string of matrix elements: "scaleX,skewX,transX,skewY,scaleY,transY" Default is 1,0,0,0,1,0.')
        parser.add_argument('-footer-matrix',
                            help = 'A 2D transformation matrix applied to the page footer contents. The origin [0,0] is located at the top-left corner of the footer. The resolution is 72 dpi. A comma separated string of matrix elements: "scaleX,skewX,transX,skewY,scaleY,transY" Default is 1,0,0,0,1,0.')
        parser.add_argument('-disable-page-height-optimization',
                            action = 'store_true',
                            help = 'Disable automatic height adjustment that compensates for pixel to point rounding errors.')
        parser.add_argument('-main-document-css-annotation',
                            action = 'store_true',
                            help = 'Add special CSS classes to the main document\'s body element. This allows applying custom styling based on these classes: pdfcrowd-page-X - where X is the current page number pdfcrowd-page-odd - odd page pdfcrowd-page-even - even page Warning: If your custom styling affects the contents area size (e.g. by using different margins, padding, border width), the resulting PDF may contain duplicit contents or some contents may be missing.')
        parser.add_argument('-header-footer-css-annotation',
                            action = 'store_true',
                            help = 'Add special CSS classes to the header/footer\'s body element. This allows applying custom styling based on these classes: pdfcrowd-page-X - where X is the current page number pdfcrowd-page-count-X - where X is the total page count pdfcrowd-page-first - the first page pdfcrowd-page-last - the last page pdfcrowd-page-odd - odd page pdfcrowd-page-even - even page')
        parser.add_argument('-max-loading-time',
                            help = 'Set the maximum time for loading the page and its resources. After this time, all requests will be considered successful. This can be useful to ensure that the conversion does not timeout. Use this method if there is no other way to fix page loading. The number of seconds to wait. The accepted range is 10-30.')
        parser.add_argument('-conversion-config',
                            help = 'Configure conversion via JSON. The configuration defines various page settings for individual PDF pages or ranges of pages. It provides flexibility in designing each page of the PDF, giving control over each page\'s size, header, footer, etc. If a page or parameter is not explicitly specified, the system will use the default settings for that page or attribute. If a JSON configuration is provided, the settings in the JSON will take precedence over the global options. The structure of the JSON must be: pageSetup: An array of objects where each object defines the configuration for a specific page or range of pages. The following properties can be set for each page object: pages: A comma-separated list of page numbers or ranges. Special strings may be used, such as odd, even, and last. For example: 1-: from page 1 to the end of the document 2: only the 2nd page 2,4,6: pages 2, 4, and 6 2-5: pages 2 through 5 odd,2: the 2nd page and all odd pages pageSize: The page size (optional). Possible values: A0, A1, A2, A3, A4, A5, A6, Letter. pageWidth: The width of the page (optional). pageHeight: The height of the page (optional). marginLeft: Left margin (optional). marginRight: Right margin (optional). marginTop: Top margin (optional). marginBottom: Bottom margin (optional). displayHeader: Header appearance (optional). Possible values: none: completely excluded space: only the content is excluded, the space is used content: the content is printed (default) displayFooter: Footer appearance (optional). Possible values: none: completely excluded space: only the content is excluded, the space is used content: the content is printed (default) headerHeight: Height of the header (optional). footerHeight: Height of the footer (optional). orientation: Page orientation, such as "portrait" or "landscape" (optional). backgroundColor: Page background color in RRGGBB or RRGGBBAA hexadecimal format (optional). Dimensions may be empty, 0 or specified in inches "in", millimeters "mm", centimeters "cm", pixels "px", or points "pt". The JSON string.')
        parser.add_argument('-conversion-config-file',
                            help = 'Configure the conversion process via JSON file. See details of the JSON string. The file path to a local file. The file must exist and not be empty.')
        parser.add_argument('-subprocess-referrer',
                            help = argparse.SUPPRESS
)
        parser.add_argument('-converter-user-agent',
                            help = 'Specify the User-Agent HTTP header that will be used by the converter when a request is made to the converted web page. The user agent. Default is latest-chrome-desktop.')
        parser.add_argument('-converter-version',
                            help = 'Set the converter version. Different versions may produce different output. Choose which one provides the best output for your case. The version identifier. Allowed values are 24.04, 20.10, 18.10, latest. Default is 24.04.')
        parser.add_argument('-use-http',
                            action = 'store_true',
                            help = 'Specify whether to use HTTP or HTTPS when connecting to the PDFCrowd API. Warning: Using HTTP is insecure as data sent over HTTP is not encrypted. Enable this option only if you know what you are doing.')
        parser.add_argument('-client-user-agent',
                            help = 'Specify the User-Agent HTTP header that the client library will use when interacting with the API. The user agent string.')
        parser.add_argument('-user-agent',
                            help = 'Set a custom user agent HTTP header. It can be useful if you are behind a proxy or a firewall. The user agent string.')
        multi_args['proxy'] = 4
        parser.add_argument('-proxy',
                            help = 'Specify an HTTP proxy that the API client library will use to connect to the internet. PROXY must contain 4 values separated by a semicolon. The proxy hostname. The proxy port. The username. The password.')
        parser.add_argument('-retry-count',
                            help = 'Specify the number of automatic retries when a 502 or 503 HTTP status code is received. The status code indicates a temporary network issue. This feature can be disabled by setting to 0. Number of retries. Default is 1.')

    if converter == 'html2image':
        converter_name = 'HtmlToImageClient'

        parser = argparse.ArgumentParser(usage = usage,
                                         description = 'Conversion from HTML to image.',
                                         add_help = False,
                                         epilog = epilog)

        add_generic_args(parser)

        parser.add_argument('-output-format',
                            help = 'The output file format. Allowed values are png, jpg, gif, tiff, bmp, ico, ppm, pgm, pbm, pnm, psb, pct, ras, tga, sgi, sun, webp. Default is png.')
        parser.add_argument('-zip-main-filename',
                            help = 'Set the file name of the main HTML document stored in the input archive. Use this when your ZIP/TAR archive contains multiple HTML files and you need to specify which one to convert. If not specified, the first HTML file found in the archive is automatically used for conversion. The file name.')
        parser.add_argument('-screenshot-width',
                            help = 'Set the output image width in pixels. The accepted range is 96-65000. Default is 1024.')
        parser.add_argument('-screenshot-height',
                            help = 'Set the output image height in pixels. If it is not specified, actual document height is used. Must be a positive integer.')
        parser.add_argument('-scale-factor',
                            help = 'Set the scaling factor (zoom) for the output image. The percentage value. Must be a positive integer. Default is 100.')
        parser.add_argument('-background-color',
                            help = 'The output image background color in RGB or RGBA hex format. Use transparent (00000000) for PNG overlays or solid colors for web display. The value must be in RRGGBB or RRGGBBAA hexadecimal format.')
        parser.add_argument('-use-print-media',
                            action = 'store_true',
                            help = 'Use the print version of the page if available via @media print CSS rules. Enable this when converting websites that have print-optimized styles. Many sites hide navigation, ads, and sidebars in print mode. Produces cleaner PDFs by using the design the website creator intended for printing.')
        parser.add_argument('-no-background',
                            action = 'store_true',
                            help = 'Do not print the background graphics to create printer-friendly PDFs. Use this when documents will be physically printed to save ink costs and improve readability. Removes background colors, images, and patterns while preserving text and foreground content. Particularly useful for documents with dark backgrounds or decorative elements.')
        parser.add_argument('-disable-javascript',
                            action = 'store_true',
                            help = 'Do not execute JavaScript during conversion. Use this to improve conversion speed when JavaScript is not needed, prevent dynamic content changes, or avoid security risks from untrusted scripts. Note that disabling JavaScript means lazy-loaded images and AJAX content will not load.')
        parser.add_argument('-disable-image-loading',
                            action = 'store_true',
                            help = 'Do not load images during conversion to create text-only PDFs. Use this to significantly speed up conversion, reduce file size, or create accessible text-focused documents. Ideal for converting documentation where images are not needed, reducing bandwidth usage, or creating lightweight PDFs for email distribution.')
        parser.add_argument('-disable-remote-fonts',
                            action = 'store_true',
                            help = 'Disable loading fonts from remote sources. Use this to speed up conversion by avoiding font download delays, ensure consistent rendering with system fonts, or work around font loading failures. Note that text will fall back to system fonts, which may change the document\'s appearance.')
        parser.add_argument('-use-mobile-user-agent',
                            action = 'store_true',
                            help = 'Use a mobile user agent when making requests to the source URL.')
        parser.add_argument('-load-iframes',
                            help = 'Specifies how iframes are handled during conversion. Use "all" to include all embedded content (videos, maps, widgets). Use "same-origin" to include only content from the same domain for security purposes. Use "none" to exclude all iframes for faster conversion and to avoid third-party content issues. Disabling iframes can significantly improve performance and reliability. Allowed values are all, same-origin, none. Default is all.')
        parser.add_argument('-block-ads',
                            action = 'store_true',
                            help = 'Automatically block common advertising networks and tracking scripts during conversion, producing cleaner PDFs with faster conversion times. Filters out third-party ad content, analytics beacons, and ad network resources. Ideal for converting news sites, blogs, or any ad-heavy content where ads distract from the main message. May occasionally block legitimate third-party content - disable if critical third-party resources are missing.')
        parser.add_argument('-default-encoding',
                            help = 'Specify the character encoding when the HTML lacks proper charset declaration or has incorrect encoding. Prevents garbled text for non-English content, especially legacy pages without UTF-8 encoding. Set to "utf-8" for modern content, "iso-8859-1" for Western European legacy pages, or other encodings for specific regional content. Only needed when auto-detection fails and you see corrupted characters in the output. The text encoding of the HTML content. Default is auto detect.')
        parser.add_argument('-locale',
                            help = 'Set the locale for the conversion to control regional formatting of dates, times, and numbers. Use this when converting content for specific regions - for example, set to "en-US" for MM/DD/YYYY dates and comma thousand separators, or "de-DE" for DD.MM.YYYY dates and period thousand separators. Essential for financial reports, invoices, or localized content. The locale code according to ISO 639. Default is en-US.')
        parser.add_argument('-http-auth-user-name',
                            help = argparse.SUPPRESS
)
        parser.add_argument('-http-auth-password',
                            help = argparse.SUPPRESS
)
        multi_args['http_auth'] = 2
        parser.add_argument('-http-auth',
                            help = 'Set credentials to access HTTP basic authentication protected websites. Use this when converting content behind HTTP authentication, such as development servers, staging environments, or password-protected documentation. Provide both username and password to authenticate requests. Essential for converting internal resources or protected content. HTTP_AUTH must contain 2 values separated by a semicolon. Set the HTTP authentication user name. Required to access protected web pages or staging environments. Set the HTTP authentication password. Required to access protected web pages or staging environments.')
        parser.add_argument('-cookies',
                            help = 'Set HTTP cookies to be included in all requests made by the converter to access authenticated or session-based content. Use this when converting pages that require login, maintain user sessions, or personalize content based on cookies. Essential for converting member-only areas, dashboards, or any content behind cookie-based authentication. Format as semicolon-separated name=value pairs. The cookie string.')
        parser.add_argument('-verify-ssl-certificates',
                            action = 'store_true',
                            help = 'Enforce SSL certificate validation for secure connections, preventing conversions from sites with invalid certificates. Enable when converting from production sites with valid certificates to ensure security. When disabled, allows conversion from any HTTPS site regardless of certificate validity - including development servers with self-signed certificates, internal corporate sites with expired certificates, or local testing environments.')
        parser.add_argument('-fail-on-main-url-error',
                            action = 'store_true',
                            help = 'Abort the conversion if the HTTP status code of the main URL is greater than or equal to 400 (client/server errors). Use this in automated workflows to catch broken URLs or authentication failures early rather than producing invalid PDFs. Ensures your system does not silently generate error page PDFs when source content is unavailable.')
        parser.add_argument('-fail-on-any-url-error',
                            action = 'store_true',
                            help = 'Abort the conversion if any sub-request (images, stylesheets, scripts) fails with HTTP 400+ errors. Use this for strict quality control when all assets must load successfully.')
        parser.add_argument('-no-xpdfcrowd-header',
                            action = 'store_true',
                            help = 'Do not send the X-Pdfcrowd HTTP header in HTTP requests made by the converter. Use this if your target server blocks or logs requests with this header, or for privacy when you do not want sites to know you are using PDFCrowd. Some security systems may block requests with non-standard headers.')
        parser.add_argument('-custom-css',
                            help = 'Apply custom CSS to the input HTML document to modify the visual appearance and layout of your content dynamically. Use this to override default styles, adjust spacing, change fonts, or fix layout issues without modifying the source HTML. Use !important in your CSS rules to prioritize and override conflicting styles. A string containing valid CSS. The string must not be empty.')
        parser.add_argument('-custom-javascript',
                            help = 'Run a custom JavaScript after the document is loaded and ready to print. Use this to modify page content before conversion, remove unwanted elements, or trigger specific page states. The script is intended for post-load DOM manipulation (add/remove elements, update CSS, ...). In addition to the standard browser APIs, the custom JavaScript code can use helper functions from our JavaScript library. A string containing a JavaScript code. The string must not be empty.')
        parser.add_argument('-on-load-javascript',
                            help = 'Run a custom JavaScript right after the document is loaded. The script is intended for early DOM manipulation (add/remove elements, update CSS, ...). In addition to the standard browser APIs, the custom JavaScript code can use helper functions from our JavaScript library. A string containing a JavaScript code. The string must not be empty.')
        parser.add_argument('-custom-http-header',
                            help = 'Set a custom HTTP header to be included in all requests made by the converter. Use this to pass authentication tokens to protected sites, add tracking headers for analytics, or provide API keys for accessing private content. Essential when converting content from APIs or internal systems that require special headers for access control. A string containing the header name and value separated by a colon.')
        parser.add_argument('-javascript-delay',
                            help = 'Wait the specified number of milliseconds to finish all JavaScript after the document is loaded. Use this to ensure lazy-loaded images, AJAX content, or animations complete before conversion. Your license defines the maximum wait time by "Max Delay" parameter. The number of milliseconds to wait. Must be a positive integer or 0. Default is 200.')
        parser.add_argument('-element-to-convert',
                            help = 'Convert only the specified element from the main document and its children. Use this to extract specific portions of a page (like article content) while excluding navigation, headers, footers, or sidebars. The element is specified by one or more CSS selectors. If the element is not found, the conversion fails. If multiple elements are found, the first one is used. One or more CSS selectors separated by commas. The string must not be empty.')
        parser.add_argument('-element-to-convert-mode',
                            help = 'Control how CSS styles are applied when converting only part of a page. The "cut-out" option extracts the element into a new document root, which may break CSS selectors like "body > div". The "remove-siblings" option keeps the element in its original DOM position but deletes other elements, preserving descendant selectors. The "hide-siblings" option keeps all elements but hides non-selected ones with display:none, preserving all CSS context. Allowed values are cut-out, remove-siblings, hide-siblings. Default is cut-out.')
        parser.add_argument('-wait-for-element',
                            help = 'Wait for the specified element in a source document. Use this when specific dynamic content must be ready before conversion, avoiding unnecessary delays from a fixed JavaScript delay. The element is specified by one or more CSS selectors. The element is searched for in the main document and all iframes. If the element is not found, the conversion fails. Your license defines the maximum wait time by the "Max Delay" parameter. One or more CSS selectors separated by commas. The string must not be empty.')
        parser.add_argument('-auto-detect-element-to-convert',
                            action = 'store_true',
                            help = 'The main HTML element for conversion is detected automatically. Use this when you want to extract article or main content without knowing the exact CSS selector, automatically excluding navigation and sidebars.')
        parser.add_argument('-readability-enhancements',
                            help = 'Automatically enhance the input HTML to improve readability by removing clutter and reformatting content. Use this when converting web pages with excessive navigation, ads, or sidebars that distract from the main content. Different versions (v1-v4) use progressively aggressive algorithms - start with "v1" and increase if more cleanup is needed. Ideal for converting blog posts, articles, or documentation into clean PDFs. Allowed values are none, readability-v1, readability-v2, readability-v3, readability-v4. Default is none.')
        parser.add_argument('-data-string',
                            help = 'Set the input data for template rendering. The data format can be JSON, XML, YAML or CSV. The input data string.')
        parser.add_argument('-data-file',
                            help = 'Load the input data for template rendering from the specified file. The data format can be JSON, XML, YAML or CSV. The file path to a local file containing the input data.')
        parser.add_argument('-data-format',
                            help = 'Specify the input data format. Use "auto" for automatic detection or explicitly set to JSON, XML, YAML, or CSV when format is known. The data format. Allowed values are auto, json, xml, yaml, csv. Default is auto.')
        parser.add_argument('-data-encoding',
                            help = 'Set the encoding of the data file set by setDataFile. The data file encoding. Default is utf-8.')
        parser.add_argument('-data-ignore-undefined',
                            action = 'store_true',
                            help = 'Ignore undefined variables in the HTML template. The default mode is strict so any undefined variable causes the conversion to fail. You can use {%% if variable is defined %%} to check if the variable is defined.')
        parser.add_argument('-data-auto-escape',
                            action = 'store_true',
                            help = 'Auto escape HTML symbols in the input data before placing them into the output.')
        parser.add_argument('-data-trim-blocks',
                            action = 'store_true',
                            help = 'Auto trim whitespace around each template command block.')
        parser.add_argument('-data-options',
                            help = 'Set the advanced data options:csv_delimiter - The CSV data delimiter, the default is ,.xml_remove_root - Remove the root XML element from the input data.data_root - The name of the root element inserted into the input data without a root node (e.g. CSV), the default is data. Comma separated list of options.')
        parser.add_argument('-debug-log',
                            action = 'store_true',
                            help = 'Turn on debug logging to troubleshoot conversion issues. Details about the conversion process, including resource loading, rendering steps, and error messages are stored in the debug log. Use this when conversions fail or produce unexpected results.')
        parser.add_argument('-tag',
                            help = 'Tag the conversion with a custom value for tracking and analytics. Use this to categorize conversions by customer ID, document type, or business unit. The tag appears in conversion statistics. A value longer than 32 characters is cut off. A string with the custom tag.')
        parser.add_argument('-http-proxy',
                            help = 'A proxy server used by the conversion process for accessing the source URLs with HTTP scheme. This can help circumvent regional restrictions or provide limited access to your intranet. The value must have format DOMAIN_OR_IP_ADDRESS:PORT.')
        parser.add_argument('-https-proxy',
                            help = 'A proxy server used by the conversion process for accessing the source URLs with HTTPS scheme. This can help circumvent regional restrictions or provide limited access to your intranet. The value must have format DOMAIN_OR_IP_ADDRESS:PORT.')
        parser.add_argument('-client-certificate',
                            help = 'A client certificate to authenticate the converter on your web server. The certificate is used for two-way SSL/TLS authentication (mutual TLS) and adds extra security. Use this when converting content from servers that require client certificate authentication for access. The file must be in PKCS12 format. The file must exist and not be empty.')
        parser.add_argument('-client-certificate-password',
                            help = 'A password for the PKCS12 file with a client certificate if the certificate file is password-protected.')
        parser.add_argument('-max-loading-time',
                            help = 'Set the maximum time for loading the page and its resources. After this time, all requests will be considered successful. This can be useful to ensure that the conversion does not timeout. Use this method if there is no other way to fix page loading. The number of seconds to wait. The accepted range is 10-30.')
        parser.add_argument('-subprocess-referrer',
                            help = argparse.SUPPRESS
)
        parser.add_argument('-converter-user-agent',
                            help = 'Specify the User-Agent HTTP header that will be used by the converter when a request is made to the converted web page. The user agent. Default is latest-chrome-desktop.')
        parser.add_argument('-converter-version',
                            help = 'Set the converter version. Different versions may produce different output. Choose which one provides the best output for your case. The version identifier. Allowed values are 24.04, 20.10, 18.10, latest. Default is 24.04.')
        parser.add_argument('-use-http',
                            action = 'store_true',
                            help = 'Specify whether to use HTTP or HTTPS when connecting to the PDFCrowd API. Warning: Using HTTP is insecure as data sent over HTTP is not encrypted. Enable this option only if you know what you are doing.')
        parser.add_argument('-client-user-agent',
                            help = 'Specify the User-Agent HTTP header that the client library will use when interacting with the API. The user agent string.')
        parser.add_argument('-user-agent',
                            help = 'Set a custom user agent HTTP header. It can be useful if you are behind a proxy or a firewall. The user agent string.')
        multi_args['proxy'] = 4
        parser.add_argument('-proxy',
                            help = 'Specify an HTTP proxy that the API client library will use to connect to the internet. PROXY must contain 4 values separated by a semicolon. The proxy hostname. The proxy port. The username. The password.')
        parser.add_argument('-retry-count',
                            help = 'Specify the number of automatic retries when a 502 or 503 HTTP status code is received. The status code indicates a temporary network issue. This feature can be disabled by setting to 0. Number of retries. Default is 1.')

    if converter == 'image2image':
        converter_name = 'ImageToImageClient'

        parser = argparse.ArgumentParser(usage = usage,
                                         description = 'Conversion from one image format to another image format.',
                                         add_help = False,
                                         epilog = epilog)

        add_generic_args(parser)

        parser.add_argument('-output-format',
                            help = 'The output file format. Allowed values are png, jpg, gif, tiff, bmp, ico, ppm, pgm, pbm, pnm, psb, pct, ras, tga, sgi, sun, webp. Default is png.')
        parser.add_argument('-resize',
                            help = 'Scale the image to different dimensions. Accepts percentage values for proportional scaling or explicit pixel dimensions for absolute sizing. The resize percentage or new image dimensions. Default is 100%%.')
        parser.add_argument('-rotate',
                            help = 'Rotate the image by the specified angle in degrees. Positive values rotate clockwise, negative values counterclockwise. The rotation specified in degrees.')
        parser.add_argument('-crop-area-x',
                            help = 'Set the horizontal starting position of the crop area, measured from the left edge of the print area. Positive values offset inward from the left edge, negative values extend beyond the left boundary. The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'. Default is 0px.')
        parser.add_argument('-crop-area-y',
                            help = 'Set the vertical starting position of the crop area, measured from the top edge of the print area. Positive values offset inward from the top edge, negative values extend beyond the top boundary. The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'. Default is 0px.')
        parser.add_argument('-crop-area-width',
                            help = 'Set the horizontal extent of the crop area. Defines the width of the region to be converted. Minimum value is 1 inch. The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'. Default is The width of the print area..')
        parser.add_argument('-crop-area-height',
                            help = 'Set the vertical extent of the crop area. Defines the height of the region to be converted. Minimum value is 1 inch. The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'. Default is The height of the print area..')
        multi_args['crop_area'] = 4
        parser.add_argument('-crop-area',
                            help = 'Define a rectangular region to convert by setting X/Y position and width/height simultaneously. Coordinates are relative to the print area\'s top-left corner. CROP_AREA must contain 4 values separated by a semicolon. Set the horizontal starting position of the crop area, measured from the left edge of the print area. Positive values offset inward from the left edge, negative values extend beyond the left boundary. Set the vertical starting position of the crop area, measured from the top edge of the print area. Positive values offset inward from the top edge, negative values extend beyond the top boundary. Set the horizontal extent of the crop area. Defines the width of the region to be converted. Minimum value is 1 inch. Set the vertical extent of the crop area. Defines the height of the region to be converted. Minimum value is 1 inch. All values the value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'.')
        parser.add_argument('-remove-borders',
                            action = 'store_true',
                            help = 'Detect and remove solid-color borders surrounding the image content. Only removes borders that consist of a single consistent color.')
        parser.add_argument('-canvas-size',
                            help = 'Set the output canvas size. Use standard sizes (A4, Letter, A3, etc.) for printable output with consistent dimensions. Allowed values are A0, A1, A2, A3, A4, A5, A6, Letter.')
        parser.add_argument('-canvas-width',
                            help = 'Set the output canvas width. The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'.')
        parser.add_argument('-canvas-height',
                            help = 'Set the output canvas height. The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'.')
        multi_args['canvas_dimensions'] = 2
        parser.add_argument('-canvas-dimensions',
                            help = 'Set the output canvas dimensions. If no canvas size is specified, margins are applied as a border around the image. CANVAS_DIMENSIONS must contain 2 values separated by a semicolon. Set the output canvas width. Set the output canvas height. All values the value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'.')
        parser.add_argument('-orientation',
                            help = 'Set the output canvas orientation. Use portrait for vertical content, landscape for horizontal or wide content. Allowed values are landscape, portrait. Default is portrait.')
        parser.add_argument('-position',
                            help = 'Set the image position on the canvas. Center for balanced composition, or corner/edge positions for specific layouts. Allowed values are center, top, bottom, left, right, top-left, top-right, bottom-left, bottom-right. Default is center.')
        parser.add_argument('-print-canvas-mode',
                            help = 'Set the mode to print the image on the canvas. Allowed values are default, fit, stretch. Default is default.')
        parser.add_argument('-margin-top',
                            help = 'Set the output canvas top margin. The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'.')
        parser.add_argument('-margin-right',
                            help = 'Set the output canvas right margin. The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'.')
        parser.add_argument('-margin-bottom',
                            help = 'Set the output canvas bottom margin. The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'.')
        parser.add_argument('-margin-left',
                            help = 'Set the output canvas left margin. The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'.')
        multi_args['margins'] = 4
        parser.add_argument('-margins',
                            help = 'Set the output canvas margins. Create white space around the image for framing, borders, or print bleed. MARGINS must contain 4 values separated by a semicolon. Set the output canvas top margin. Set the output canvas right margin. Set the output canvas bottom margin. Set the output canvas left margin. All values the value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'.')
        parser.add_argument('-canvas-background-color',
                            help = 'The canvas background color in RGB or RGBA hexadecimal format. The color fills the entire canvas regardless of margins. If no canvas size is specified and the image format supports background (e.g. PDF, PNG), the background color is applied too. The value must be in RRGGBB or RRGGBBAA hexadecimal format.')
        parser.add_argument('-dpi',
                            help = 'Set the DPI resolution of the input image. The DPI affects margin options specified in points too (e.g. 1 point is equal to 1 pixel in 96 DPI). The DPI value. Default is 96.')
        parser.add_argument('-debug-log',
                            action = 'store_true',
                            help = 'Turn on debug logging to troubleshoot conversion issues. Details about the conversion process, including resource loading, rendering steps, and error messages are stored in the debug log. Use this when conversions fail or produce unexpected results.')
        parser.add_argument('-tag',
                            help = 'Tag the conversion with a custom value for tracking and analytics. Use this to categorize conversions by customer ID, document type, or business unit. The tag appears in conversion statistics. A value longer than 32 characters is cut off. A string with the custom tag.')
        parser.add_argument('-http-proxy',
                            help = 'A proxy server used by the conversion process for accessing the source URLs with HTTP scheme. This can help circumvent regional restrictions or provide limited access to your intranet. The value must have format DOMAIN_OR_IP_ADDRESS:PORT.')
        parser.add_argument('-https-proxy',
                            help = 'A proxy server used by the conversion process for accessing the source URLs with HTTPS scheme. This can help circumvent regional restrictions or provide limited access to your intranet. The value must have format DOMAIN_OR_IP_ADDRESS:PORT.')
        parser.add_argument('-converter-version',
                            help = 'Set the converter version. Different versions may produce different output. Choose which one provides the best output for your case. The version identifier. Allowed values are 24.04, 20.10, 18.10, latest. Default is 24.04.')
        parser.add_argument('-use-http',
                            action = 'store_true',
                            help = 'Specify whether to use HTTP or HTTPS when connecting to the PDFCrowd API. Warning: Using HTTP is insecure as data sent over HTTP is not encrypted. Enable this option only if you know what you are doing.')
        parser.add_argument('-client-user-agent',
                            help = 'Specify the User-Agent HTTP header that the client library will use when interacting with the API. The user agent string.')
        parser.add_argument('-user-agent',
                            help = 'Set a custom user agent HTTP header. It can be useful if you are behind a proxy or a firewall. The user agent string.')
        multi_args['proxy'] = 4
        parser.add_argument('-proxy',
                            help = 'Specify an HTTP proxy that the API client library will use to connect to the internet. PROXY must contain 4 values separated by a semicolon. The proxy hostname. The proxy port. The username. The password.')
        parser.add_argument('-retry-count',
                            help = 'Specify the number of automatic retries when a 502 or 503 HTTP status code is received. The status code indicates a temporary network issue. This feature can be disabled by setting to 0. Number of retries. Default is 1.')

    if converter == 'pdf2pdf':
        converter_name = 'PdfToPdfClient'

        parser = argparse.ArgumentParser(usage = usage,
                                         description = 'Conversion from PDF to PDF.',
                                         add_help = False,
                                         epilog = epilog)

        add_generic_args(parser, '+')

        parser.add_argument('-action',
                            help = 'Specify the PDF manipulation operation to perform on input files. Allowed values are join, shuffle, extract, delete. Default is join.')
        parser.add_argument('-input-pdf-password',
                            help = 'Password for decrypting encrypted input PDFs. The input PDF password.')
        parser.add_argument('-page-range',
                            help = 'Specify which pages to target. Supports individual pages, ranges, open-ended ranges, and combinations. The keyword "last" can be used to reference the final page. A comma separated list of page numbers or ranges.')
        parser.add_argument('-page-watermark',
                            help = 'Apply the first page of a watermark PDF to every page of the output PDF. Use this to add transparent overlays like "DRAFT" stamps, security markings, or branding elements that appear on top of content. Ideal for confidential document marking or adding protective overlays. The file path to a local file. The file must exist and not be empty.')
        parser.add_argument('-page-watermark-url',
                            help = 'Load a file from the specified URL and apply the file as a watermark to each page of the output PDF. A watermark can be either a PDF or an image. If a multi-page file (PDF or TIFF) is used, the first page is used as the watermark. Supported protocols are http:// and https://.')
        parser.add_argument('-multipage-watermark',
                            help = 'Apply each page of a watermark PDF to the corresponding page of the output PDF. Use this for page-specific watermarks where different pages need different overlays - for example, different approval stamps per department. If the watermark has fewer pages than the output, the last watermark page is repeated for remaining pages. The file path to a local file. The file must exist and not be empty.')
        parser.add_argument('-multipage-watermark-url',
                            help = 'Load a file from the specified URL and apply each page of the file as a watermark to the corresponding page of the output PDF. A watermark can be either a PDF or an image. Supported protocols are http:// and https://.')
        parser.add_argument('-page-background',
                            help = 'Apply the first page of a background PDF to every page of the output PDF. Use this to add letterheads, branded templates, or decorative backgrounds that appear behind your content. Backgrounds appear beneath content, while watermarks layer on top. Perfect for adding company letterheads to reports or applying branded templates to dynamically generated content. The file path to a local file. The file must exist and not be empty.')
        parser.add_argument('-page-background-url',
                            help = 'Load a file from the specified URL and apply the file as a background to each page of the output PDF. A background can be either a PDF or an image. If a multi-page file (PDF or TIFF) is used, the first page is used as the background. Supported protocols are http:// and https://.')
        parser.add_argument('-multipage-background',
                            help = 'Apply each page of a background PDF to the corresponding page of the output PDF. Use this for page-specific backgrounds where each page needs a different template - for example, different letterheads for front and back pages. If the background has fewer pages than the output, the last background page is repeated for remaining pages. The file path to a local file. The file must exist and not be empty.')
        parser.add_argument('-multipage-background-url',
                            help = 'Load a file from the specified URL and apply each page of the file as a background to the corresponding page of the output PDF. A background can be either a PDF or an image. Supported protocols are http:// and https://.')
        parser.add_argument('-linearize',
                            action = 'store_true',
                            help = 'Create linearized PDF. This is also known as Fast Web View. Use this to optimize PDFs for progressive download, allowing users to start viewing the first page while the rest downloads.')
        parser.add_argument('-encrypt',
                            action = 'store_true',
                            help = 'Encrypt the PDF to prevent search engines from indexing the contents and add an extra layer of security. Use this for confidential documents, internal reports, or any content you do not want appearing in search results. Combine with a password to require authentication for viewing, or just use encryption alone to prevent indexing while keeping the PDF publicly readable.')
        parser.add_argument('-user-password',
                            help = 'Protect the PDF with a user password to restrict who can open and view the document. Recipients must enter this password to view the PDF. Use this for confidential documents, sensitive data, or content distribution where you want to control access. Combine with permission flags to restrict what users can do after opening. The user password.')
        parser.add_argument('-owner-password',
                            help = 'Protect the PDF with an owner password for administrative control. This password allows changing permissions, passwords, and document restrictions - like a master key. Use different user and owner passwords to give recipients restricted access while retaining full control. The owner password should be kept confidential and different from the user password. The owner password.')
        parser.add_argument('-no-print',
                            action = 'store_true',
                            help = 'Disallow printing of the output PDF to protect sensitive content. Use this for confidential documents, copyrighted materials, or preview versions you want to restrict.')
        parser.add_argument('-no-modify',
                            action = 'store_true',
                            help = 'Disallow modification of the output PDF to maintain document integrity. Use this for official documents, contracts, or records that should not be altered after creation. Prevents recipients from editing content, adding annotations, or extracting pages.')
        parser.add_argument('-no-copy',
                            action = 'store_true',
                            help = 'Disallow text and graphics extraction from the output PDF to protect copyrighted content. Use this for ebooks, proprietary documents, or materials where you want to prevent easy copying and redistribution.')
        parser.add_argument('-title',
                            help = 'Set the title of the PDF that appears in PDF reader title bars and document properties. Use descriptive titles for better organization and searchability in document management systems. This metadata helps users identify documents when multiple PDFs are open and improves accessibility for screen readers. The title.')
        parser.add_argument('-subject',
                            help = 'Set the subject of the PDF to categorize or summarize the document content. Use this to add searchable metadata for document management systems, improve organization in large PDF libraries, or provide context about the document\'s purpose. Appears in PDF properties dialog. The subject.')
        parser.add_argument('-author',
                            help = 'Set the author of the PDF for attribution and document tracking. Use this to identify who created the document, important for official documents, reports, or publications. This metadata appears in PDF properties and helps with document management and version control. The author.')
        parser.add_argument('-keywords',
                            help = 'Associate keywords with the document to improve searchability in document management systems. Use relevant terms that describe the content, making it easier to find documents later. Separate multiple keywords with commas. Particularly useful for large document repositories or DAM systems. The string with the keywords.')
        parser.add_argument('-use-metadata-from',
                            help = 'Use metadata (title, subject, author and keywords) from the n-th input PDF when merging multiple PDFs. Set to 1 to use the first PDF\'s metadata, 2 for the second, etc. Use this when combining PDFs and you want to preserve the metadata from a specific document rather than starting with blank metadata. Set to 0 for no metadata. Set the index of the input PDF file from which to use the metadata. 0 means no metadata. Must be a positive integer or 0.')
        parser.add_argument('-page-layout',
                            help = 'Control how pages appear when the PDF opens in viewers that respect these preferences. "single-page" for focused reading one page at a time. "one-column" for continuous scrolling like a web page. "two-column-left" for book-like layouts with odd pages on left (international standard). "two-column-right" for magazines with odd pages on right. Allowed values are single-page, one-column, two-column-left, two-column-right.')
        parser.add_argument('-page-mode',
                            help = 'Control the initial display mode when the PDF opens. "full-screen" for presentations and kiosk displays where you want an immersive experience. "thumbnails" for long documents where visual page navigation is helpful. "outlines" for structured documents with bookmarks/table of contents. Allowed values are full-screen, thumbnails, outlines.')
        parser.add_argument('-initial-zoom-type',
                            help = 'Control how the PDF is initially zoomed when opened. Allowed values are fit-width, fit-height, fit-page.')
        parser.add_argument('-initial-page',
                            help = 'Display the specified page when the document is opened. Must be a positive integer.')
        parser.add_argument('-initial-zoom',
                            help = 'Specify the initial page zoom in percents when the document is opened. Must be a positive integer.')
        parser.add_argument('-hide-toolbar',
                            action = 'store_true',
                            help = 'Hide the viewer\'s toolbar when the PDF is opened to provide a cleaner, more focused reading experience. Use this for presentations, kiosk displays, or immersive reading where you want minimal UI distractions.')
        parser.add_argument('-hide-menubar',
                            action = 'store_true',
                            help = 'Hide the viewer\'s menu bar when the PDF is opened for a cleaner interface. Use this for kiosk mode, presentations, or embedded PDFs where you want to minimize UI elements.')
        parser.add_argument('-hide-window-ui',
                            action = 'store_true',
                            help = 'Hide user interface elements like scroll bars and navigation controls when the PDF opens. Use this for presentation mode, digital signage, or embedded PDFs where you want the most minimal interface possible. Combines with other UI hiding options for full-screen immersive viewing.')
        parser.add_argument('-fit-window',
                            action = 'store_true',
                            help = 'Resize the PDF viewer window to fit the size of the first displayed page when opened. Use this to ensure the PDF opens at an appropriate size rather than filling the entire screen. Particularly useful for small documents, forms, or certificates that look better at actual size.')
        parser.add_argument('-center-window',
                            action = 'store_true',
                            help = 'Position the PDF viewer window in the center of the screen when opened. Use this with window resizing to create a professional, centered display for forms, certificates, or small documents. Improves the initial viewing experience by avoiding corner-positioned windows.')
        parser.add_argument('-display-title',
                            action = 'store_true',
                            help = 'Display the title of the HTML document in the PDF viewer\'s title bar instead of the filename. Use this to show more descriptive titles when PDFs are opened - particularly useful when the filename is cryptic or auto-generated. Improves user experience by showing meaningful document names.')
        parser.add_argument('-right-to-left',
                            action = 'store_true',
                            help = 'Set the predominant reading order for text to right-to-left. This option has no direct effect on the document\'s contents or page numbering but can be used to determine the relative positioning of pages when displayed side by side or printed n-up.')
        parser.add_argument('-debug-log',
                            action = 'store_true',
                            help = 'Turn on debug logging to troubleshoot conversion issues. Details about the conversion process, including resource loading, rendering steps, and error messages are stored in the debug log. Use this when conversions fail or produce unexpected results.')
        parser.add_argument('-tag',
                            help = 'Tag the conversion with a custom value for tracking and analytics. Use this to categorize conversions by customer ID, document type, or business unit. The tag appears in conversion statistics. A value longer than 32 characters is cut off. A string with the custom tag.')
        parser.add_argument('-converter-version',
                            help = 'Set the converter version. Different versions may produce different output. Choose which one provides the best output for your case. The version identifier. Allowed values are 24.04, 20.10, 18.10, latest. Default is 24.04.')
        parser.add_argument('-use-http',
                            action = 'store_true',
                            help = 'Specify whether to use HTTP or HTTPS when connecting to the PDFCrowd API. Warning: Using HTTP is insecure as data sent over HTTP is not encrypted. Enable this option only if you know what you are doing.')
        parser.add_argument('-client-user-agent',
                            help = 'Specify the User-Agent HTTP header that the client library will use when interacting with the API. The user agent string.')
        parser.add_argument('-user-agent',
                            help = 'Set a custom user agent HTTP header. It can be useful if you are behind a proxy or a firewall. The user agent string.')
        multi_args['proxy'] = 4
        parser.add_argument('-proxy',
                            help = 'Specify an HTTP proxy that the API client library will use to connect to the internet. PROXY must contain 4 values separated by a semicolon. The proxy hostname. The proxy port. The username. The password.')
        parser.add_argument('-retry-count',
                            help = 'Specify the number of automatic retries when a 502 or 503 HTTP status code is received. The status code indicates a temporary network issue. This feature can be disabled by setting to 0. Number of retries. Default is 1.')

    if converter == 'image2pdf':
        converter_name = 'ImageToPdfClient'

        parser = argparse.ArgumentParser(usage = usage,
                                         description = 'Conversion from an image to PDF.',
                                         add_help = False,
                                         epilog = epilog)

        add_generic_args(parser)

        parser.add_argument('-resize',
                            help = 'Scale the image to different dimensions. Accepts percentage values for proportional scaling or explicit pixel dimensions for absolute sizing. The resize percentage or new image dimensions. Default is 100%%.')
        parser.add_argument('-rotate',
                            help = 'Rotate the image by the specified angle in degrees. Positive values rotate clockwise, negative values counterclockwise. The rotation specified in degrees.')
        parser.add_argument('-crop-area-x',
                            help = 'Set the horizontal starting position of the crop area, measured from the left edge of the print area. Positive values offset inward from the left edge, negative values extend beyond the left boundary. The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'. Default is 0px.')
        parser.add_argument('-crop-area-y',
                            help = 'Set the vertical starting position of the crop area, measured from the top edge of the print area. Positive values offset inward from the top edge, negative values extend beyond the top boundary. The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'. Default is 0px.')
        parser.add_argument('-crop-area-width',
                            help = 'Set the horizontal extent of the crop area. Defines the width of the region to be converted. Minimum value is 1 inch. The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'. Default is The width of the print area..')
        parser.add_argument('-crop-area-height',
                            help = 'Set the vertical extent of the crop area. Defines the height of the region to be converted. Minimum value is 1 inch. The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'. Default is The height of the print area..')
        multi_args['crop_area'] = 4
        parser.add_argument('-crop-area',
                            help = 'Define a rectangular region to convert by setting X/Y position and width/height simultaneously. Coordinates are relative to the print area\'s top-left corner. CROP_AREA must contain 4 values separated by a semicolon. Set the horizontal starting position of the crop area, measured from the left edge of the print area. Positive values offset inward from the left edge, negative values extend beyond the left boundary. Set the vertical starting position of the crop area, measured from the top edge of the print area. Positive values offset inward from the top edge, negative values extend beyond the top boundary. Set the horizontal extent of the crop area. Defines the width of the region to be converted. Minimum value is 1 inch. Set the vertical extent of the crop area. Defines the height of the region to be converted. Minimum value is 1 inch. All values the value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'.')
        parser.add_argument('-remove-borders',
                            action = 'store_true',
                            help = 'Detect and remove solid-color borders surrounding the image content. Only removes borders that consist of a single consistent color.')
        parser.add_argument('-page-size',
                            help = 'Set the output page size. Use standard sizes (A4, Letter, A3, etc.) for printable output with consistent dimensions. Allowed values are A0, A1, A2, A3, A4, A5, A6, Letter.')
        parser.add_argument('-page-width',
                            help = 'Set the output page width. The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'.')
        parser.add_argument('-page-height',
                            help = 'Set the output page height. The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'.')
        multi_args['page_dimensions'] = 2
        parser.add_argument('-page-dimensions',
                            help = 'Set the output page dimensions. If no page size is specified, margins are applied as a border around the image. PAGE_DIMENSIONS must contain 2 values separated by a semicolon. Set the output page width. Set the output page height. All values the value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'.')
        parser.add_argument('-orientation',
                            help = 'Set the output page orientation. Use portrait for standard documents, landscape for wide content like tables. Allowed values are landscape, portrait. Default is portrait.')
        parser.add_argument('-position',
                            help = 'Set the image position on the page. Center for balanced layout, or corner/edge positions for specific design needs. Allowed values are center, top, bottom, left, right, top-left, top-right, bottom-left, bottom-right. Default is center.')
        parser.add_argument('-print-page-mode',
                            help = 'Set the mode to print the image on the content area of the page. Allowed values are default, fit, stretch. Default is default.')
        parser.add_argument('-margin-top',
                            help = 'Set the output page top margin. The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'.')
        parser.add_argument('-margin-right',
                            help = 'Set the output page right margin. The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'.')
        parser.add_argument('-margin-bottom',
                            help = 'Set the output page bottom margin. The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'.')
        parser.add_argument('-margin-left',
                            help = 'Set the output page left margin. The value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'.')
        multi_args['page_margins'] = 4
        parser.add_argument('-page-margins',
                            help = 'Set the output page margins. Control white space for readability, binding clearance, or print requirements. PAGE_MARGINS must contain 4 values separated by a semicolon. Set the output page top margin. Set the output page right margin. Set the output page bottom margin. Set the output page left margin. All values the value must be specified in inches \'in\', millimeters \'mm\', centimeters \'cm\', pixels \'px\', or points \'pt\'.')
        parser.add_argument('-page-background-color',
                            help = 'The page background color in RGB or RGBA hexadecimal format. The color fills the entire page regardless of the margins. If no page size is specified and the image format supports background (e.g. PDF, PNG), the background color is applied too. The value must be in RRGGBB or RRGGBBAA hexadecimal format.')
        parser.add_argument('-dpi',
                            help = 'Set the DPI resolution of the input image. The DPI affects margin options specified in points too (e.g. 1 point is equal to 1 pixel in 96 DPI). The DPI value. Default is 96.')
        parser.add_argument('-page-watermark',
                            help = 'Apply the first page of a watermark PDF to every page of the output PDF. Use this to add transparent overlays like "DRAFT" stamps, security markings, or branding elements that appear on top of content. Ideal for confidential document marking or adding protective overlays. The file path to a local file. The file must exist and not be empty.')
        parser.add_argument('-page-watermark-url',
                            help = 'Load a file from the specified URL and apply the file as a watermark to each page of the output PDF. A watermark can be either a PDF or an image. If a multi-page file (PDF or TIFF) is used, the first page is used as the watermark. Supported protocols are http:// and https://.')
        parser.add_argument('-multipage-watermark',
                            help = 'Apply each page of a watermark PDF to the corresponding page of the output PDF. Use this for page-specific watermarks where different pages need different overlays - for example, different approval stamps per department. If the watermark has fewer pages than the output, the last watermark page is repeated for remaining pages. The file path to a local file. The file must exist and not be empty.')
        parser.add_argument('-multipage-watermark-url',
                            help = 'Load a file from the specified URL and apply each page of the file as a watermark to the corresponding page of the output PDF. A watermark can be either a PDF or an image. Supported protocols are http:// and https://.')
        parser.add_argument('-page-background',
                            help = 'Apply the first page of a background PDF to every page of the output PDF. Use this to add letterheads, branded templates, or decorative backgrounds that appear behind your content. Backgrounds appear beneath content, while watermarks layer on top. Perfect for adding company letterheads to reports or applying branded templates to dynamically generated content. The file path to a local file. The file must exist and not be empty.')
        parser.add_argument('-page-background-url',
                            help = 'Load a file from the specified URL and apply the file as a background to each page of the output PDF. A background can be either a PDF or an image. If a multi-page file (PDF or TIFF) is used, the first page is used as the background. Supported protocols are http:// and https://.')
        parser.add_argument('-multipage-background',
                            help = 'Apply each page of a background PDF to the corresponding page of the output PDF. Use this for page-specific backgrounds where each page needs a different template - for example, different letterheads for front and back pages. If the background has fewer pages than the output, the last background page is repeated for remaining pages. The file path to a local file. The file must exist and not be empty.')
        parser.add_argument('-multipage-background-url',
                            help = 'Load a file from the specified URL and apply each page of the file as a background to the corresponding page of the output PDF. A background can be either a PDF or an image. Supported protocols are http:// and https://.')
        parser.add_argument('-linearize',
                            action = 'store_true',
                            help = 'Create linearized PDF. This is also known as Fast Web View. Use this to optimize PDFs for progressive download, allowing users to start viewing the first page while the rest downloads.')
        parser.add_argument('-encrypt',
                            action = 'store_true',
                            help = 'Encrypt the PDF to prevent search engines from indexing the contents and add an extra layer of security. Use this for confidential documents, internal reports, or any content you do not want appearing in search results. Combine with a password to require authentication for viewing, or just use encryption alone to prevent indexing while keeping the PDF publicly readable.')
        parser.add_argument('-user-password',
                            help = 'Protect the PDF with a user password to restrict who can open and view the document. Recipients must enter this password to view the PDF. Use this for confidential documents, sensitive data, or content distribution where you want to control access. Combine with permission flags to restrict what users can do after opening. The user password.')
        parser.add_argument('-owner-password',
                            help = 'Protect the PDF with an owner password for administrative control. This password allows changing permissions, passwords, and document restrictions - like a master key. Use different user and owner passwords to give recipients restricted access while retaining full control. The owner password should be kept confidential and different from the user password. The owner password.')
        parser.add_argument('-no-print',
                            action = 'store_true',
                            help = 'Disallow printing of the output PDF to protect sensitive content. Use this for confidential documents, copyrighted materials, or preview versions you want to restrict.')
        parser.add_argument('-no-modify',
                            action = 'store_true',
                            help = 'Disallow modification of the output PDF to maintain document integrity. Use this for official documents, contracts, or records that should not be altered after creation. Prevents recipients from editing content, adding annotations, or extracting pages.')
        parser.add_argument('-no-copy',
                            action = 'store_true',
                            help = 'Disallow text and graphics extraction from the output PDF to protect copyrighted content. Use this for ebooks, proprietary documents, or materials where you want to prevent easy copying and redistribution.')
        parser.add_argument('-title',
                            help = 'Set the title of the PDF that appears in PDF reader title bars and document properties. Use descriptive titles for better organization and searchability in document management systems. This metadata helps users identify documents when multiple PDFs are open and improves accessibility for screen readers. The title.')
        parser.add_argument('-subject',
                            help = 'Set the subject of the PDF to categorize or summarize the document content. Use this to add searchable metadata for document management systems, improve organization in large PDF libraries, or provide context about the document\'s purpose. Appears in PDF properties dialog. The subject.')
        parser.add_argument('-author',
                            help = 'Set the author of the PDF for attribution and document tracking. Use this to identify who created the document, important for official documents, reports, or publications. This metadata appears in PDF properties and helps with document management and version control. The author.')
        parser.add_argument('-keywords',
                            help = 'Associate keywords with the document to improve searchability in document management systems. Use relevant terms that describe the content, making it easier to find documents later. Separate multiple keywords with commas. Particularly useful for large document repositories or DAM systems. The string with the keywords.')
        parser.add_argument('-page-layout',
                            help = 'Control how pages appear when the PDF opens in viewers that respect these preferences. "single-page" for focused reading one page at a time. "one-column" for continuous scrolling like a web page. "two-column-left" for book-like layouts with odd pages on left (international standard). "two-column-right" for magazines with odd pages on right. Allowed values are single-page, one-column, two-column-left, two-column-right.')
        parser.add_argument('-page-mode',
                            help = 'Control the initial display mode when the PDF opens. "full-screen" for presentations and kiosk displays where you want an immersive experience. "thumbnails" for long documents where visual page navigation is helpful. "outlines" for structured documents with bookmarks/table of contents. Allowed values are full-screen, thumbnails, outlines.')
        parser.add_argument('-initial-zoom-type',
                            help = 'Control how the PDF is initially zoomed when opened. Allowed values are fit-width, fit-height, fit-page.')
        parser.add_argument('-initial-page',
                            help = 'Display the specified page when the document is opened. Must be a positive integer.')
        parser.add_argument('-initial-zoom',
                            help = 'Specify the initial page zoom in percents when the document is opened. Must be a positive integer.')
        parser.add_argument('-hide-toolbar',
                            action = 'store_true',
                            help = 'Hide the viewer\'s toolbar when the PDF is opened to provide a cleaner, more focused reading experience. Use this for presentations, kiosk displays, or immersive reading where you want minimal UI distractions.')
        parser.add_argument('-hide-menubar',
                            action = 'store_true',
                            help = 'Hide the viewer\'s menu bar when the PDF is opened for a cleaner interface. Use this for kiosk mode, presentations, or embedded PDFs where you want to minimize UI elements.')
        parser.add_argument('-hide-window-ui',
                            action = 'store_true',
                            help = 'Hide user interface elements like scroll bars and navigation controls when the PDF opens. Use this for presentation mode, digital signage, or embedded PDFs where you want the most minimal interface possible. Combines with other UI hiding options for full-screen immersive viewing.')
        parser.add_argument('-fit-window',
                            action = 'store_true',
                            help = 'Resize the PDF viewer window to fit the size of the first displayed page when opened. Use this to ensure the PDF opens at an appropriate size rather than filling the entire screen. Particularly useful for small documents, forms, or certificates that look better at actual size.')
        parser.add_argument('-center-window',
                            action = 'store_true',
                            help = 'Position the PDF viewer window in the center of the screen when opened. Use this with window resizing to create a professional, centered display for forms, certificates, or small documents. Improves the initial viewing experience by avoiding corner-positioned windows.')
        parser.add_argument('-display-title',
                            action = 'store_true',
                            help = 'Display the title of the HTML document in the PDF viewer\'s title bar instead of the filename. Use this to show more descriptive titles when PDFs are opened - particularly useful when the filename is cryptic or auto-generated. Improves user experience by showing meaningful document names.')
        parser.add_argument('-debug-log',
                            action = 'store_true',
                            help = 'Turn on debug logging to troubleshoot conversion issues. Details about the conversion process, including resource loading, rendering steps, and error messages are stored in the debug log. Use this when conversions fail or produce unexpected results.')
        parser.add_argument('-tag',
                            help = 'Tag the conversion with a custom value for tracking and analytics. Use this to categorize conversions by customer ID, document type, or business unit. The tag appears in conversion statistics. A value longer than 32 characters is cut off. A string with the custom tag.')
        parser.add_argument('-http-proxy',
                            help = 'A proxy server used by the conversion process for accessing the source URLs with HTTP scheme. This can help circumvent regional restrictions or provide limited access to your intranet. The value must have format DOMAIN_OR_IP_ADDRESS:PORT.')
        parser.add_argument('-https-proxy',
                            help = 'A proxy server used by the conversion process for accessing the source URLs with HTTPS scheme. This can help circumvent regional restrictions or provide limited access to your intranet. The value must have format DOMAIN_OR_IP_ADDRESS:PORT.')
        parser.add_argument('-converter-version',
                            help = 'Set the converter version. Different versions may produce different output. Choose which one provides the best output for your case. The version identifier. Allowed values are 24.04, 20.10, 18.10, latest. Default is 24.04.')
        parser.add_argument('-use-http',
                            action = 'store_true',
                            help = 'Specify whether to use HTTP or HTTPS when connecting to the PDFCrowd API. Warning: Using HTTP is insecure as data sent over HTTP is not encrypted. Enable this option only if you know what you are doing.')
        parser.add_argument('-client-user-agent',
                            help = 'Specify the User-Agent HTTP header that the client library will use when interacting with the API. The user agent string.')
        parser.add_argument('-user-agent',
                            help = 'Set a custom user agent HTTP header. It can be useful if you are behind a proxy or a firewall. The user agent string.')
        multi_args['proxy'] = 4
        parser.add_argument('-proxy',
                            help = 'Specify an HTTP proxy that the API client library will use to connect to the internet. PROXY must contain 4 values separated by a semicolon. The proxy hostname. The proxy port. The username. The password.')
        parser.add_argument('-retry-count',
                            help = 'Specify the number of automatic retries when a 502 or 503 HTTP status code is received. The status code indicates a temporary network issue. This feature can be disabled by setting to 0. Number of retries. Default is 1.')

    if converter == 'pdf2html':
        converter_name = 'PdfToHtmlClient'

        parser = argparse.ArgumentParser(usage = usage,
                                         description = 'Conversion from PDF to HTML.',
                                         add_help = False,
                                         epilog = epilog)

        add_generic_args(parser)

        parser.add_argument('-pdf-password',
                            help = 'Password to open the encrypted PDF file. The input PDF password.')
        parser.add_argument('-scale-factor',
                            help = 'Set the scaling factor (zoom) for the main page area. The percentage value. Must be a positive integer. Default is 100.')
        parser.add_argument('-print-page-range',
                            help = 'Set the page range to print. A comma separated list of page numbers or ranges.')
        parser.add_argument('-dpi',
                            help = 'Set the output graphics DPI. Higher values (144-300) improve quality but increase file size. Use 144 for web, 300 for print. The DPI value. Default is 144.')
        parser.add_argument('-image-mode',
                            help = 'Specify where the images are stored. Use separate files for better performance with large images or when serving images from a CDN. Use embedded for single-file portability. The image storage mode. Allowed values are embed, separate, none. Default is embed.')
        parser.add_argument('-image-format',
                            help = 'Specify the format for the output images. Use PNG for lossless quality, JPG for smaller file sizes, or SVG for vector graphics. The image format. Allowed values are png, jpg, svg. Default is png.')
        parser.add_argument('-css-mode',
                            help = 'Specify where the style sheets are stored. Use separate files for better browser caching and easier debugging. Use embedded for single-file HTML output. The style sheet storage mode. Allowed values are embed, separate. Default is embed.')
        parser.add_argument('-font-mode',
                            help = 'Specify where the fonts are stored. Use separate files for better browser caching and to reduce HTML file size. Use embedded for single-file portability. The font storage mode. Allowed values are embed, separate. Default is embed.')
        parser.add_argument('-type3-mode',
                            help = 'Set the processing mode for handling Type 3 fonts. The type3 font mode. Allowed values are raster, convert. Default is raster.')
        parser.add_argument('-split-ligatures',
                            action = 'store_true',
                            help = 'Converts ligatures, two or more letters combined into a single glyph, back into their individual ASCII characters.')
        parser.add_argument('-custom-css',
                            help = 'Apply custom CSS to the output HTML document to modify the visual appearance and layout. Use this to customize the styling of the converted HTML, adjust fonts, colors, spacing, or override default conversion styles. Use !important in your CSS rules to prioritize and override conflicting styles. A string containing valid CSS. The string must not be empty.')
        parser.add_argument('-html-namespace',
                            help = 'Add the specified prefix to all id and class attributes in the HTML content, creating a namespace for safe integration into another HTML document. This ensures unique identifiers, preventing conflicts when merging with other HTML. The prefix to add before each id and class attribute name. Start with a letter or underscore, and use only letters, numbers, hyphens, underscores, or colons.')
        parser.add_argument('-force-zip',
                            action = 'store_true',
                            help = 'Enforce the zip output format. Use when you want output as a zip archive even if single-file output would be possible.')
        parser.add_argument('-title',
                            help = 'Set the HTML title. The title from the input PDF is used by default. The HTML title.')
        parser.add_argument('-subject',
                            help = 'Set the HTML subject. The subject from the input PDF is used by default. The HTML subject.')
        parser.add_argument('-author',
                            help = 'Set the HTML author. The author from the input PDF is used by default. The HTML author.')
        parser.add_argument('-keywords',
                            help = 'Associate keywords with the HTML document. Keywords from the input PDF are used by default. The string containing the keywords.')
        parser.add_argument('-debug-log',
                            action = 'store_true',
                            help = 'Turn on debug logging to troubleshoot conversion issues. Details about the conversion process, including resource loading, rendering steps, and error messages are stored in the debug log. Use this when conversions fail or produce unexpected results.')
        parser.add_argument('-tag',
                            help = 'Tag the conversion with a custom value for tracking and analytics. Use this to categorize conversions by customer ID, document type, or business unit. The tag appears in conversion statistics. A value longer than 32 characters is cut off. A string with the custom tag.')
        parser.add_argument('-http-proxy',
                            help = 'A proxy server used by the conversion process for accessing the source URLs with HTTP scheme. This can help circumvent regional restrictions or provide limited access to your intranet. The value must have format DOMAIN_OR_IP_ADDRESS:PORT.')
        parser.add_argument('-https-proxy',
                            help = 'A proxy server used by the conversion process for accessing the source URLs with HTTPS scheme. This can help circumvent regional restrictions or provide limited access to your intranet. The value must have format DOMAIN_OR_IP_ADDRESS:PORT.')
        parser.add_argument('-converter-version',
                            help = 'Set the converter version. Different versions may produce different output. Choose which one provides the best output for your case. The version identifier. Allowed values are 24.04, 20.10, 18.10, latest. Default is 24.04.')
        parser.add_argument('-use-http',
                            action = 'store_true',
                            help = 'Specify whether to use HTTP or HTTPS when connecting to the PDFCrowd API. Warning: Using HTTP is insecure as data sent over HTTP is not encrypted. Enable this option only if you know what you are doing.')
        parser.add_argument('-client-user-agent',
                            help = 'Specify the User-Agent HTTP header that the client library will use when interacting with the API. The user agent string.')
        parser.add_argument('-user-agent',
                            help = 'Set a custom user agent HTTP header. It can be useful if you are behind a proxy or a firewall. The user agent string.')
        multi_args['proxy'] = 4
        parser.add_argument('-proxy',
                            help = 'Specify an HTTP proxy that the API client library will use to connect to the internet. PROXY must contain 4 values separated by a semicolon. The proxy hostname. The proxy port. The username. The password.')
        parser.add_argument('-retry-count',
                            help = 'Specify the number of automatic retries when a 502 or 503 HTTP status code is received. The status code indicates a temporary network issue. This feature can be disabled by setting to 0. Number of retries. Default is 1.')

    if converter == 'pdf2text':
        converter_name = 'PdfToTextClient'

        parser = argparse.ArgumentParser(usage = usage,
                                         description = 'Conversion from PDF to text.',
                                         add_help = False,
                                         epilog = epilog)

        add_generic_args(parser)

        parser.add_argument('-pdf-password',
                            help = 'The password to open the encrypted PDF file. The input PDF password.')
        parser.add_argument('-print-page-range',
                            help = 'Set the page range to print. A comma separated list of page numbers or ranges.')
        parser.add_argument('-no-layout',
                            action = 'store_true',
                            help = 'Ignore the original PDF layout. Extract text in reading order without preserving column structure or positioning. Simpler output for pure text extraction.')
        parser.add_argument('-eol',
                            help = 'The end-of-line convention for the text output. Allowed values are unix, dos, mac. Default is unix.')
        parser.add_argument('-page-break-mode',
                            help = 'Specify the page break mode for the text output. Allowed values are none, default, custom. Default is none.')
        parser.add_argument('-custom-page-break',
                            help = 'Specify the custom page break. String to insert between the pages.')
        parser.add_argument('-paragraph-mode',
                            help = 'Specify the paragraph detection mode. Enable to format output with proper paragraph breaks. Use "none" for raw text, or detection modes for formatted output. Allowed values are none, bounding-box, characters. Default is none.')
        parser.add_argument('-line-spacing-threshold',
                            help = 'Set the maximum line spacing when the paragraph detection mode is enabled. The value must be a positive integer percentage. Default is 10%%.')
        parser.add_argument('-remove-hyphenation',
                            action = 'store_true',
                            help = 'Remove the hyphen character from the end of lines.')
        parser.add_argument('-remove-empty-lines',
                            action = 'store_true',
                            help = 'Remove empty lines from the text output.')
        parser.add_argument('-crop-area-x',
                            help = 'Set the top left X coordinate of the crop area in points. Must be a positive integer or 0.')
        parser.add_argument('-crop-area-y',
                            help = 'Set the top left Y coordinate of the crop area in points. Must be a positive integer or 0.')
        parser.add_argument('-crop-area-width',
                            help = 'Set the width of the crop area in points. Must be a positive integer or 0. Default is PDF page width..')
        parser.add_argument('-crop-area-height',
                            help = 'Set the height of the crop area in points. Must be a positive integer or 0. Default is PDF page height..')
        multi_args['crop_area'] = 4
        parser.add_argument('-crop-area',
                            help = 'Set the crop area. It allows you to extract just a part of a PDF page. CROP_AREA must contain 4 values separated by a semicolon. Set the top left X coordinate of the crop area in points. Set the top left Y coordinate of the crop area in points. Set the width of the crop area in points. Set the height of the crop area in points. All values must be a positive integer or 0.')
        parser.add_argument('-debug-log',
                            action = 'store_true',
                            help = 'Turn on debug logging to troubleshoot conversion issues. Details about the conversion process, including resource loading, rendering steps, and error messages are stored in the debug log. Use this when conversions fail or produce unexpected results.')
        parser.add_argument('-tag',
                            help = 'Tag the conversion with a custom value for tracking and analytics. Use this to categorize conversions by customer ID, document type, or business unit. The tag appears in conversion statistics. A value longer than 32 characters is cut off. A string with the custom tag.')
        parser.add_argument('-http-proxy',
                            help = 'A proxy server used by the conversion process for accessing the source URLs with HTTP scheme. This can help circumvent regional restrictions or provide limited access to your intranet. The value must have format DOMAIN_OR_IP_ADDRESS:PORT.')
        parser.add_argument('-https-proxy',
                            help = 'A proxy server used by the conversion process for accessing the source URLs with HTTPS scheme. This can help circumvent regional restrictions or provide limited access to your intranet. The value must have format DOMAIN_OR_IP_ADDRESS:PORT.')
        parser.add_argument('-use-http',
                            action = 'store_true',
                            help = 'Specify whether to use HTTP or HTTPS when connecting to the PDFCrowd API. Warning: Using HTTP is insecure as data sent over HTTP is not encrypted. Enable this option only if you know what you are doing.')
        parser.add_argument('-client-user-agent',
                            help = 'Specify the User-Agent HTTP header that the client library will use when interacting with the API. The user agent string.')
        parser.add_argument('-user-agent',
                            help = 'Set a custom user agent HTTP header. It can be useful if you are behind a proxy or a firewall. The user agent string.')
        multi_args['proxy'] = 4
        parser.add_argument('-proxy',
                            help = 'Specify an HTTP proxy that the API client library will use to connect to the internet. PROXY must contain 4 values separated by a semicolon. The proxy hostname. The proxy port. The username. The password.')
        parser.add_argument('-retry-count',
                            help = 'Specify the number of automatic retries when a 502 or 503 HTTP status code is received. The status code indicates a temporary network issue. This feature can be disabled by setting to 0. Number of retries. Default is 1.')

    if converter == 'pdf2image':
        converter_name = 'PdfToImageClient'

        parser = argparse.ArgumentParser(usage = usage,
                                         description = 'Conversion from PDF to image.',
                                         add_help = False,
                                         epilog = epilog)

        add_generic_args(parser)

        parser.add_argument('-output-format',
                            help = 'The output file format. Allowed values are png, jpg, gif, tiff, bmp, ico, ppm, pgm, pbm, pnm, psb, pct, ras, tga, sgi, sun, webp. Default is png.')
        parser.add_argument('-pdf-password',
                            help = 'Password to open the encrypted PDF file. The input PDF password.')
        parser.add_argument('-print-page-range',
                            help = 'Set the page range to print. A comma separated list of page numbers or ranges.')
        parser.add_argument('-dpi',
                            help = 'Set the output graphics DPI. Higher values increase quality but also file size. Use 72-96 for screen, 150 for web, 300 for print. The DPI value. Default is 144.')
        parser.add_argument('-force-zip',
                            action = 'store_true',
                            help = 'Enforce the zip output format. Get output as zip even for single images. Useful for consistent file handling in automated workflows.')
        parser.add_argument('-use-cropbox',
                            action = 'store_true',
                            help = 'Use the crop box rather than media box. Respects PDF crop settings for trimmed output. Use when PDFs have defined crop boundaries.')
        parser.add_argument('-crop-area-x',
                            help = 'Set the top left X coordinate of the crop area in points. Must be a positive integer or 0.')
        parser.add_argument('-crop-area-y',
                            help = 'Set the top left Y coordinate of the crop area in points. Must be a positive integer or 0.')
        parser.add_argument('-crop-area-width',
                            help = 'Set the width of the crop area in points. Must be a positive integer or 0. Default is PDF page width..')
        parser.add_argument('-crop-area-height',
                            help = 'Set the height of the crop area in points. Must be a positive integer or 0. Default is PDF page height..')
        multi_args['crop_area'] = 4
        parser.add_argument('-crop-area',
                            help = 'Set the crop area. It allows you to extract just a part of a PDF page. CROP_AREA must contain 4 values separated by a semicolon. Set the top left X coordinate of the crop area in points. Set the top left Y coordinate of the crop area in points. Set the width of the crop area in points. Set the height of the crop area in points. All values must be a positive integer or 0.')
        parser.add_argument('-use-grayscale',
                            action = 'store_true',
                            help = 'Generate a grayscale image. Reduces file size and creates professional black-and-white output for printing or document archival.')
        parser.add_argument('-debug-log',
                            action = 'store_true',
                            help = 'Turn on debug logging to troubleshoot conversion issues. Details about the conversion process, including resource loading, rendering steps, and error messages are stored in the debug log. Use this when conversions fail or produce unexpected results.')
        parser.add_argument('-tag',
                            help = 'Tag the conversion with a custom value for tracking and analytics. Use this to categorize conversions by customer ID, document type, or business unit. The tag appears in conversion statistics. A value longer than 32 characters is cut off. A string with the custom tag.')
        parser.add_argument('-http-proxy',
                            help = 'A proxy server used by the conversion process for accessing the source URLs with HTTP scheme. This can help circumvent regional restrictions or provide limited access to your intranet. The value must have format DOMAIN_OR_IP_ADDRESS:PORT.')
        parser.add_argument('-https-proxy',
                            help = 'A proxy server used by the conversion process for accessing the source URLs with HTTPS scheme. This can help circumvent regional restrictions or provide limited access to your intranet. The value must have format DOMAIN_OR_IP_ADDRESS:PORT.')
        parser.add_argument('-use-http',
                            action = 'store_true',
                            help = 'Specify whether to use HTTP or HTTPS when connecting to the PDFCrowd API. Warning: Using HTTP is insecure as data sent over HTTP is not encrypted. Enable this option only if you know what you are doing.')
        parser.add_argument('-client-user-agent',
                            help = 'Specify the User-Agent HTTP header that the client library will use when interacting with the API. The user agent string.')
        parser.add_argument('-user-agent',
                            help = 'Set a custom user agent HTTP header. It can be useful if you are behind a proxy or a firewall. The user agent string.')
        multi_args['proxy'] = 4
        parser.add_argument('-proxy',
                            help = 'Specify an HTTP proxy that the API client library will use to connect to the internet. PROXY must contain 4 values separated by a semicolon. The proxy hostname. The proxy port. The username. The password.')
        parser.add_argument('-retry-count',
                            help = 'Specify the number of automatic retries when a 502 or 503 HTTP status code is received. The status code indicates a temporary network issue. This feature can be disabled by setting to 0. Number of retries. Default is 1.')


    if not parser:
        term_error("Unknown converter '%s'." % converter)

    if help_wanted:
        parser.print_help()
        sys.exit()

    args = parser.parse_args(argv[1:])

    if not args.user_name:
        term_error('Missing user name.')

    if not args.api_key:
        term_error('Missing API key.')

    converter = getattr(sys.modules[__name__], converter_name)(args.user_name, args.api_key)

    def invoke_method(method, value, arg):
        if arg in multi_args.keys():
            values = value.split(';')
            if len(values) != multi_args[arg]:
                raise Error("Invalid number of arguments for '%s': %s" % (arg, value))
            getattr(converter, method)(*values)
        else:
            getattr(converter, method)(value)

    def get_input(source):
        if source == '-':
            lines = (line for line in sys.stdin)
            return 'convertString', ''.join(lines)

        if re.match('(?i)^https?://.*$', source):
            return 'convertUrl', source

        if os.path.isfile(source):
            return 'convertFile', source

        term_error("Invalid source '{}'. Must be a valid file, URL, or '-'.".format(source))

    args.user_name = None
    args.api_key = None
    for arg in vars(args):
        if not arg.startswith('_') and arg != 'source':
            value = getattr(args, arg)
            if value:
                method = ''.join([w.title() if w.islower() else w for w in arg.split('_')])
                try:
                    invoke_method('set' + method, value, arg)
                except AttributeError:
                    invoke_method(method[0].lower() + method[1:], value, arg)

    if converter_name == 'PdfToPdfClient':
        for in_file in args.source:
            converter.addPdfFile(in_file)
        out = converter.convert()
    else:
        method, args = get_input(args.source[0])
        out = getattr(converter, method)(args)
    if PYTHON_3:
        sys.stdout.buffer.write(out)
    else:
        sys.stdout.write(out)

if __name__ == "__main__":
    main(sys.argv[1:])
