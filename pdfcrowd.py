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

__version__ = '4.4.1'

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


    class Error(Exception):
        """Thrown when an error occurs."""
        def __init__(self, error, http_code=None):
            self.http_code = http_code
            self.error = error if isinstance(error, str) else str(error, "utf-8")

        def __str__(self):
            if self.http_code:
                return "%d - %s" % (self.http_code, self.error)
            else:
                return self.error

        def getCode(self):
            return self.http_code

        def getMessage(self):
            return self.error

    class Client:
        """Pdfcrowd API client."""

        def __init__(self, username, apikey, host=None, http_port=None):
            """Client constructor.

            username -- your username at Pdfcrowd
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
                body = body if isinstance(body, bytes) else bytes(body, "utf-8")
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
                raise Error(err[1])

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

        def getCode(self):
            return self.http_code

        def getMessage(self):
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
                raise Error(err[1])


    API_SELECTOR_BASE = '/api/'
    HOST_LEGACY = os.environ.get('PDFCROWD_HOST', 'pdfcrowd.com')
    HTTP_PORT = 80
    HTTPS_PORT = 443

# =====================================
# === PDFCrowd cloud version client ===
# =====================================

HOST = os.environ.get('PDFCROWD_HOST', 'api.pdfcrowd.com')
MULTIPART_BOUNDARY = '----------ThIs_Is_tHe_bOUnDary_$'
CLIENT_VERSION = '4.4.1'

def get_utf8_string(string):
    if not PYTHON_3 and isinstance(string, unicode):
        return string.encode('utf-8')
    return string

def create_invalid_value_message(value, field, converter, hint, id):
    message = "Invalid value '%s' for a field '%s'." % (value, field)
    if hint:
        message += " " + hint
    return message + ' ' + "Details: https://www.pdfcrowd.com/doc/api/%s/python/#%s" % (converter, id)

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
    body.append('\r\n'.join(head).encode('utf-8'))
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
    value = value if isinstance(value, bytes) else bytes(value, 'utf-8')
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
        self.setUserAgent('pdfcrowd_python_client/4.4.1 (http://pdfcrowd.com)')

        self.retry_count = 1

    def _reset_response_data(self):
        self.debug_log_url = None
        self.credits = 999999
        self.consumed_credits = 0
        self.job_id = ''
        self.page_count = 0
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
        if self.proxy_host:
            conn = self._create_connection(self.proxy_host, self.proxy_port)
            conn.putrequest('POST', 'http://%s:%d%s' % (HOST, self.port, '/convert/'))
            if self.proxy_user_name:
                conn.putheader('Proxy-Authorization',
                               encode_credentials(self.proxy_user_name, self.proxy_password))
        else:
            conn = self._create_connection(HOST, self.port)
            conn.putrequest('POST', '/convert/')
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
                if err.getCode() == 502 and self.retry_count > self.retry:
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
            body = body if isinstance(body, bytes) else bytes(body, 'utf-8')
            conn.send(body)
            response = conn.getresponse()

            self.debug_log_url = response.getheader('X-Pdfcrowd-Debug-Log', '')
            self.credits = int(response.getheader('X-Pdfcrowd-Remaining-Credits', 999999))
            self.consumed_credits = int(response.getheader('X-Pdfcrowd-Consumed-Credits', 0))
            self.job_id = response.getheader('X-Pdfcrowd-Job-Id', '')
            self.page_count = int(response.getheader('X-Pdfcrowd-Pages', 0))
            self.output_size = int(response.getheader('X-Pdfcrowd-Output-Size', 0))

            if (os.environ.get('PDFCROWD_UNIT_TEST_MODE') and
                self.retry_count > self.retry):
                raise Error('test 502', 502)

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
            raise Error("There was a problem connecting to Pdfcrowd servers over HTTPS:\n" +
                        "{} ({})".format(err.reason, err.errno) +
                        "\nYou can still use the API over HTTP, you just need to add the following line right after Pdfcrowd client initialization:\nclient.setUseHttp(True)",
                        481)
        except socket.gaierror as err:
            raise Error(err[1])
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

    def getOutputSize(self):
        return self.output_size

# generated code

class HtmlToPdfClient:
    """
    Conversion from HTML to PDF.
    """

    def __init__(self, user_name, api_key):
        """
        Constructor for the Pdfcrowd API client.

        user_name - Your username at Pdfcrowd.
        api_key - Your API key.
        """
        self.helper = ConnectionHelper(user_name, api_key)
        self.fields = {
            'input_format': 'html',
            'output_format': 'pdf'
        }
        self.file_id = 1
        self.files = {}
        self.raw_data = {}

    def convertUrl(self, url):
        """
        Convert a web page.

        url - The address of the web page to convert. The supported protocols are http:// and https://.
        return - Byte array containing the conversion output.
        """
        if not re.match('(?i)^https?://.*$', url):
            raise Error(create_invalid_value_message(url, "url", "html-to-pdf", "The supported protocols are http:// and https://.", "convert_url"), 470);
        
        self.fields['url'] = get_utf8_string(url)
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertUrlToStream(self, url, out_stream):
        """
        Convert a web page and write the result to an output stream.

        url - The address of the web page to convert. The supported protocols are http:// and https://.
        out_stream - The output stream that will contain the conversion output.
        """
        if not re.match('(?i)^https?://.*$', url):
            raise Error(create_invalid_value_message(url, "url", "html-to-pdf", "The supported protocols are http:// and https://.", "convert_url_to_stream"), 470);
        
        self.fields['url'] = get_utf8_string(url)
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertUrlToFile(self, url, file_path):
        """
        Convert a web page and write the result to a local file.

        url - The address of the web page to convert. The supported protocols are http:// and https://.
        file_path - The output file path. The string must not be empty.
        """
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "file_path", "html-to-pdf", "The string must not be empty.", "convert_url_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        try:
            self.convertUrlToStream(url, output_file)
            output_file.close()
        except Error:
            output_file.close()
            os.remove(file_path)
            raise

    def convertFile(self, file):
        """
        Convert a local file.

        file - The path to a local file to convert. The file can be either a single file or an archive (.tar.gz, .tar.bz2, or .zip). If the HTML document refers to local external assets (images, style sheets, javascript), zip the document together with the assets. The file must exist and not be empty. The file name must have a valid extension.
        return - Byte array containing the conversion output.
        """
        if not (os.path.isfile(file) and os.path.getsize(file)):
            raise Error(create_invalid_value_message(file, "file", "html-to-pdf", "The file must exist and not be empty.", "convert_file"), 470);
        
        if not (os.path.isfile(file) and os.path.getsize(file)):
            raise Error(create_invalid_value_message(file, "file", "html-to-pdf", "The file name must have a valid extension.", "convert_file"), 470);
        
        self.files['file'] = get_utf8_string(file)
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertFileToStream(self, file, out_stream):
        """
        Convert a local file and write the result to an output stream.

        file - The path to a local file to convert. The file can be either a single file or an archive (.tar.gz, .tar.bz2, or .zip). If the HTML document refers to local external assets (images, style sheets, javascript), zip the document together with the assets. The file must exist and not be empty. The file name must have a valid extension.
        out_stream - The output stream that will contain the conversion output.
        """
        if not (os.path.isfile(file) and os.path.getsize(file)):
            raise Error(create_invalid_value_message(file, "file", "html-to-pdf", "The file must exist and not be empty.", "convert_file_to_stream"), 470);
        
        if not (os.path.isfile(file) and os.path.getsize(file)):
            raise Error(create_invalid_value_message(file, "file", "html-to-pdf", "The file name must have a valid extension.", "convert_file_to_stream"), 470);
        
        self.files['file'] = get_utf8_string(file)
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertFileToFile(self, file, file_path):
        """
        Convert a local file and write the result to a local file.

        file - The path to a local file to convert. The file can be either a single file or an archive (.tar.gz, .tar.bz2, or .zip). If the HTML document refers to local external assets (images, style sheets, javascript), zip the document together with the assets. The file must exist and not be empty. The file name must have a valid extension.
        file_path - The output file path. The string must not be empty.
        """
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "file_path", "html-to-pdf", "The string must not be empty.", "convert_file_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        try:
            self.convertFileToStream(file, output_file)
            output_file.close()
        except Error:
            output_file.close()
            os.remove(file_path)
            raise

    def convertString(self, text):
        """
        Convert a string.

        text - The string content to convert. The string must not be empty.
        return - Byte array containing the conversion output.
        """
        if not (text):
            raise Error(create_invalid_value_message(text, "text", "html-to-pdf", "The string must not be empty.", "convert_string"), 470);
        
        self.fields['text'] = get_utf8_string(text)
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertStringToStream(self, text, out_stream):
        """
        Convert a string and write the output to an output stream.

        text - The string content to convert. The string must not be empty.
        out_stream - The output stream that will contain the conversion output.
        """
        if not (text):
            raise Error(create_invalid_value_message(text, "text", "html-to-pdf", "The string must not be empty.", "convert_string_to_stream"), 470);
        
        self.fields['text'] = get_utf8_string(text)
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertStringToFile(self, text, file_path):
        """
        Convert a string and write the output to a file.

        text - The string content to convert. The string must not be empty.
        file_path - The output file path. The string must not be empty.
        """
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "file_path", "html-to-pdf", "The string must not be empty.", "convert_string_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        try:
            self.convertStringToStream(text, output_file)
            output_file.close()
        except Error:
            output_file.close()
            os.remove(file_path)
            raise

    def setPageSize(self, page_size):
        """
        Set the output page size.

        page_size - Allowed values are A2, A3, A4, A5, A6, Letter.
        return - The converter object.
        """
        if not re.match('(?i)^(A2|A3|A4|A5|A6|Letter)$', page_size):
            raise Error(create_invalid_value_message(page_size, "page_size", "html-to-pdf", "Allowed values are A2, A3, A4, A5, A6, Letter.", "set_page_size"), 470);
        
        self.fields['page_size'] = get_utf8_string(page_size)
        return self

    def setPageWidth(self, page_width):
        """
        Set the output page width. The safe maximum is 200in otherwise some PDF viewers may be unable to open the PDF.

        page_width - Can be specified in inches (in), millimeters (mm), centimeters (cm), or points (pt).
        return - The converter object.
        """
        if not re.match('(?i)^[0-9]*(\.[0-9]+)?(pt|px|mm|cm|in)$', page_width):
            raise Error(create_invalid_value_message(page_width, "page_width", "html-to-pdf", "Can be specified in inches (in), millimeters (mm), centimeters (cm), or points (pt).", "set_page_width"), 470);
        
        self.fields['page_width'] = get_utf8_string(page_width)
        return self

    def setPageHeight(self, page_height):
        """
        Set the output page height. Use -1 for a single page PDF. The safe maximum is 200in otherwise some PDF viewers may be unable to open the PDF.

        page_height - Can be -1 or specified in inches (in), millimeters (mm), centimeters (cm), or points (pt).
        return - The converter object.
        """
        if not re.match('(?i)^\-1$|^[0-9]*(\.[0-9]+)?(pt|px|mm|cm|in)$', page_height):
            raise Error(create_invalid_value_message(page_height, "page_height", "html-to-pdf", "Can be -1 or specified in inches (in), millimeters (mm), centimeters (cm), or points (pt).", "set_page_height"), 470);
        
        self.fields['page_height'] = get_utf8_string(page_height)
        return self

    def setPageDimensions(self, width, height):
        """
        Set the output page dimensions.

        width - Set the output page width. The safe maximum is 200in otherwise some PDF viewers may be unable to open the PDF. Can be specified in inches (in), millimeters (mm), centimeters (cm), or points (pt).
        height - Set the output page height. Use -1 for a single page PDF. The safe maximum is 200in otherwise some PDF viewers may be unable to open the PDF. Can be -1 or specified in inches (in), millimeters (mm), centimeters (cm), or points (pt).
        return - The converter object.
        """
        self.setPageWidth(width)
        self.setPageHeight(height)
        return self

    def setOrientation(self, orientation):
        """
        Set the output page orientation.

        orientation - Allowed values are landscape, portrait.
        return - The converter object.
        """
        if not re.match('(?i)^(landscape|portrait)$', orientation):
            raise Error(create_invalid_value_message(orientation, "orientation", "html-to-pdf", "Allowed values are landscape, portrait.", "set_orientation"), 470);
        
        self.fields['orientation'] = get_utf8_string(orientation)
        return self

    def setMarginTop(self, margin_top):
        """
        Set the output page top margin.

        margin_top - Can be specified in inches (in), millimeters (mm), centimeters (cm), or points (pt).
        return - The converter object.
        """
        if not re.match('(?i)^[0-9]*(\.[0-9]+)?(pt|px|mm|cm|in)$', margin_top):
            raise Error(create_invalid_value_message(margin_top, "margin_top", "html-to-pdf", "Can be specified in inches (in), millimeters (mm), centimeters (cm), or points (pt).", "set_margin_top"), 470);
        
        self.fields['margin_top'] = get_utf8_string(margin_top)
        return self

    def setMarginRight(self, margin_right):
        """
        Set the output page right margin.

        margin_right - Can be specified in inches (in), millimeters (mm), centimeters (cm), or points (pt).
        return - The converter object.
        """
        if not re.match('(?i)^[0-9]*(\.[0-9]+)?(pt|px|mm|cm|in)$', margin_right):
            raise Error(create_invalid_value_message(margin_right, "margin_right", "html-to-pdf", "Can be specified in inches (in), millimeters (mm), centimeters (cm), or points (pt).", "set_margin_right"), 470);
        
        self.fields['margin_right'] = get_utf8_string(margin_right)
        return self

    def setMarginBottom(self, margin_bottom):
        """
        Set the output page bottom margin.

        margin_bottom - Can be specified in inches (in), millimeters (mm), centimeters (cm), or points (pt).
        return - The converter object.
        """
        if not re.match('(?i)^[0-9]*(\.[0-9]+)?(pt|px|mm|cm|in)$', margin_bottom):
            raise Error(create_invalid_value_message(margin_bottom, "margin_bottom", "html-to-pdf", "Can be specified in inches (in), millimeters (mm), centimeters (cm), or points (pt).", "set_margin_bottom"), 470);
        
        self.fields['margin_bottom'] = get_utf8_string(margin_bottom)
        return self

    def setMarginLeft(self, margin_left):
        """
        Set the output page left margin.

        margin_left - Can be specified in inches (in), millimeters (mm), centimeters (cm), or points (pt).
        return - The converter object.
        """
        if not re.match('(?i)^[0-9]*(\.[0-9]+)?(pt|px|mm|cm|in)$', margin_left):
            raise Error(create_invalid_value_message(margin_left, "margin_left", "html-to-pdf", "Can be specified in inches (in), millimeters (mm), centimeters (cm), or points (pt).", "set_margin_left"), 470);
        
        self.fields['margin_left'] = get_utf8_string(margin_left)
        return self

    def setNoMargins(self, no_margins):
        """
        Disable margins.

        no_margins - Set to True to disable margins.
        return - The converter object.
        """
        self.fields['no_margins'] = no_margins
        return self

    def setPageMargins(self, top, right, bottom, left):
        """
        Set the output page margins.

        top - Set the output page top margin. Can be specified in inches (in), millimeters (mm), centimeters (cm), or points (pt).
        right - Set the output page right margin. Can be specified in inches (in), millimeters (mm), centimeters (cm), or points (pt).
        bottom - Set the output page bottom margin. Can be specified in inches (in), millimeters (mm), centimeters (cm), or points (pt).
        left - Set the output page left margin. Can be specified in inches (in), millimeters (mm), centimeters (cm), or points (pt).
        return - The converter object.
        """
        self.setMarginTop(top)
        self.setMarginRight(right)
        self.setMarginBottom(bottom)
        self.setMarginLeft(left)
        return self

    def setHeaderUrl(self, header_url):
        """
        Load an HTML code from the specified URL and use it as the page header. The following classes can be used in the HTML. The content of the respective elements will be expanded as follows: pdfcrowd-page-count - the total page count of printed pages pdfcrowd-page-number - the current page number pdfcrowd-source-url - the source URL of a converted document The following attributes can be used: data-pdfcrowd-number-format - specifies the type of the used numerals Arabic numerals are used by default. Roman numerals can be generated by the roman and roman-lowercase values Example: <span class='pdfcrowd-page-number' data-pdfcrowd-number-format='roman'></span> data-pdfcrowd-placement - specifies where to place the source URL, allowed values: The URL is inserted to the content Example: <span class='pdfcrowd-source-url'></span> will produce <span>http://example.com</span> href - the URL is set to the href attribute Example: <a class='pdfcrowd-source-url' data-pdfcrowd-placement='href'>Link to source</a> will produce <a href='http://example.com'>Link to source</a> href-and-content - the URL is set to the href attribute and to the content Example: <a class='pdfcrowd-source-url' data-pdfcrowd-placement='href-and-content'></a> will produce <a href='http://example.com'>http://example.com</a>

        header_url - The supported protocols are http:// and https://.
        return - The converter object.
        """
        if not re.match('(?i)^https?://.*$', header_url):
            raise Error(create_invalid_value_message(header_url, "header_url", "html-to-pdf", "The supported protocols are http:// and https://.", "set_header_url"), 470);
        
        self.fields['header_url'] = get_utf8_string(header_url)
        return self

    def setHeaderHtml(self, header_html):
        """
        Use the specified HTML code as the page header. The following classes can be used in the HTML. The content of the respective elements will be expanded as follows: pdfcrowd-page-count - the total page count of printed pages pdfcrowd-page-number - the current page number pdfcrowd-source-url - the source URL of a converted document The following attributes can be used: data-pdfcrowd-number-format - specifies the type of the used numerals Arabic numerals are used by default. Roman numerals can be generated by the roman and roman-lowercase values Example: <span class='pdfcrowd-page-number' data-pdfcrowd-number-format='roman'></span> data-pdfcrowd-placement - specifies where to place the source URL, allowed values: The URL is inserted to the content Example: <span class='pdfcrowd-source-url'></span> will produce <span>http://example.com</span> href - the URL is set to the href attribute Example: <a class='pdfcrowd-source-url' data-pdfcrowd-placement='href'>Link to source</a> will produce <a href='http://example.com'>Link to source</a> href-and-content - the URL is set to the href attribute and to the content Example: <a class='pdfcrowd-source-url' data-pdfcrowd-placement='href-and-content'></a> will produce <a href='http://example.com'>http://example.com</a>

        header_html - The string must not be empty.
        return - The converter object.
        """
        if not (header_html):
            raise Error(create_invalid_value_message(header_html, "header_html", "html-to-pdf", "The string must not be empty.", "set_header_html"), 470);
        
        self.fields['header_html'] = get_utf8_string(header_html)
        return self

    def setHeaderHeight(self, header_height):
        """
        Set the header height.

        header_height - Can be specified in inches (in), millimeters (mm), centimeters (cm), or points (pt).
        return - The converter object.
        """
        if not re.match('(?i)^[0-9]*(\.[0-9]+)?(pt|px|mm|cm|in)$', header_height):
            raise Error(create_invalid_value_message(header_height, "header_height", "html-to-pdf", "Can be specified in inches (in), millimeters (mm), centimeters (cm), or points (pt).", "set_header_height"), 470);
        
        self.fields['header_height'] = get_utf8_string(header_height)
        return self

    def setFooterUrl(self, footer_url):
        """
        Load an HTML code from the specified URL and use it as the page footer. The following classes can be used in the HTML. The content of the respective elements will be expanded as follows: pdfcrowd-page-count - the total page count of printed pages pdfcrowd-page-number - the current page number pdfcrowd-source-url - the source URL of a converted document The following attributes can be used: data-pdfcrowd-number-format - specifies the type of the used numerals Arabic numerals are used by default. Roman numerals can be generated by the roman and roman-lowercase values Example: <span class='pdfcrowd-page-number' data-pdfcrowd-number-format='roman'></span> data-pdfcrowd-placement - specifies where to place the source URL, allowed values: The URL is inserted to the content Example: <span class='pdfcrowd-source-url'></span> will produce <span>http://example.com</span> href - the URL is set to the href attribute Example: <a class='pdfcrowd-source-url' data-pdfcrowd-placement='href'>Link to source</a> will produce <a href='http://example.com'>Link to source</a> href-and-content - the URL is set to the href attribute and to the content Example: <a class='pdfcrowd-source-url' data-pdfcrowd-placement='href-and-content'></a> will produce <a href='http://example.com'>http://example.com</a>

        footer_url - The supported protocols are http:// and https://.
        return - The converter object.
        """
        if not re.match('(?i)^https?://.*$', footer_url):
            raise Error(create_invalid_value_message(footer_url, "footer_url", "html-to-pdf", "The supported protocols are http:// and https://.", "set_footer_url"), 470);
        
        self.fields['footer_url'] = get_utf8_string(footer_url)
        return self

    def setFooterHtml(self, footer_html):
        """
        Use the specified HTML as the page footer. The following classes can be used in the HTML. The content of the respective elements will be expanded as follows: pdfcrowd-page-count - the total page count of printed pages pdfcrowd-page-number - the current page number pdfcrowd-source-url - the source URL of a converted document The following attributes can be used: data-pdfcrowd-number-format - specifies the type of the used numerals Arabic numerals are used by default. Roman numerals can be generated by the roman and roman-lowercase values Example: <span class='pdfcrowd-page-number' data-pdfcrowd-number-format='roman'></span> data-pdfcrowd-placement - specifies where to place the source URL, allowed values: The URL is inserted to the content Example: <span class='pdfcrowd-source-url'></span> will produce <span>http://example.com</span> href - the URL is set to the href attribute Example: <a class='pdfcrowd-source-url' data-pdfcrowd-placement='href'>Link to source</a> will produce <a href='http://example.com'>Link to source</a> href-and-content - the URL is set to the href attribute and to the content Example: <a class='pdfcrowd-source-url' data-pdfcrowd-placement='href-and-content'></a> will produce <a href='http://example.com'>http://example.com</a>

        footer_html - The string must not be empty.
        return - The converter object.
        """
        if not (footer_html):
            raise Error(create_invalid_value_message(footer_html, "footer_html", "html-to-pdf", "The string must not be empty.", "set_footer_html"), 470);
        
        self.fields['footer_html'] = get_utf8_string(footer_html)
        return self

    def setFooterHeight(self, footer_height):
        """
        Set the footer height.

        footer_height - Can be specified in inches (in), millimeters (mm), centimeters (cm), or points (pt).
        return - The converter object.
        """
        if not re.match('(?i)^[0-9]*(\.[0-9]+)?(pt|px|mm|cm|in)$', footer_height):
            raise Error(create_invalid_value_message(footer_height, "footer_height", "html-to-pdf", "Can be specified in inches (in), millimeters (mm), centimeters (cm), or points (pt).", "set_footer_height"), 470);
        
        self.fields['footer_height'] = get_utf8_string(footer_height)
        return self

    def setPrintPageRange(self, pages):
        """
        Set the page range to print.

        pages - A comma seperated list of page numbers or ranges.
        return - The converter object.
        """
        if not re.match('^(?:\s*(?:\d+|(?:\d*\s*\-\s*\d+)|(?:\d+\s*\-\s*\d*))\s*,\s*)*\s*(?:\d+|(?:\d*\s*\-\s*\d+)|(?:\d+\s*\-\s*\d*))\s*$', pages):
            raise Error(create_invalid_value_message(pages, "pages", "html-to-pdf", "A comma seperated list of page numbers or ranges.", "set_print_page_range"), 470);
        
        self.fields['print_page_range'] = get_utf8_string(pages)
        return self

    def setPageBackgroundColor(self, page_background_color):
        """
        The page background color in RGB or RGBA hexadecimal format. The color fills the entire page regardless of the margins.

        page_background_color - The value must be in RRGGBB or RRGGBBAA hexadecimal format.
        return - The converter object.
        """
        if not re.match('^[0-9a-fA-F]{6,8}$', page_background_color):
            raise Error(create_invalid_value_message(page_background_color, "page_background_color", "html-to-pdf", "The value must be in RRGGBB or RRGGBBAA hexadecimal format.", "set_page_background_color"), 470);
        
        self.fields['page_background_color'] = get_utf8_string(page_background_color)
        return self

    def setPageWatermark(self, page_watermark):
        """
        Apply the first page of the watermark PDF to every page of the output PDF.

        page_watermark - The file path to a local watermark PDF file. The file must exist and not be empty.
        return - The converter object.
        """
        if not (os.path.isfile(page_watermark) and os.path.getsize(page_watermark)):
            raise Error(create_invalid_value_message(page_watermark, "page_watermark", "html-to-pdf", "The file must exist and not be empty.", "set_page_watermark"), 470);
        
        self.files['page_watermark'] = get_utf8_string(page_watermark)
        return self

    def setMultipageWatermark(self, multipage_watermark):
        """
        Apply each page of the specified watermark PDF to the corresponding page of the output PDF.

        multipage_watermark - The file path to a local watermark PDF file. The file must exist and not be empty.
        return - The converter object.
        """
        if not (os.path.isfile(multipage_watermark) and os.path.getsize(multipage_watermark)):
            raise Error(create_invalid_value_message(multipage_watermark, "multipage_watermark", "html-to-pdf", "The file must exist and not be empty.", "set_multipage_watermark"), 470);
        
        self.files['multipage_watermark'] = get_utf8_string(multipage_watermark)
        return self

    def setPageBackground(self, page_background):
        """
        Apply the first page of the specified PDF to the background of every page of the output PDF.

        page_background - The file path to a local background PDF file. The file must exist and not be empty.
        return - The converter object.
        """
        if not (os.path.isfile(page_background) and os.path.getsize(page_background)):
            raise Error(create_invalid_value_message(page_background, "page_background", "html-to-pdf", "The file must exist and not be empty.", "set_page_background"), 470);
        
        self.files['page_background'] = get_utf8_string(page_background)
        return self

    def setMultipageBackground(self, multipage_background):
        """
        Apply each page of the specified PDF to the background of the corresponding page of the output PDF.

        multipage_background - The file path to a local background PDF file. The file must exist and not be empty.
        return - The converter object.
        """
        if not (os.path.isfile(multipage_background) and os.path.getsize(multipage_background)):
            raise Error(create_invalid_value_message(multipage_background, "multipage_background", "html-to-pdf", "The file must exist and not be empty.", "set_multipage_background"), 470);
        
        self.files['multipage_background'] = get_utf8_string(multipage_background)
        return self

    def setExcludeHeaderOnPages(self, pages):
        """
        The page header is not printed on the specified pages.

        pages - List of physical page numbers. Negative numbers count backwards from the last page: -1 is the last page, -2 is the last but one page, and so on. A comma seperated list of page numbers.
        return - The converter object.
        """
        if not re.match('^(?:\s*\-?\d+\s*,)*\s*\-?\d+\s*$', pages):
            raise Error(create_invalid_value_message(pages, "pages", "html-to-pdf", "A comma seperated list of page numbers.", "set_exclude_header_on_pages"), 470);
        
        self.fields['exclude_header_on_pages'] = get_utf8_string(pages)
        return self

    def setExcludeFooterOnPages(self, pages):
        """
        The page footer is not printed on the specified pages.

        pages - List of physical page numbers. Negative numbers count backwards from the last page: -1 is the last page, -2 is the last but one page, and so on. A comma seperated list of page numbers.
        return - The converter object.
        """
        if not re.match('^(?:\s*\-?\d+\s*,)*\s*\-?\d+\s*$', pages):
            raise Error(create_invalid_value_message(pages, "pages", "html-to-pdf", "A comma seperated list of page numbers.", "set_exclude_footer_on_pages"), 470);
        
        self.fields['exclude_footer_on_pages'] = get_utf8_string(pages)
        return self

    def setPageNumberingOffset(self, offset):
        """
        Set an offset between physical and logical page numbers.

        offset - Integer specifying page offset.
        return - The converter object.
        """
        self.fields['page_numbering_offset'] = offset
        return self

    def setNoBackground(self, no_background):
        """
        Do not print the background graphics.

        no_background - Set to True to disable the background graphics.
        return - The converter object.
        """
        self.fields['no_background'] = no_background
        return self

    def setDisableJavascript(self, disable_javascript):
        """
        Do not execute JavaScript.

        disable_javascript - Set to True to disable JavaScript in web pages.
        return - The converter object.
        """
        self.fields['disable_javascript'] = disable_javascript
        return self

    def setDisableImageLoading(self, disable_image_loading):
        """
        Do not load images.

        disable_image_loading - Set to True to disable loading of images.
        return - The converter object.
        """
        self.fields['disable_image_loading'] = disable_image_loading
        return self

    def setDisableRemoteFonts(self, disable_remote_fonts):
        """
        Disable loading fonts from remote sources.

        disable_remote_fonts - Set to True disable loading remote fonts.
        return - The converter object.
        """
        self.fields['disable_remote_fonts'] = disable_remote_fonts
        return self

    def setBlockAds(self, block_ads):
        """
        Try to block ads. Enabling this option can produce smaller output and speed up the conversion.

        block_ads - Set to True to block ads in web pages.
        return - The converter object.
        """
        self.fields['block_ads'] = block_ads
        return self

    def setDefaultEncoding(self, default_encoding):
        """
        Set the default HTML content text encoding.

        default_encoding - The text encoding of the HTML content.
        return - The converter object.
        """
        self.fields['default_encoding'] = get_utf8_string(default_encoding)
        return self

    def setHttpAuthUserName(self, user_name):
        """
        Set the HTTP authentication user name.

        user_name - The user name.
        return - The converter object.
        """
        self.fields['http_auth_user_name'] = get_utf8_string(user_name)
        return self

    def setHttpAuthPassword(self, password):
        """
        Set the HTTP authentication password.

        password - The password.
        return - The converter object.
        """
        self.fields['http_auth_password'] = get_utf8_string(password)
        return self

    def setHttpAuth(self, user_name, password):
        """
        Set credentials to access HTTP base authentication protected websites.

        user_name - Set the HTTP authentication user name.
        password - Set the HTTP authentication password.
        return - The converter object.
        """
        self.setHttpAuthUserName(user_name)
        self.setHttpAuthPassword(password)
        return self

    def setUsePrintMedia(self, use_print_media):
        """
        Use the print version of the page if available (@media print).

        use_print_media - Set to True to use the print version of the page.
        return - The converter object.
        """
        self.fields['use_print_media'] = use_print_media
        return self

    def setNoXpdfcrowdHeader(self, no_xpdfcrowd_header):
        """
        Do not send the X-Pdfcrowd HTTP header in Pdfcrowd HTTP requests.

        no_xpdfcrowd_header - Set to True to disable sending X-Pdfcrowd HTTP header.
        return - The converter object.
        """
        self.fields['no_xpdfcrowd_header'] = no_xpdfcrowd_header
        return self

    def setCookies(self, cookies):
        """
        Set cookies that are sent in Pdfcrowd HTTP requests.

        cookies - The cookie string.
        return - The converter object.
        """
        self.fields['cookies'] = get_utf8_string(cookies)
        return self

    def setVerifySslCertificates(self, verify_ssl_certificates):
        """
        Do not allow insecure HTTPS connections.

        verify_ssl_certificates - Set to True to enable SSL certificate verification.
        return - The converter object.
        """
        self.fields['verify_ssl_certificates'] = verify_ssl_certificates
        return self

    def setFailOnMainUrlError(self, fail_on_error):
        """
        Abort the conversion if the main URL HTTP status code is greater than or equal to 400.

        fail_on_error - Set to True to abort the conversion.
        return - The converter object.
        """
        self.fields['fail_on_main_url_error'] = fail_on_error
        return self

    def setFailOnAnyUrlError(self, fail_on_error):
        """
        Abort the conversion if any of the sub-request HTTP status code is greater than or equal to 400 or if some sub-requests are still pending. See details in a debug log.

        fail_on_error - Set to True to abort the conversion.
        return - The converter object.
        """
        self.fields['fail_on_any_url_error'] = fail_on_error
        return self

    def setCustomJavascript(self, custom_javascript):
        """
        Run a custom JavaScript after the document is loaded. The script is intended for post-load DOM manipulation (add/remove elements, update CSS, ...).

        custom_javascript - String containing a JavaScript code. The string must not be empty.
        return - The converter object.
        """
        if not (custom_javascript):
            raise Error(create_invalid_value_message(custom_javascript, "custom_javascript", "html-to-pdf", "The string must not be empty.", "set_custom_javascript"), 470);
        
        self.fields['custom_javascript'] = get_utf8_string(custom_javascript)
        return self

    def setCustomHttpHeader(self, custom_http_header):
        """
        Set a custom HTTP header that is sent in Pdfcrowd HTTP requests.

        custom_http_header - A string containing the header name and value separated by a colon.
        return - The converter object.
        """
        if not re.match('^.+:.+$', custom_http_header):
            raise Error(create_invalid_value_message(custom_http_header, "custom_http_header", "html-to-pdf", "A string containing the header name and value separated by a colon.", "set_custom_http_header"), 470);
        
        self.fields['custom_http_header'] = get_utf8_string(custom_http_header)
        return self

    def setJavascriptDelay(self, javascript_delay):
        """
        Wait the specified number of milliseconds to finish all JavaScript after the document is loaded. The maximum value is determined by your API license.

        javascript_delay - The number of milliseconds to wait. Must be a positive integer number or 0.
        return - The converter object.
        """
        if not (int(javascript_delay) >= 0):
            raise Error(create_invalid_value_message(javascript_delay, "javascript_delay", "html-to-pdf", "Must be a positive integer number or 0.", "set_javascript_delay"), 470);
        
        self.fields['javascript_delay'] = javascript_delay
        return self

    def setElementToConvert(self, selectors):
        """
        Convert only the specified element from the main document and its children. The element is specified by one or more CSS selectors. If the element is not found, the conversion fails. If multiple elements are found, the first one is used.

        selectors - One or more CSS selectors separated by commas. The string must not be empty.
        return - The converter object.
        """
        if not (selectors):
            raise Error(create_invalid_value_message(selectors, "selectors", "html-to-pdf", "The string must not be empty.", "set_element_to_convert"), 470);
        
        self.fields['element_to_convert'] = get_utf8_string(selectors)
        return self

    def setElementToConvertMode(self, mode):
        """
        Specify the DOM handling when only a part of the document is converted.

        mode - Allowed values are cut-out, remove-siblings, hide-siblings.
        return - The converter object.
        """
        if not re.match('(?i)^(cut-out|remove-siblings|hide-siblings)$', mode):
            raise Error(create_invalid_value_message(mode, "mode", "html-to-pdf", "Allowed values are cut-out, remove-siblings, hide-siblings.", "set_element_to_convert_mode"), 470);
        
        self.fields['element_to_convert_mode'] = get_utf8_string(mode)
        return self

    def setWaitForElement(self, selectors):
        """
        Wait for the specified element in a source document. The element is specified by one or more CSS selectors. The element is searched for in the main document and all iframes. If the element is not found, the conversion fails. Your API license defines the maximum wait time by "Max Delay" parameter.

        selectors - One or more CSS selectors separated by commas. The string must not be empty.
        return - The converter object.
        """
        if not (selectors):
            raise Error(create_invalid_value_message(selectors, "selectors", "html-to-pdf", "The string must not be empty.", "set_wait_for_element"), 470);
        
        self.fields['wait_for_element'] = get_utf8_string(selectors)
        return self

    def setViewportWidth(self, viewport_width):
        """
        Set the viewport width in pixels. The viewport is the user's visible area of the page.

        viewport_width - The value must be in a range 96-7680.
        return - The converter object.
        """
        if not (int(viewport_width) >= 96 and int(viewport_width) <= 7680):
            raise Error(create_invalid_value_message(viewport_width, "viewport_width", "html-to-pdf", "The value must be in a range 96-7680.", "set_viewport_width"), 470);
        
        self.fields['viewport_width'] = viewport_width
        return self

    def setViewportHeight(self, viewport_height):
        """
        Set the viewport height in pixels. The viewport is the user's visible area of the page.

        viewport_height - Must be a positive integer number.
        return - The converter object.
        """
        if not (int(viewport_height) > 0):
            raise Error(create_invalid_value_message(viewport_height, "viewport_height", "html-to-pdf", "Must be a positive integer number.", "set_viewport_height"), 470);
        
        self.fields['viewport_height'] = viewport_height
        return self

    def setViewport(self, width, height):
        """
        Set the viewport size. The viewport is the user's visible area of the page.

        width - Set the viewport width in pixels. The viewport is the user's visible area of the page. The value must be in a range 96-7680.
        height - Set the viewport height in pixels. The viewport is the user's visible area of the page. Must be a positive integer number.
        return - The converter object.
        """
        self.setViewportWidth(width)
        self.setViewportHeight(height)
        return self

    def setRenderingMode(self, rendering_mode):
        """
        Sets the rendering mode.

        rendering_mode - The rendering mode. Allowed values are default, viewport.
        return - The converter object.
        """
        if not re.match('(?i)^(default|viewport)$', rendering_mode):
            raise Error(create_invalid_value_message(rendering_mode, "rendering_mode", "html-to-pdf", "Allowed values are default, viewport.", "set_rendering_mode"), 470);
        
        self.fields['rendering_mode'] = get_utf8_string(rendering_mode)
        return self

    def setScaleFactor(self, scale_factor):
        """
        Set the scaling factor (zoom) for the main page area.

        scale_factor - The scale factor. The value must be in a range 10-500.
        return - The converter object.
        """
        if not (int(scale_factor) >= 10 and int(scale_factor) <= 500):
            raise Error(create_invalid_value_message(scale_factor, "scale_factor", "html-to-pdf", "The value must be in a range 10-500.", "set_scale_factor"), 470);
        
        self.fields['scale_factor'] = scale_factor
        return self

    def setHeaderFooterScaleFactor(self, header_footer_scale_factor):
        """
        Set the scaling factor (zoom) for the header and footer.

        header_footer_scale_factor - The scale factor. The value must be in a range 10-500.
        return - The converter object.
        """
        if not (int(header_footer_scale_factor) >= 10 and int(header_footer_scale_factor) <= 500):
            raise Error(create_invalid_value_message(header_footer_scale_factor, "header_footer_scale_factor", "html-to-pdf", "The value must be in a range 10-500.", "set_header_footer_scale_factor"), 470);
        
        self.fields['header_footer_scale_factor'] = header_footer_scale_factor
        return self

    def setDisableSmartShrinking(self, disable_smart_shrinking):
        """
        Disable the intelligent shrinking strategy that tries to optimally fit the HTML contents to a PDF page.

        disable_smart_shrinking - Set to True to disable the intelligent shrinking strategy.
        return - The converter object.
        """
        self.fields['disable_smart_shrinking'] = disable_smart_shrinking
        return self

    def setLinearize(self, linearize):
        """
        Create linearized PDF. This is also known as Fast Web View.

        linearize - Set to True to create linearized PDF.
        return - The converter object.
        """
        self.fields['linearize'] = linearize
        return self

    def setEncrypt(self, encrypt):
        """
        Encrypt the PDF. This prevents search engines from indexing the contents.

        encrypt - Set to True to enable PDF encryption.
        return - The converter object.
        """
        self.fields['encrypt'] = encrypt
        return self

    def setUserPassword(self, user_password):
        """
        Protect the PDF with a user password. When a PDF has a user password, it must be supplied in order to view the document and to perform operations allowed by the access permissions.

        user_password - The user password.
        return - The converter object.
        """
        self.fields['user_password'] = get_utf8_string(user_password)
        return self

    def setOwnerPassword(self, owner_password):
        """
        Protect the PDF with an owner password. Supplying an owner password grants unlimited access to the PDF including changing the passwords and access permissions.

        owner_password - The owner password.
        return - The converter object.
        """
        self.fields['owner_password'] = get_utf8_string(owner_password)
        return self

    def setNoPrint(self, no_print):
        """
        Disallow printing of the output PDF.

        no_print - Set to True to set the no-print flag in the output PDF.
        return - The converter object.
        """
        self.fields['no_print'] = no_print
        return self

    def setNoModify(self, no_modify):
        """
        Disallow modification of the ouput PDF.

        no_modify - Set to True to set the read-only only flag in the output PDF.
        return - The converter object.
        """
        self.fields['no_modify'] = no_modify
        return self

    def setNoCopy(self, no_copy):
        """
        Disallow text and graphics extraction from the output PDF.

        no_copy - Set to True to set the no-copy flag in the output PDF.
        return - The converter object.
        """
        self.fields['no_copy'] = no_copy
        return self

    def setTitle(self, title):
        """
        Set the title of the PDF.

        title - The title.
        return - The converter object.
        """
        self.fields['title'] = get_utf8_string(title)
        return self

    def setSubject(self, subject):
        """
        Set the subject of the PDF.

        subject - The subject.
        return - The converter object.
        """
        self.fields['subject'] = get_utf8_string(subject)
        return self

    def setAuthor(self, author):
        """
        Set the author of the PDF.

        author - The author.
        return - The converter object.
        """
        self.fields['author'] = get_utf8_string(author)
        return self

    def setKeywords(self, keywords):
        """
        Associate keywords with the document.

        keywords - The string with the keywords.
        return - The converter object.
        """
        self.fields['keywords'] = get_utf8_string(keywords)
        return self

    def setPageLayout(self, page_layout):
        """
        Specify the page layout to be used when the document is opened.

        page_layout - Allowed values are single-page, one-column, two-column-left, two-column-right.
        return - The converter object.
        """
        if not re.match('(?i)^(single-page|one-column|two-column-left|two-column-right)$', page_layout):
            raise Error(create_invalid_value_message(page_layout, "page_layout", "html-to-pdf", "Allowed values are single-page, one-column, two-column-left, two-column-right.", "set_page_layout"), 470);
        
        self.fields['page_layout'] = get_utf8_string(page_layout)
        return self

    def setPageMode(self, page_mode):
        """
        Specify how the document should be displayed when opened.

        page_mode - Allowed values are full-screen, thumbnails, outlines.
        return - The converter object.
        """
        if not re.match('(?i)^(full-screen|thumbnails|outlines)$', page_mode):
            raise Error(create_invalid_value_message(page_mode, "page_mode", "html-to-pdf", "Allowed values are full-screen, thumbnails, outlines.", "set_page_mode"), 470);
        
        self.fields['page_mode'] = get_utf8_string(page_mode)
        return self

    def setInitialZoomType(self, initial_zoom_type):
        """
        Specify how the page should be displayed when opened.

        initial_zoom_type - Allowed values are fit-width, fit-height, fit-page.
        return - The converter object.
        """
        if not re.match('(?i)^(fit-width|fit-height|fit-page)$', initial_zoom_type):
            raise Error(create_invalid_value_message(initial_zoom_type, "initial_zoom_type", "html-to-pdf", "Allowed values are fit-width, fit-height, fit-page.", "set_initial_zoom_type"), 470);
        
        self.fields['initial_zoom_type'] = get_utf8_string(initial_zoom_type)
        return self

    def setInitialPage(self, initial_page):
        """
        Display the specified page when the document is opened.

        initial_page - Must be a positive integer number.
        return - The converter object.
        """
        if not (int(initial_page) > 0):
            raise Error(create_invalid_value_message(initial_page, "initial_page", "html-to-pdf", "Must be a positive integer number.", "set_initial_page"), 470);
        
        self.fields['initial_page'] = initial_page
        return self

    def setInitialZoom(self, initial_zoom):
        """
        Specify the initial page zoom in percents when the document is opened.

        initial_zoom - Must be a positive integer number.
        return - The converter object.
        """
        if not (int(initial_zoom) > 0):
            raise Error(create_invalid_value_message(initial_zoom, "initial_zoom", "html-to-pdf", "Must be a positive integer number.", "set_initial_zoom"), 470);
        
        self.fields['initial_zoom'] = initial_zoom
        return self

    def setHideToolbar(self, hide_toolbar):
        """
        Specify whether to hide the viewer application's tool bars when the document is active.

        hide_toolbar - Set to True to hide tool bars.
        return - The converter object.
        """
        self.fields['hide_toolbar'] = hide_toolbar
        return self

    def setHideMenubar(self, hide_menubar):
        """
        Specify whether to hide the viewer application's menu bar when the document is active.

        hide_menubar - Set to True to hide the menu bar.
        return - The converter object.
        """
        self.fields['hide_menubar'] = hide_menubar
        return self

    def setHideWindowUi(self, hide_window_ui):
        """
        Specify whether to hide user interface elements in the document's window (such as scroll bars and navigation controls), leaving only the document's contents displayed.

        hide_window_ui - Set to True to hide ui elements.
        return - The converter object.
        """
        self.fields['hide_window_ui'] = hide_window_ui
        return self

    def setFitWindow(self, fit_window):
        """
        Specify whether to resize the document's window to fit the size of the first displayed page.

        fit_window - Set to True to resize the window.
        return - The converter object.
        """
        self.fields['fit_window'] = fit_window
        return self

    def setCenterWindow(self, center_window):
        """
        Specify whether to position the document's window in the center of the screen.

        center_window - Set to True to center the window.
        return - The converter object.
        """
        self.fields['center_window'] = center_window
        return self

    def setDisplayTitle(self, display_title):
        """
        Specify whether the window's title bar should display the document title. If false , the title bar should instead display the name of the PDF file containing the document.

        display_title - Set to True to display the title.
        return - The converter object.
        """
        self.fields['display_title'] = display_title
        return self

    def setRightToLeft(self, right_to_left):
        """
        Set the predominant reading order for text to right-to-left. This option has no direct effect on the document's contents or page numbering but can be used to determine the relative positioning of pages when displayed side by side or printed n-up

        right_to_left - Set to True to set right-to-left reading order.
        return - The converter object.
        """
        self.fields['right_to_left'] = right_to_left
        return self

    def setDebugLog(self, debug_log):
        """
        Turn on the debug logging. Details about the conversion are stored in the debug log. The URL of the log can be obtained from the getDebugLogUrl method or available in conversion statistics.

        debug_log - Set to True to enable the debug logging.
        return - The converter object.
        """
        self.fields['debug_log'] = debug_log
        return self

    def getDebugLogUrl(self):
        """
        Get the URL of the debug log for the last conversion.
        return - The link to the debug log.
        """
        return self.helper.getDebugLogUrl()

    def getRemainingCreditCount(self):
        """
        Get the number of conversion credits available in your account.
        The returned value can differ from the actual count if you run parallel conversions.
        The special value 999999 is returned if the information is not available.
        return - The number of credits.
        """
        return self.helper.getRemainingCreditCount()

    def getConsumedCreditCount(self):
        """
        Get the number of credits consumed by the last conversion.
        return - The number of credits.
        """
        return self.helper.getConsumedCreditCount()

    def getJobId(self):
        """
        Get the job id.
        return - The unique job identifier.
        """
        return self.helper.getJobId()

    def getPageCount(self):
        """
        Get the total number of pages in the output document.
        return - The page count.
        """
        return self.helper.getPageCount()

    def getOutputSize(self):
        """
        Get the size of the output in bytes.
        return - The count of bytes.
        """
        return self.helper.getOutputSize()

    def setTag(self, tag):
        """
        Tag the conversion with a custom value. The tag is used in conversion statistics. A value longer than 32 characters is cut off.

        tag - A string with the custom tag.
        return - The converter object.
        """
        self.fields['tag'] = get_utf8_string(tag)
        return self

    def setHttpProxy(self, http_proxy):
        """
        A proxy server used by Pdfcrowd conversion process for accessing the source URLs with HTTP scheme. It can help to circumvent regional restrictions or provide limited access to your intranet.

        http_proxy - The value must have format DOMAIN_OR_IP_ADDRESS:PORT.
        return - The converter object.
        """
        if not re.match('(?i)^([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z0-9]{1,}:\d+$', http_proxy):
            raise Error(create_invalid_value_message(http_proxy, "http_proxy", "html-to-pdf", "The value must have format DOMAIN_OR_IP_ADDRESS:PORT.", "set_http_proxy"), 470);
        
        self.fields['http_proxy'] = get_utf8_string(http_proxy)
        return self

    def setHttpsProxy(self, https_proxy):
        """
        A proxy server used by Pdfcrowd conversion process for accessing the source URLs with HTTPS scheme. It can help to circumvent regional restrictions or provide limited access to your intranet.

        https_proxy - The value must have format DOMAIN_OR_IP_ADDRESS:PORT.
        return - The converter object.
        """
        if not re.match('(?i)^([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z0-9]{1,}:\d+$', https_proxy):
            raise Error(create_invalid_value_message(https_proxy, "https_proxy", "html-to-pdf", "The value must have format DOMAIN_OR_IP_ADDRESS:PORT.", "set_https_proxy"), 470);
        
        self.fields['https_proxy'] = get_utf8_string(https_proxy)
        return self

    def setClientCertificate(self, client_certificate):
        """
        A client certificate to authenticate Pdfcrowd converter on your web server. The certificate is used for two-way SSL/TLS authentication and adds extra security.

        client_certificate - The file must be in PKCS12 format. The file must exist and not be empty.
        return - The converter object.
        """
        if not (os.path.isfile(client_certificate) and os.path.getsize(client_certificate)):
            raise Error(create_invalid_value_message(client_certificate, "client_certificate", "html-to-pdf", "The file must exist and not be empty.", "set_client_certificate"), 470);
        
        self.files['client_certificate'] = get_utf8_string(client_certificate)
        return self

    def setClientCertificatePassword(self, client_certificate_password):
        """
        A password for PKCS12 file with a client certificate if it's needed.

        client_certificate_password -
        return - The converter object.
        """
        self.fields['client_certificate_password'] = get_utf8_string(client_certificate_password)
        return self

    def setUseHttp(self, use_http):
        """
        Specifies if the client communicates over HTTP or HTTPS with Pdfcrowd API.

        use_http - Set to True to use HTTP.
        return - The converter object.
        """
        self.helper.setUseHttp(use_http)
        return self

    def setUserAgent(self, user_agent):
        """
        Set a custom user agent HTTP header. It can be usefull if you are behind some proxy or firewall.

        user_agent - The user agent string.
        return - The converter object.
        """
        self.helper.setUserAgent(user_agent)
        return self

    def setProxy(self, host, port, user_name, password):
        """
        Specifies an HTTP proxy that the API client library will use to connect to the internet.

        host - The proxy hostname.
        port - The proxy port.
        user_name - The username.
        password - The password.
        return - The converter object.
        """
        self.helper.setProxy(host, port, user_name, password)
        return self

    def setRetryCount(self, retry_count):
        """
        Specifies the number of retries when the 502 HTTP status code is received. The 502 status code indicates a temporary network issue. This feature can be disabled by setting to 0.

        retry_count - Number of retries wanted.
        return - The converter object.
        """
        self.helper.setRetryCount(retry_count)
        return self

class HtmlToImageClient:
    """
    Conversion from HTML to image.
    """

    def __init__(self, user_name, api_key):
        """
        Constructor for the Pdfcrowd API client.

        user_name - Your username at Pdfcrowd.
        api_key - Your API key.
        """
        self.helper = ConnectionHelper(user_name, api_key)
        self.fields = {
            'input_format': 'html',
            'output_format': 'png'
        }
        self.file_id = 1
        self.files = {}
        self.raw_data = {}

    def setOutputFormat(self, output_format):
        """
        The format of the output file.

        output_format - Allowed values are png, jpg, gif, tiff, bmp, ico, ppm, pgm, pbm, pnm, psb, pct, ras, tga, sgi, sun, webp.
        return - The converter object.
        """
        if not re.match('(?i)^(png|jpg|gif|tiff|bmp|ico|ppm|pgm|pbm|pnm|psb|pct|ras|tga|sgi|sun|webp)$', output_format):
            raise Error(create_invalid_value_message(output_format, "output_format", "html-to-image", "Allowed values are png, jpg, gif, tiff, bmp, ico, ppm, pgm, pbm, pnm, psb, pct, ras, tga, sgi, sun, webp.", "set_output_format"), 470);
        
        self.fields['output_format'] = get_utf8_string(output_format)
        return self

    def convertUrl(self, url):
        """
        Convert a web page.

        url - The address of the web page to convert. The supported protocols are http:// and https://.
        return - Byte array containing the conversion output.
        """
        if not re.match('(?i)^https?://.*$', url):
            raise Error(create_invalid_value_message(url, "url", "html-to-image", "The supported protocols are http:// and https://.", "convert_url"), 470);
        
        self.fields['url'] = get_utf8_string(url)
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertUrlToStream(self, url, out_stream):
        """
        Convert a web page and write the result to an output stream.

        url - The address of the web page to convert. The supported protocols are http:// and https://.
        out_stream - The output stream that will contain the conversion output.
        """
        if not re.match('(?i)^https?://.*$', url):
            raise Error(create_invalid_value_message(url, "url", "html-to-image", "The supported protocols are http:// and https://.", "convert_url_to_stream"), 470);
        
        self.fields['url'] = get_utf8_string(url)
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertUrlToFile(self, url, file_path):
        """
        Convert a web page and write the result to a local file.

        url - The address of the web page to convert. The supported protocols are http:// and https://.
        file_path - The output file path. The string must not be empty.
        """
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "file_path", "html-to-image", "The string must not be empty.", "convert_url_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        try:
            self.convertUrlToStream(url, output_file)
            output_file.close()
        except Error:
            output_file.close()
            os.remove(file_path)
            raise

    def convertFile(self, file):
        """
        Convert a local file.

        file - The path to a local file to convert. The file can be either a single file or an archive (.tar.gz, .tar.bz2, or .zip). If the HTML document refers to local external assets (images, style sheets, javascript), zip the document together with the assets. The file must exist and not be empty. The file name must have a valid extension.
        return - Byte array containing the conversion output.
        """
        if not (os.path.isfile(file) and os.path.getsize(file)):
            raise Error(create_invalid_value_message(file, "file", "html-to-image", "The file must exist and not be empty.", "convert_file"), 470);
        
        if not (os.path.isfile(file) and os.path.getsize(file)):
            raise Error(create_invalid_value_message(file, "file", "html-to-image", "The file name must have a valid extension.", "convert_file"), 470);
        
        self.files['file'] = get_utf8_string(file)
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertFileToStream(self, file, out_stream):
        """
        Convert a local file and write the result to an output stream.

        file - The path to a local file to convert. The file can be either a single file or an archive (.tar.gz, .tar.bz2, or .zip). If the HTML document refers to local external assets (images, style sheets, javascript), zip the document together with the assets. The file must exist and not be empty. The file name must have a valid extension.
        out_stream - The output stream that will contain the conversion output.
        """
        if not (os.path.isfile(file) and os.path.getsize(file)):
            raise Error(create_invalid_value_message(file, "file", "html-to-image", "The file must exist and not be empty.", "convert_file_to_stream"), 470);
        
        if not (os.path.isfile(file) and os.path.getsize(file)):
            raise Error(create_invalid_value_message(file, "file", "html-to-image", "The file name must have a valid extension.", "convert_file_to_stream"), 470);
        
        self.files['file'] = get_utf8_string(file)
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertFileToFile(self, file, file_path):
        """
        Convert a local file and write the result to a local file.

        file - The path to a local file to convert. The file can be either a single file or an archive (.tar.gz, .tar.bz2, or .zip). If the HTML document refers to local external assets (images, style sheets, javascript), zip the document together with the assets. The file must exist and not be empty. The file name must have a valid extension.
        file_path - The output file path. The string must not be empty.
        """
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "file_path", "html-to-image", "The string must not be empty.", "convert_file_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        try:
            self.convertFileToStream(file, output_file)
            output_file.close()
        except Error:
            output_file.close()
            os.remove(file_path)
            raise

    def convertString(self, text):
        """
        Convert a string.

        text - The string content to convert. The string must not be empty.
        return - Byte array containing the conversion output.
        """
        if not (text):
            raise Error(create_invalid_value_message(text, "text", "html-to-image", "The string must not be empty.", "convert_string"), 470);
        
        self.fields['text'] = get_utf8_string(text)
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertStringToStream(self, text, out_stream):
        """
        Convert a string and write the output to an output stream.

        text - The string content to convert. The string must not be empty.
        out_stream - The output stream that will contain the conversion output.
        """
        if not (text):
            raise Error(create_invalid_value_message(text, "text", "html-to-image", "The string must not be empty.", "convert_string_to_stream"), 470);
        
        self.fields['text'] = get_utf8_string(text)
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertStringToFile(self, text, file_path):
        """
        Convert a string and write the output to a file.

        text - The string content to convert. The string must not be empty.
        file_path - The output file path. The string must not be empty.
        """
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "file_path", "html-to-image", "The string must not be empty.", "convert_string_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        try:
            self.convertStringToStream(text, output_file)
            output_file.close()
        except Error:
            output_file.close()
            os.remove(file_path)
            raise

    def setNoBackground(self, no_background):
        """
        Do not print the background graphics.

        no_background - Set to True to disable the background graphics.
        return - The converter object.
        """
        self.fields['no_background'] = no_background
        return self

    def setDisableJavascript(self, disable_javascript):
        """
        Do not execute JavaScript.

        disable_javascript - Set to True to disable JavaScript in web pages.
        return - The converter object.
        """
        self.fields['disable_javascript'] = disable_javascript
        return self

    def setDisableImageLoading(self, disable_image_loading):
        """
        Do not load images.

        disable_image_loading - Set to True to disable loading of images.
        return - The converter object.
        """
        self.fields['disable_image_loading'] = disable_image_loading
        return self

    def setDisableRemoteFonts(self, disable_remote_fonts):
        """
        Disable loading fonts from remote sources.

        disable_remote_fonts - Set to True disable loading remote fonts.
        return - The converter object.
        """
        self.fields['disable_remote_fonts'] = disable_remote_fonts
        return self

    def setBlockAds(self, block_ads):
        """
        Try to block ads. Enabling this option can produce smaller output and speed up the conversion.

        block_ads - Set to True to block ads in web pages.
        return - The converter object.
        """
        self.fields['block_ads'] = block_ads
        return self

    def setDefaultEncoding(self, default_encoding):
        """
        Set the default HTML content text encoding.

        default_encoding - The text encoding of the HTML content.
        return - The converter object.
        """
        self.fields['default_encoding'] = get_utf8_string(default_encoding)
        return self

    def setHttpAuthUserName(self, user_name):
        """
        Set the HTTP authentication user name.

        user_name - The user name.
        return - The converter object.
        """
        self.fields['http_auth_user_name'] = get_utf8_string(user_name)
        return self

    def setHttpAuthPassword(self, password):
        """
        Set the HTTP authentication password.

        password - The password.
        return - The converter object.
        """
        self.fields['http_auth_password'] = get_utf8_string(password)
        return self

    def setHttpAuth(self, user_name, password):
        """
        Set credentials to access HTTP base authentication protected websites.

        user_name - Set the HTTP authentication user name.
        password - Set the HTTP authentication password.
        return - The converter object.
        """
        self.setHttpAuthUserName(user_name)
        self.setHttpAuthPassword(password)
        return self

    def setUsePrintMedia(self, use_print_media):
        """
        Use the print version of the page if available (@media print).

        use_print_media - Set to True to use the print version of the page.
        return - The converter object.
        """
        self.fields['use_print_media'] = use_print_media
        return self

    def setNoXpdfcrowdHeader(self, no_xpdfcrowd_header):
        """
        Do not send the X-Pdfcrowd HTTP header in Pdfcrowd HTTP requests.

        no_xpdfcrowd_header - Set to True to disable sending X-Pdfcrowd HTTP header.
        return - The converter object.
        """
        self.fields['no_xpdfcrowd_header'] = no_xpdfcrowd_header
        return self

    def setCookies(self, cookies):
        """
        Set cookies that are sent in Pdfcrowd HTTP requests.

        cookies - The cookie string.
        return - The converter object.
        """
        self.fields['cookies'] = get_utf8_string(cookies)
        return self

    def setVerifySslCertificates(self, verify_ssl_certificates):
        """
        Do not allow insecure HTTPS connections.

        verify_ssl_certificates - Set to True to enable SSL certificate verification.
        return - The converter object.
        """
        self.fields['verify_ssl_certificates'] = verify_ssl_certificates
        return self

    def setFailOnMainUrlError(self, fail_on_error):
        """
        Abort the conversion if the main URL HTTP status code is greater than or equal to 400.

        fail_on_error - Set to True to abort the conversion.
        return - The converter object.
        """
        self.fields['fail_on_main_url_error'] = fail_on_error
        return self

    def setFailOnAnyUrlError(self, fail_on_error):
        """
        Abort the conversion if any of the sub-request HTTP status code is greater than or equal to 400 or if some sub-requests are still pending. See details in a debug log.

        fail_on_error - Set to True to abort the conversion.
        return - The converter object.
        """
        self.fields['fail_on_any_url_error'] = fail_on_error
        return self

    def setCustomJavascript(self, custom_javascript):
        """
        Run a custom JavaScript after the document is loaded. The script is intended for post-load DOM manipulation (add/remove elements, update CSS, ...).

        custom_javascript - String containing a JavaScript code. The string must not be empty.
        return - The converter object.
        """
        if not (custom_javascript):
            raise Error(create_invalid_value_message(custom_javascript, "custom_javascript", "html-to-image", "The string must not be empty.", "set_custom_javascript"), 470);
        
        self.fields['custom_javascript'] = get_utf8_string(custom_javascript)
        return self

    def setCustomHttpHeader(self, custom_http_header):
        """
        Set a custom HTTP header that is sent in Pdfcrowd HTTP requests.

        custom_http_header - A string containing the header name and value separated by a colon.
        return - The converter object.
        """
        if not re.match('^.+:.+$', custom_http_header):
            raise Error(create_invalid_value_message(custom_http_header, "custom_http_header", "html-to-image", "A string containing the header name and value separated by a colon.", "set_custom_http_header"), 470);
        
        self.fields['custom_http_header'] = get_utf8_string(custom_http_header)
        return self

    def setJavascriptDelay(self, javascript_delay):
        """
        Wait the specified number of milliseconds to finish all JavaScript after the document is loaded. The maximum value is determined by your API license.

        javascript_delay - The number of milliseconds to wait. Must be a positive integer number or 0.
        return - The converter object.
        """
        if not (int(javascript_delay) >= 0):
            raise Error(create_invalid_value_message(javascript_delay, "javascript_delay", "html-to-image", "Must be a positive integer number or 0.", "set_javascript_delay"), 470);
        
        self.fields['javascript_delay'] = javascript_delay
        return self

    def setElementToConvert(self, selectors):
        """
        Convert only the specified element from the main document and its children. The element is specified by one or more CSS selectors. If the element is not found, the conversion fails. If multiple elements are found, the first one is used.

        selectors - One or more CSS selectors separated by commas. The string must not be empty.
        return - The converter object.
        """
        if not (selectors):
            raise Error(create_invalid_value_message(selectors, "selectors", "html-to-image", "The string must not be empty.", "set_element_to_convert"), 470);
        
        self.fields['element_to_convert'] = get_utf8_string(selectors)
        return self

    def setElementToConvertMode(self, mode):
        """
        Specify the DOM handling when only a part of the document is converted.

        mode - Allowed values are cut-out, remove-siblings, hide-siblings.
        return - The converter object.
        """
        if not re.match('(?i)^(cut-out|remove-siblings|hide-siblings)$', mode):
            raise Error(create_invalid_value_message(mode, "mode", "html-to-image", "Allowed values are cut-out, remove-siblings, hide-siblings.", "set_element_to_convert_mode"), 470);
        
        self.fields['element_to_convert_mode'] = get_utf8_string(mode)
        return self

    def setWaitForElement(self, selectors):
        """
        Wait for the specified element in a source document. The element is specified by one or more CSS selectors. The element is searched for in the main document and all iframes. If the element is not found, the conversion fails. Your API license defines the maximum wait time by "Max Delay" parameter.

        selectors - One or more CSS selectors separated by commas. The string must not be empty.
        return - The converter object.
        """
        if not (selectors):
            raise Error(create_invalid_value_message(selectors, "selectors", "html-to-image", "The string must not be empty.", "set_wait_for_element"), 470);
        
        self.fields['wait_for_element'] = get_utf8_string(selectors)
        return self

    def setScreenshotWidth(self, screenshot_width):
        """
        Set the output image width in pixels.

        screenshot_width - The value must be in a range 96-7680.
        return - The converter object.
        """
        if not (int(screenshot_width) >= 96 and int(screenshot_width) <= 7680):
            raise Error(create_invalid_value_message(screenshot_width, "screenshot_width", "html-to-image", "The value must be in a range 96-7680.", "set_screenshot_width"), 470);
        
        self.fields['screenshot_width'] = screenshot_width
        return self

    def setScreenshotHeight(self, screenshot_height):
        """
        Set the output image height in pixels. If it's not specified, actual document height is used.

        screenshot_height - Must be a positive integer number.
        return - The converter object.
        """
        if not (int(screenshot_height) > 0):
            raise Error(create_invalid_value_message(screenshot_height, "screenshot_height", "html-to-image", "Must be a positive integer number.", "set_screenshot_height"), 470);
        
        self.fields['screenshot_height'] = screenshot_height
        return self

    def setDebugLog(self, debug_log):
        """
        Turn on the debug logging. Details about the conversion are stored in the debug log. The URL of the log can be obtained from the getDebugLogUrl method or available in conversion statistics.

        debug_log - Set to True to enable the debug logging.
        return - The converter object.
        """
        self.fields['debug_log'] = debug_log
        return self

    def getDebugLogUrl(self):
        """
        Get the URL of the debug log for the last conversion.
        return - The link to the debug log.
        """
        return self.helper.getDebugLogUrl()

    def getRemainingCreditCount(self):
        """
        Get the number of conversion credits available in your account.
        The returned value can differ from the actual count if you run parallel conversions.
        The special value 999999 is returned if the information is not available.
        return - The number of credits.
        """
        return self.helper.getRemainingCreditCount()

    def getConsumedCreditCount(self):
        """
        Get the number of credits consumed by the last conversion.
        return - The number of credits.
        """
        return self.helper.getConsumedCreditCount()

    def getJobId(self):
        """
        Get the job id.
        return - The unique job identifier.
        """
        return self.helper.getJobId()

    def getOutputSize(self):
        """
        Get the size of the output in bytes.
        return - The count of bytes.
        """
        return self.helper.getOutputSize()

    def setTag(self, tag):
        """
        Tag the conversion with a custom value. The tag is used in conversion statistics. A value longer than 32 characters is cut off.

        tag - A string with the custom tag.
        return - The converter object.
        """
        self.fields['tag'] = get_utf8_string(tag)
        return self

    def setHttpProxy(self, http_proxy):
        """
        A proxy server used by Pdfcrowd conversion process for accessing the source URLs with HTTP scheme. It can help to circumvent regional restrictions or provide limited access to your intranet.

        http_proxy - The value must have format DOMAIN_OR_IP_ADDRESS:PORT.
        return - The converter object.
        """
        if not re.match('(?i)^([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z0-9]{1,}:\d+$', http_proxy):
            raise Error(create_invalid_value_message(http_proxy, "http_proxy", "html-to-image", "The value must have format DOMAIN_OR_IP_ADDRESS:PORT.", "set_http_proxy"), 470);
        
        self.fields['http_proxy'] = get_utf8_string(http_proxy)
        return self

    def setHttpsProxy(self, https_proxy):
        """
        A proxy server used by Pdfcrowd conversion process for accessing the source URLs with HTTPS scheme. It can help to circumvent regional restrictions or provide limited access to your intranet.

        https_proxy - The value must have format DOMAIN_OR_IP_ADDRESS:PORT.
        return - The converter object.
        """
        if not re.match('(?i)^([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z0-9]{1,}:\d+$', https_proxy):
            raise Error(create_invalid_value_message(https_proxy, "https_proxy", "html-to-image", "The value must have format DOMAIN_OR_IP_ADDRESS:PORT.", "set_https_proxy"), 470);
        
        self.fields['https_proxy'] = get_utf8_string(https_proxy)
        return self

    def setClientCertificate(self, client_certificate):
        """
        A client certificate to authenticate Pdfcrowd converter on your web server. The certificate is used for two-way SSL/TLS authentication and adds extra security.

        client_certificate - The file must be in PKCS12 format. The file must exist and not be empty.
        return - The converter object.
        """
        if not (os.path.isfile(client_certificate) and os.path.getsize(client_certificate)):
            raise Error(create_invalid_value_message(client_certificate, "client_certificate", "html-to-image", "The file must exist and not be empty.", "set_client_certificate"), 470);
        
        self.files['client_certificate'] = get_utf8_string(client_certificate)
        return self

    def setClientCertificatePassword(self, client_certificate_password):
        """
        A password for PKCS12 file with a client certificate if it's needed.

        client_certificate_password -
        return - The converter object.
        """
        self.fields['client_certificate_password'] = get_utf8_string(client_certificate_password)
        return self

    def setUseHttp(self, use_http):
        """
        Specifies if the client communicates over HTTP or HTTPS with Pdfcrowd API.

        use_http - Set to True to use HTTP.
        return - The converter object.
        """
        self.helper.setUseHttp(use_http)
        return self

    def setUserAgent(self, user_agent):
        """
        Set a custom user agent HTTP header. It can be usefull if you are behind some proxy or firewall.

        user_agent - The user agent string.
        return - The converter object.
        """
        self.helper.setUserAgent(user_agent)
        return self

    def setProxy(self, host, port, user_name, password):
        """
        Specifies an HTTP proxy that the API client library will use to connect to the internet.

        host - The proxy hostname.
        port - The proxy port.
        user_name - The username.
        password - The password.
        return - The converter object.
        """
        self.helper.setProxy(host, port, user_name, password)
        return self

    def setRetryCount(self, retry_count):
        """
        Specifies the number of retries when the 502 HTTP status code is received. The 502 status code indicates a temporary network issue. This feature can be disabled by setting to 0.

        retry_count - Number of retries wanted.
        return - The converter object.
        """
        self.helper.setRetryCount(retry_count)
        return self

class ImageToImageClient:
    """
    Conversion from one image format to another image format.
    """

    def __init__(self, user_name, api_key):
        """
        Constructor for the Pdfcrowd API client.

        user_name - Your username at Pdfcrowd.
        api_key - Your API key.
        """
        self.helper = ConnectionHelper(user_name, api_key)
        self.fields = {
            'input_format': 'image',
            'output_format': 'png'
        }
        self.file_id = 1
        self.files = {}
        self.raw_data = {}

    def convertUrl(self, url):
        """
        Convert an image.

        url - The address of the image to convert. The supported protocols are http:// and https://.
        return - Byte array containing the conversion output.
        """
        if not re.match('(?i)^https?://.*$', url):
            raise Error(create_invalid_value_message(url, "url", "image-to-image", "The supported protocols are http:// and https://.", "convert_url"), 470);
        
        self.fields['url'] = get_utf8_string(url)
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertUrlToStream(self, url, out_stream):
        """
        Convert an image and write the result to an output stream.

        url - The address of the image to convert. The supported protocols are http:// and https://.
        out_stream - The output stream that will contain the conversion output.
        """
        if not re.match('(?i)^https?://.*$', url):
            raise Error(create_invalid_value_message(url, "url", "image-to-image", "The supported protocols are http:// and https://.", "convert_url_to_stream"), 470);
        
        self.fields['url'] = get_utf8_string(url)
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertUrlToFile(self, url, file_path):
        """
        Convert an image and write the result to a local file.

        url - The address of the image to convert. The supported protocols are http:// and https://.
        file_path - The output file path. The string must not be empty.
        """
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "file_path", "image-to-image", "The string must not be empty.", "convert_url_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        try:
            self.convertUrlToStream(url, output_file)
            output_file.close()
        except Error:
            output_file.close()
            os.remove(file_path)
            raise

    def convertFile(self, file):
        """
        Convert a local file.

        file - The path to a local file to convert. The file can be either a single file or an archive (.tar.gz, .tar.bz2, or .zip). The file must exist and not be empty.
        return - Byte array containing the conversion output.
        """
        if not (os.path.isfile(file) and os.path.getsize(file)):
            raise Error(create_invalid_value_message(file, "file", "image-to-image", "The file must exist and not be empty.", "convert_file"), 470);
        
        self.files['file'] = get_utf8_string(file)
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertFileToStream(self, file, out_stream):
        """
        Convert a local file and write the result to an output stream.

        file - The path to a local file to convert. The file can be either a single file or an archive (.tar.gz, .tar.bz2, or .zip). The file must exist and not be empty.
        out_stream - The output stream that will contain the conversion output.
        """
        if not (os.path.isfile(file) and os.path.getsize(file)):
            raise Error(create_invalid_value_message(file, "file", "image-to-image", "The file must exist and not be empty.", "convert_file_to_stream"), 470);
        
        self.files['file'] = get_utf8_string(file)
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertFileToFile(self, file, file_path):
        """
        Convert a local file and write the result to a local file.

        file - The path to a local file to convert. The file can be either a single file or an archive (.tar.gz, .tar.bz2, or .zip). The file must exist and not be empty.
        file_path - The output file path. The string must not be empty.
        """
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "file_path", "image-to-image", "The string must not be empty.", "convert_file_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        try:
            self.convertFileToStream(file, output_file)
            output_file.close()
        except Error:
            output_file.close()
            os.remove(file_path)
            raise

    def convertRawData(self, data):
        """
        Convert raw data.

        data - The raw content to be converted.
        return - Byte array with the output.
        """
        self.raw_data['file'] = data
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertRawDataToStream(self, data, out_stream):
        """
        Convert raw data and write the result to an output stream.

        data - The raw content to be converted.
        out_stream - The output stream that will contain the conversion output.
        """
        self.raw_data['file'] = data
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertRawDataToFile(self, data, file_path):
        """
        Convert raw data to a file.

        data - The raw content to be converted.
        file_path - The output file path. The string must not be empty.
        """
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "file_path", "image-to-image", "The string must not be empty.", "convert_raw_data_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        try:
            self.convertRawDataToStream(data, output_file)
            output_file.close()
        except Error:
            output_file.close()
            os.remove(file_path)
            raise

    def setOutputFormat(self, output_format):
        """
        The format of the output file.

        output_format - Allowed values are png, jpg, gif, tiff, bmp, ico, ppm, pgm, pbm, pnm, psb, pct, ras, tga, sgi, sun, webp.
        return - The converter object.
        """
        if not re.match('(?i)^(png|jpg|gif|tiff|bmp|ico|ppm|pgm|pbm|pnm|psb|pct|ras|tga|sgi|sun|webp)$', output_format):
            raise Error(create_invalid_value_message(output_format, "output_format", "image-to-image", "Allowed values are png, jpg, gif, tiff, bmp, ico, ppm, pgm, pbm, pnm, psb, pct, ras, tga, sgi, sun, webp.", "set_output_format"), 470);
        
        self.fields['output_format'] = get_utf8_string(output_format)
        return self

    def setResize(self, resize):
        """
        Resize the image.

        resize - The resize percentage or new image dimensions.
        return - The converter object.
        """
        self.fields['resize'] = get_utf8_string(resize)
        return self

    def setRotate(self, rotate):
        """
        Rotate the image.

        rotate - The rotation specified in degrees.
        return - The converter object.
        """
        self.fields['rotate'] = get_utf8_string(rotate)
        return self

    def setDebugLog(self, debug_log):
        """
        Turn on the debug logging. Details about the conversion are stored in the debug log. The URL of the log can be obtained from the getDebugLogUrl method or available in conversion statistics.

        debug_log - Set to True to enable the debug logging.
        return - The converter object.
        """
        self.fields['debug_log'] = debug_log
        return self

    def getDebugLogUrl(self):
        """
        Get the URL of the debug log for the last conversion.
        return - The link to the debug log.
        """
        return self.helper.getDebugLogUrl()

    def getRemainingCreditCount(self):
        """
        Get the number of conversion credits available in your account.
        The returned value can differ from the actual count if you run parallel conversions.
        The special value 999999 is returned if the information is not available.
        return - The number of credits.
        """
        return self.helper.getRemainingCreditCount()

    def getConsumedCreditCount(self):
        """
        Get the number of credits consumed by the last conversion.
        return - The number of credits.
        """
        return self.helper.getConsumedCreditCount()

    def getJobId(self):
        """
        Get the job id.
        return - The unique job identifier.
        """
        return self.helper.getJobId()

    def getOutputSize(self):
        """
        Get the size of the output in bytes.
        return - The count of bytes.
        """
        return self.helper.getOutputSize()

    def setTag(self, tag):
        """
        Tag the conversion with a custom value. The tag is used in conversion statistics. A value longer than 32 characters is cut off.

        tag - A string with the custom tag.
        return - The converter object.
        """
        self.fields['tag'] = get_utf8_string(tag)
        return self

    def setHttpProxy(self, http_proxy):
        """
        A proxy server used by Pdfcrowd conversion process for accessing the source URLs with HTTP scheme. It can help to circumvent regional restrictions or provide limited access to your intranet.

        http_proxy - The value must have format DOMAIN_OR_IP_ADDRESS:PORT.
        return - The converter object.
        """
        if not re.match('(?i)^([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z0-9]{1,}:\d+$', http_proxy):
            raise Error(create_invalid_value_message(http_proxy, "http_proxy", "image-to-image", "The value must have format DOMAIN_OR_IP_ADDRESS:PORT.", "set_http_proxy"), 470);
        
        self.fields['http_proxy'] = get_utf8_string(http_proxy)
        return self

    def setHttpsProxy(self, https_proxy):
        """
        A proxy server used by Pdfcrowd conversion process for accessing the source URLs with HTTPS scheme. It can help to circumvent regional restrictions or provide limited access to your intranet.

        https_proxy - The value must have format DOMAIN_OR_IP_ADDRESS:PORT.
        return - The converter object.
        """
        if not re.match('(?i)^([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z0-9]{1,}:\d+$', https_proxy):
            raise Error(create_invalid_value_message(https_proxy, "https_proxy", "image-to-image", "The value must have format DOMAIN_OR_IP_ADDRESS:PORT.", "set_https_proxy"), 470);
        
        self.fields['https_proxy'] = get_utf8_string(https_proxy)
        return self

    def setUseHttp(self, use_http):
        """
        Specifies if the client communicates over HTTP or HTTPS with Pdfcrowd API.

        use_http - Set to True to use HTTP.
        return - The converter object.
        """
        self.helper.setUseHttp(use_http)
        return self

    def setUserAgent(self, user_agent):
        """
        Set a custom user agent HTTP header. It can be usefull if you are behind some proxy or firewall.

        user_agent - The user agent string.
        return - The converter object.
        """
        self.helper.setUserAgent(user_agent)
        return self

    def setProxy(self, host, port, user_name, password):
        """
        Specifies an HTTP proxy that the API client library will use to connect to the internet.

        host - The proxy hostname.
        port - The proxy port.
        user_name - The username.
        password - The password.
        return - The converter object.
        """
        self.helper.setProxy(host, port, user_name, password)
        return self

    def setRetryCount(self, retry_count):
        """
        Specifies the number of retries when the 502 HTTP status code is received. The 502 status code indicates a temporary network issue. This feature can be disabled by setting to 0.

        retry_count - Number of retries wanted.
        return - The converter object.
        """
        self.helper.setRetryCount(retry_count)
        return self

class PdfToPdfClient:
    """
    Conversion from PDF to PDF.
    """

    def __init__(self, user_name, api_key):
        """
        Constructor for the Pdfcrowd API client.

        user_name - Your username at Pdfcrowd.
        api_key - Your API key.
        """
        self.helper = ConnectionHelper(user_name, api_key)
        self.fields = {
            'input_format': 'pdf',
            'output_format': 'pdf'
        }
        self.file_id = 1
        self.files = {}
        self.raw_data = {}

    def setAction(self, action):
        """
        Specifies the action to be performed on the input PDFs.

        action - Allowed values are join, shuffle.
        return - The converter object.
        """
        if not re.match('(?i)^(join|shuffle)$', action):
            raise Error(create_invalid_value_message(action, "action", "pdf-to-pdf", "Allowed values are join, shuffle.", "set_action"), 470);
        
        self.fields['action'] = get_utf8_string(action)
        return self

    def convert(self):
        """
        Perform an action on the input files.
        return - Byte array containing the output PDF.
        """
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertToStream(self, out_stream):
        """
        Perform an action on the input files and write the output PDF to an output stream.

        out_stream - The output stream that will contain the output PDF.
        """
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertToFile(self, file_path):
        """
        Perform an action on the input files and write the output PDF to a file.

        file_path - The output file path. The string must not be empty.
        """
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "file_path", "pdf-to-pdf", "The string must not be empty.", "convert_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        self.convertToStream(output_file)
        output_file.close()

    def addPdfFile(self, file_path):
        """
        Add a PDF file to the list of the input PDFs.

        file_path - The file path to a local PDF file. The file must exist and not be empty.
        return - The converter object.
        """
        if not (os.path.isfile(file_path) and os.path.getsize(file_path)):
            raise Error(create_invalid_value_message(file_path, "file_path", "pdf-to-pdf", "The file must exist and not be empty.", "add_pdf_file"), 470);
        
        self.files['f_{}'.format(self.file_id)] = file_path
        self.file_id += 1
        return self

    def addPdfRawData(self, pdf_raw_data):
        """
        Add in-memory raw PDF data to the list of the input PDFs.Typical usage is for adding PDF created by another Pdfcrowd converter. Example in PHP: $clientPdf2Pdf->addPdfRawData($clientHtml2Pdf->convertUrl('http://www.example.com'));

        pdf_raw_data - The raw PDF data. The input data must be PDF content.
        return - The converter object.
        """
        if not (pdf_raw_data and len(pdf_raw_data) > 300 and (pdf_raw_data[0:4] == '%PDF' or pdf_raw_data[0:4] == u'%PDF' or pdf_raw_data[0:4] == b'%PDF')):
            raise Error(create_invalid_value_message("raw PDF data", "pdf_raw_data", "pdf-to-pdf", "The input data must be PDF content.", "add_pdf_raw_data"), 470);
        
        self.raw_data['f_{}'.format(self.file_id)] = pdf_raw_data
        self.file_id += 1
        return self

    def setDebugLog(self, debug_log):
        """
        Turn on the debug logging. Details about the conversion are stored in the debug log. The URL of the log can be obtained from the getDebugLogUrl method or available in conversion statistics.

        debug_log - Set to True to enable the debug logging.
        return - The converter object.
        """
        self.fields['debug_log'] = debug_log
        return self

    def getDebugLogUrl(self):
        """
        Get the URL of the debug log for the last conversion.
        return - The link to the debug log.
        """
        return self.helper.getDebugLogUrl()

    def getRemainingCreditCount(self):
        """
        Get the number of conversion credits available in your account.
        The returned value can differ from the actual count if you run parallel conversions.
        The special value 999999 is returned if the information is not available.
        return - The number of credits.
        """
        return self.helper.getRemainingCreditCount()

    def getConsumedCreditCount(self):
        """
        Get the number of credits consumed by the last conversion.
        return - The number of credits.
        """
        return self.helper.getConsumedCreditCount()

    def getJobId(self):
        """
        Get the job id.
        return - The unique job identifier.
        """
        return self.helper.getJobId()

    def getPageCount(self):
        """
        Get the total number of pages in the output document.
        return - The page count.
        """
        return self.helper.getPageCount()

    def getOutputSize(self):
        """
        Get the size of the output in bytes.
        return - The count of bytes.
        """
        return self.helper.getOutputSize()

    def setTag(self, tag):
        """
        Tag the conversion with a custom value. The tag is used in conversion statistics. A value longer than 32 characters is cut off.

        tag - A string with the custom tag.
        return - The converter object.
        """
        self.fields['tag'] = get_utf8_string(tag)
        return self

    def setUseHttp(self, use_http):
        """
        Specifies if the client communicates over HTTP or HTTPS with Pdfcrowd API.

        use_http - Set to True to use HTTP.
        return - The converter object.
        """
        self.helper.setUseHttp(use_http)
        return self

    def setUserAgent(self, user_agent):
        """
        Set a custom user agent HTTP header. It can be usefull if you are behind some proxy or firewall.

        user_agent - The user agent string.
        return - The converter object.
        """
        self.helper.setUserAgent(user_agent)
        return self

    def setProxy(self, host, port, user_name, password):
        """
        Specifies an HTTP proxy that the API client library will use to connect to the internet.

        host - The proxy hostname.
        port - The proxy port.
        user_name - The username.
        password - The password.
        return - The converter object.
        """
        self.helper.setProxy(host, port, user_name, password)
        return self

    def setRetryCount(self, retry_count):
        """
        Specifies the number of retries when the 502 HTTP status code is received. The 502 status code indicates a temporary network issue. This feature can be disabled by setting to 0.

        retry_count - Number of retries wanted.
        return - The converter object.
        """
        self.helper.setRetryCount(retry_count)
        return self

class ImageToPdfClient:
    """
    Conversion from an image to PDF.
    """

    def __init__(self, user_name, api_key):
        """
        Constructor for the Pdfcrowd API client.

        user_name - Your username at Pdfcrowd.
        api_key - Your API key.
        """
        self.helper = ConnectionHelper(user_name, api_key)
        self.fields = {
            'input_format': 'image',
            'output_format': 'pdf'
        }
        self.file_id = 1
        self.files = {}
        self.raw_data = {}

    def convertUrl(self, url):
        """
        Convert an image.

        url - The address of the image to convert. The supported protocols are http:// and https://.
        return - Byte array containing the conversion output.
        """
        if not re.match('(?i)^https?://.*$', url):
            raise Error(create_invalid_value_message(url, "url", "image-to-pdf", "The supported protocols are http:// and https://.", "convert_url"), 470);
        
        self.fields['url'] = get_utf8_string(url)
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertUrlToStream(self, url, out_stream):
        """
        Convert an image and write the result to an output stream.

        url - The address of the image to convert. The supported protocols are http:// and https://.
        out_stream - The output stream that will contain the conversion output.
        """
        if not re.match('(?i)^https?://.*$', url):
            raise Error(create_invalid_value_message(url, "url", "image-to-pdf", "The supported protocols are http:// and https://.", "convert_url_to_stream"), 470);
        
        self.fields['url'] = get_utf8_string(url)
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertUrlToFile(self, url, file_path):
        """
        Convert an image and write the result to a local file.

        url - The address of the image to convert. The supported protocols are http:// and https://.
        file_path - The output file path. The string must not be empty.
        """
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "file_path", "image-to-pdf", "The string must not be empty.", "convert_url_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        try:
            self.convertUrlToStream(url, output_file)
            output_file.close()
        except Error:
            output_file.close()
            os.remove(file_path)
            raise

    def convertFile(self, file):
        """
        Convert a local file.

        file - The path to a local file to convert. The file can be either a single file or an archive (.tar.gz, .tar.bz2, or .zip). The file must exist and not be empty.
        return - Byte array containing the conversion output.
        """
        if not (os.path.isfile(file) and os.path.getsize(file)):
            raise Error(create_invalid_value_message(file, "file", "image-to-pdf", "The file must exist and not be empty.", "convert_file"), 470);
        
        self.files['file'] = get_utf8_string(file)
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertFileToStream(self, file, out_stream):
        """
        Convert a local file and write the result to an output stream.

        file - The path to a local file to convert. The file can be either a single file or an archive (.tar.gz, .tar.bz2, or .zip). The file must exist and not be empty.
        out_stream - The output stream that will contain the conversion output.
        """
        if not (os.path.isfile(file) and os.path.getsize(file)):
            raise Error(create_invalid_value_message(file, "file", "image-to-pdf", "The file must exist and not be empty.", "convert_file_to_stream"), 470);
        
        self.files['file'] = get_utf8_string(file)
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertFileToFile(self, file, file_path):
        """
        Convert a local file and write the result to a local file.

        file - The path to a local file to convert. The file can be either a single file or an archive (.tar.gz, .tar.bz2, or .zip). The file must exist and not be empty.
        file_path - The output file path. The string must not be empty.
        """
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "file_path", "image-to-pdf", "The string must not be empty.", "convert_file_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        try:
            self.convertFileToStream(file, output_file)
            output_file.close()
        except Error:
            output_file.close()
            os.remove(file_path)
            raise

    def convertRawData(self, data):
        """
        Convert raw data.

        data - The raw content to be converted.
        return - Byte array with the output.
        """
        self.raw_data['file'] = data
        return self.helper.post(self.fields, self.files, self.raw_data)

    def convertRawDataToStream(self, data, out_stream):
        """
        Convert raw data and write the result to an output stream.

        data - The raw content to be converted.
        out_stream - The output stream that will contain the conversion output.
        """
        self.raw_data['file'] = data
        self.helper.post(self.fields, self.files, self.raw_data, out_stream)

    def convertRawDataToFile(self, data, file_path):
        """
        Convert raw data to a file.

        data - The raw content to be converted.
        file_path - The output file path. The string must not be empty.
        """
        if not (file_path):
            raise Error(create_invalid_value_message(file_path, "file_path", "image-to-pdf", "The string must not be empty.", "convert_raw_data_to_file"), 470);
        
        output_file = open(file_path, 'wb')
        try:
            self.convertRawDataToStream(data, output_file)
            output_file.close()
        except Error:
            output_file.close()
            os.remove(file_path)
            raise

    def setResize(self, resize):
        """
        Resize the image.

        resize - The resize percentage or new image dimensions.
        return - The converter object.
        """
        self.fields['resize'] = get_utf8_string(resize)
        return self

    def setRotate(self, rotate):
        """
        Rotate the image.

        rotate - The rotation specified in degrees.
        return - The converter object.
        """
        self.fields['rotate'] = get_utf8_string(rotate)
        return self

    def setDebugLog(self, debug_log):
        """
        Turn on the debug logging. Details about the conversion are stored in the debug log. The URL of the log can be obtained from the getDebugLogUrl method or available in conversion statistics.

        debug_log - Set to True to enable the debug logging.
        return - The converter object.
        """
        self.fields['debug_log'] = debug_log
        return self

    def getDebugLogUrl(self):
        """
        Get the URL of the debug log for the last conversion.
        return - The link to the debug log.
        """
        return self.helper.getDebugLogUrl()

    def getRemainingCreditCount(self):
        """
        Get the number of conversion credits available in your account.
        The returned value can differ from the actual count if you run parallel conversions.
        The special value 999999 is returned if the information is not available.
        return - The number of credits.
        """
        return self.helper.getRemainingCreditCount()

    def getConsumedCreditCount(self):
        """
        Get the number of credits consumed by the last conversion.
        return - The number of credits.
        """
        return self.helper.getConsumedCreditCount()

    def getJobId(self):
        """
        Get the job id.
        return - The unique job identifier.
        """
        return self.helper.getJobId()

    def getOutputSize(self):
        """
        Get the size of the output in bytes.
        return - The count of bytes.
        """
        return self.helper.getOutputSize()

    def setTag(self, tag):
        """
        Tag the conversion with a custom value. The tag is used in conversion statistics. A value longer than 32 characters is cut off.

        tag - A string with the custom tag.
        return - The converter object.
        """
        self.fields['tag'] = get_utf8_string(tag)
        return self

    def setHttpProxy(self, http_proxy):
        """
        A proxy server used by Pdfcrowd conversion process for accessing the source URLs with HTTP scheme. It can help to circumvent regional restrictions or provide limited access to your intranet.

        http_proxy - The value must have format DOMAIN_OR_IP_ADDRESS:PORT.
        return - The converter object.
        """
        if not re.match('(?i)^([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z0-9]{1,}:\d+$', http_proxy):
            raise Error(create_invalid_value_message(http_proxy, "http_proxy", "image-to-pdf", "The value must have format DOMAIN_OR_IP_ADDRESS:PORT.", "set_http_proxy"), 470);
        
        self.fields['http_proxy'] = get_utf8_string(http_proxy)
        return self

    def setHttpsProxy(self, https_proxy):
        """
        A proxy server used by Pdfcrowd conversion process for accessing the source URLs with HTTPS scheme. It can help to circumvent regional restrictions or provide limited access to your intranet.

        https_proxy - The value must have format DOMAIN_OR_IP_ADDRESS:PORT.
        return - The converter object.
        """
        if not re.match('(?i)^([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z0-9]{1,}:\d+$', https_proxy):
            raise Error(create_invalid_value_message(https_proxy, "https_proxy", "image-to-pdf", "The value must have format DOMAIN_OR_IP_ADDRESS:PORT.", "set_https_proxy"), 470);
        
        self.fields['https_proxy'] = get_utf8_string(https_proxy)
        return self

    def setUseHttp(self, use_http):
        """
        Specifies if the client communicates over HTTP or HTTPS with Pdfcrowd API.

        use_http - Set to True to use HTTP.
        return - The converter object.
        """
        self.helper.setUseHttp(use_http)
        return self

    def setUserAgent(self, user_agent):
        """
        Set a custom user agent HTTP header. It can be usefull if you are behind some proxy or firewall.

        user_agent - The user agent string.
        return - The converter object.
        """
        self.helper.setUserAgent(user_agent)
        return self

    def setProxy(self, host, port, user_name, password):
        """
        Specifies an HTTP proxy that the API client library will use to connect to the internet.

        host - The proxy hostname.
        port - The proxy port.
        user_name - The username.
        password - The password.
        return - The converter object.
        """
        self.helper.setProxy(host, port, user_name, password)
        return self

    def setRetryCount(self, retry_count):
        """
        Specifies the number of retries when the 502 HTTP status code is received. The 502 status code indicates a temporary network issue. This feature can be disabled by setting to 0.

        retry_count - Number of retries wanted.
        return - The converter object.
        """
        self.helper.setRetryCount(retry_count)
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

        parser.add_argument('-page-size',
                            help = 'Set the output page size. Allowed values are A2, A3, A4, A5, A6, Letter.'
)
        parser.add_argument('-page-width',
                            help = 'Set the output page width. The safe maximum is 200in otherwise some PDF viewers may be unable to open the PDF. Can be specified in inches (in), millimeters (mm), centimeters (cm), or points (pt).'
)
        parser.add_argument('-page-height',
                            help = 'Set the output page height. Use -1 for a single page PDF. The safe maximum is 200in otherwise some PDF viewers may be unable to open the PDF. Can be -1 or specified in inches (in), millimeters (mm), centimeters (cm), or points (pt).'
)
        multi_args['page_dimensions'] = 2
        parser.add_argument('-page-dimensions',
                            help = 'Set the output page dimensions. PAGE_DIMENSIONS must contain 2 values separated by a semicolon. Set the output page width. The safe maximum is 200in otherwise some PDF viewers may be unable to open the PDF. Can be specified in inches (in), millimeters (mm), centimeters (cm), or points (pt). Set the output page height. Use -1 for a single page PDF. The safe maximum is 200in otherwise some PDF viewers may be unable to open the PDF. Can be -1 or specified in inches (in), millimeters (mm), centimeters (cm), or points (pt).'
)
        parser.add_argument('-orientation',
                            help = 'Set the output page orientation. Allowed values are landscape, portrait.'
)
        parser.add_argument('-margin-top',
                            help = 'Set the output page top margin. Can be specified in inches (in), millimeters (mm), centimeters (cm), or points (pt).'
)
        parser.add_argument('-margin-right',
                            help = 'Set the output page right margin. Can be specified in inches (in), millimeters (mm), centimeters (cm), or points (pt).'
)
        parser.add_argument('-margin-bottom',
                            help = 'Set the output page bottom margin. Can be specified in inches (in), millimeters (mm), centimeters (cm), or points (pt).'
)
        parser.add_argument('-margin-left',
                            help = 'Set the output page left margin. Can be specified in inches (in), millimeters (mm), centimeters (cm), or points (pt).'
)
        parser.add_argument('-no-margins',
                            action = 'store_true',
                            help = 'Disable margins.'
)
        multi_args['page_margins'] = 4
        parser.add_argument('-page-margins',
                            help = 'Set the output page margins. PAGE_MARGINS must contain 4 values separated by a semicolon. Set the output page top margin. Set the output page right margin. Set the output page bottom margin. Set the output page left margin. All values can be specified in inches (in), millimeters (mm), centimeters (cm), or points (pt).'
)
        parser.add_argument('-header-url',
                            help = 'Load an HTML code from the specified URL and use it as the page header. The following classes can be used in the HTML. The content of the respective elements will be expanded as follows: pdfcrowd-page-count - the total page count of printed pages pdfcrowd-page-number - the current page number pdfcrowd-source-url - the source URL of a converted document The following attributes can be used: data-pdfcrowd-number-format - specifies the type of the used numerals Arabic numerals are used by default. Roman numerals can be generated by the roman and roman-lowercase values Example: <span class=\'pdfcrowd-page-number\' data-pdfcrowd-number-format=\'roman\'></span> data-pdfcrowd-placement - specifies where to place the source URL, allowed values: The URL is inserted to the content Example: <span class=\'pdfcrowd-source-url\'></span> will produce <span>http://example.com</span> href - the URL is set to the href attribute Example: <a class=\'pdfcrowd-source-url\' data-pdfcrowd-placement=\'href\'>Link to source</a> will produce <a href=\'http://example.com\'>Link to source</a> href-and-content - the URL is set to the href attribute and to the content Example: <a class=\'pdfcrowd-source-url\' data-pdfcrowd-placement=\'href-and-content\'></a> will produce <a href=\'http://example.com\'>http://example.com</a> The supported protocols are http:// and https://.'
)
        parser.add_argument('-header-html',
                            help = 'Use the specified HTML code as the page header. The following classes can be used in the HTML. The content of the respective elements will be expanded as follows: pdfcrowd-page-count - the total page count of printed pages pdfcrowd-page-number - the current page number pdfcrowd-source-url - the source URL of a converted document The following attributes can be used: data-pdfcrowd-number-format - specifies the type of the used numerals Arabic numerals are used by default. Roman numerals can be generated by the roman and roman-lowercase values Example: <span class=\'pdfcrowd-page-number\' data-pdfcrowd-number-format=\'roman\'></span> data-pdfcrowd-placement - specifies where to place the source URL, allowed values: The URL is inserted to the content Example: <span class=\'pdfcrowd-source-url\'></span> will produce <span>http://example.com</span> href - the URL is set to the href attribute Example: <a class=\'pdfcrowd-source-url\' data-pdfcrowd-placement=\'href\'>Link to source</a> will produce <a href=\'http://example.com\'>Link to source</a> href-and-content - the URL is set to the href attribute and to the content Example: <a class=\'pdfcrowd-source-url\' data-pdfcrowd-placement=\'href-and-content\'></a> will produce <a href=\'http://example.com\'>http://example.com</a> The string must not be empty.'
)
        parser.add_argument('-header-height',
                            help = 'Set the header height. Can be specified in inches (in), millimeters (mm), centimeters (cm), or points (pt).'
)
        parser.add_argument('-footer-url',
                            help = 'Load an HTML code from the specified URL and use it as the page footer. The following classes can be used in the HTML. The content of the respective elements will be expanded as follows: pdfcrowd-page-count - the total page count of printed pages pdfcrowd-page-number - the current page number pdfcrowd-source-url - the source URL of a converted document The following attributes can be used: data-pdfcrowd-number-format - specifies the type of the used numerals Arabic numerals are used by default. Roman numerals can be generated by the roman and roman-lowercase values Example: <span class=\'pdfcrowd-page-number\' data-pdfcrowd-number-format=\'roman\'></span> data-pdfcrowd-placement - specifies where to place the source URL, allowed values: The URL is inserted to the content Example: <span class=\'pdfcrowd-source-url\'></span> will produce <span>http://example.com</span> href - the URL is set to the href attribute Example: <a class=\'pdfcrowd-source-url\' data-pdfcrowd-placement=\'href\'>Link to source</a> will produce <a href=\'http://example.com\'>Link to source</a> href-and-content - the URL is set to the href attribute and to the content Example: <a class=\'pdfcrowd-source-url\' data-pdfcrowd-placement=\'href-and-content\'></a> will produce <a href=\'http://example.com\'>http://example.com</a> The supported protocols are http:// and https://.'
)
        parser.add_argument('-footer-html',
                            help = 'Use the specified HTML as the page footer. The following classes can be used in the HTML. The content of the respective elements will be expanded as follows: pdfcrowd-page-count - the total page count of printed pages pdfcrowd-page-number - the current page number pdfcrowd-source-url - the source URL of a converted document The following attributes can be used: data-pdfcrowd-number-format - specifies the type of the used numerals Arabic numerals are used by default. Roman numerals can be generated by the roman and roman-lowercase values Example: <span class=\'pdfcrowd-page-number\' data-pdfcrowd-number-format=\'roman\'></span> data-pdfcrowd-placement - specifies where to place the source URL, allowed values: The URL is inserted to the content Example: <span class=\'pdfcrowd-source-url\'></span> will produce <span>http://example.com</span> href - the URL is set to the href attribute Example: <a class=\'pdfcrowd-source-url\' data-pdfcrowd-placement=\'href\'>Link to source</a> will produce <a href=\'http://example.com\'>Link to source</a> href-and-content - the URL is set to the href attribute and to the content Example: <a class=\'pdfcrowd-source-url\' data-pdfcrowd-placement=\'href-and-content\'></a> will produce <a href=\'http://example.com\'>http://example.com</a> The string must not be empty.'
)
        parser.add_argument('-footer-height',
                            help = 'Set the footer height. Can be specified in inches (in), millimeters (mm), centimeters (cm), or points (pt).'
)
        parser.add_argument('-print-page-range',
                            help = 'Set the page range to print. A comma seperated list of page numbers or ranges.'
)
        parser.add_argument('-page-background-color',
                            help = 'The page background color in RGB or RGBA hexadecimal format. The color fills the entire page regardless of the margins. The value must be in RRGGBB or RRGGBBAA hexadecimal format.'
)
        parser.add_argument('-page-watermark',
                            help = 'Apply the first page of the watermark PDF to every page of the output PDF. The file path to a local watermark PDF file. The file must exist and not be empty.'
)
        parser.add_argument('-multipage-watermark',
                            help = 'Apply each page of the specified watermark PDF to the corresponding page of the output PDF. The file path to a local watermark PDF file. The file must exist and not be empty.'
)
        parser.add_argument('-page-background',
                            help = 'Apply the first page of the specified PDF to the background of every page of the output PDF. The file path to a local background PDF file. The file must exist and not be empty.'
)
        parser.add_argument('-multipage-background',
                            help = 'Apply each page of the specified PDF to the background of the corresponding page of the output PDF. The file path to a local background PDF file. The file must exist and not be empty.'
)
        parser.add_argument('-exclude-header-on-pages',
                            help = 'The page header is not printed on the specified pages. List of physical page numbers. Negative numbers count backwards from the last page: -1 is the last page, -2 is the last but one page, and so on. A comma seperated list of page numbers.'
)
        parser.add_argument('-exclude-footer-on-pages',
                            help = 'The page footer is not printed on the specified pages. List of physical page numbers. Negative numbers count backwards from the last page: -1 is the last page, -2 is the last but one page, and so on. A comma seperated list of page numbers.'
)
        parser.add_argument('-page-numbering-offset',
                            help = 'Set an offset between physical and logical page numbers. Integer specifying page offset.'
)
        parser.add_argument('-no-background',
                            action = 'store_true',
                            help = 'Do not print the background graphics.'
)
        parser.add_argument('-disable-javascript',
                            action = 'store_true',
                            help = 'Do not execute JavaScript.'
)
        parser.add_argument('-disable-image-loading',
                            action = 'store_true',
                            help = 'Do not load images.'
)
        parser.add_argument('-disable-remote-fonts',
                            action = 'store_true',
                            help = 'Disable loading fonts from remote sources.'
)
        parser.add_argument('-block-ads',
                            action = 'store_true',
                            help = 'Try to block ads. Enabling this option can produce smaller output and speed up the conversion.'
)
        parser.add_argument('-default-encoding',
                            help = 'Set the default HTML content text encoding. The text encoding of the HTML content.'
)
        parser.add_argument('-http-auth-user-name',
                            help = argparse.SUPPRESS
)
        parser.add_argument('-http-auth-password',
                            help = argparse.SUPPRESS
)
        multi_args['http_auth'] = 2
        parser.add_argument('-http-auth',
                            help = 'Set credentials to access HTTP base authentication protected websites. HTTP_AUTH must contain 2 values separated by a semicolon. Set the HTTP authentication user name. Set the HTTP authentication password.'
)
        parser.add_argument('-use-print-media',
                            action = 'store_true',
                            help = 'Use the print version of the page if available (@media print).'
)
        parser.add_argument('-no-xpdfcrowd-header',
                            action = 'store_true',
                            help = 'Do not send the X-Pdfcrowd HTTP header in Pdfcrowd HTTP requests.'
)
        parser.add_argument('-cookies',
                            help = 'Set cookies that are sent in Pdfcrowd HTTP requests. The cookie string.'
)
        parser.add_argument('-verify-ssl-certificates',
                            action = 'store_true',
                            help = 'Do not allow insecure HTTPS connections.'
)
        parser.add_argument('-fail-on-main-url-error',
                            action = 'store_true',
                            help = 'Abort the conversion if the main URL HTTP status code is greater than or equal to 400.'
)
        parser.add_argument('-fail-on-any-url-error',
                            action = 'store_true',
                            help = 'Abort the conversion if any of the sub-request HTTP status code is greater than or equal to 400 or if some sub-requests are still pending. See details in a debug log.'
)
        parser.add_argument('-custom-javascript',
                            help = 'Run a custom JavaScript after the document is loaded. The script is intended for post-load DOM manipulation (add/remove elements, update CSS, ...). String containing a JavaScript code. The string must not be empty.'
)
        parser.add_argument('-custom-http-header',
                            help = 'Set a custom HTTP header that is sent in Pdfcrowd HTTP requests. A string containing the header name and value separated by a colon.'
)
        parser.add_argument('-javascript-delay',
                            help = 'Wait the specified number of milliseconds to finish all JavaScript after the document is loaded. The maximum value is determined by your API license. The number of milliseconds to wait. Must be a positive integer number or 0.'
)
        parser.add_argument('-element-to-convert',
                            help = 'Convert only the specified element from the main document and its children. The element is specified by one or more CSS selectors. If the element is not found, the conversion fails. If multiple elements are found, the first one is used. One or more CSS selectors separated by commas. The string must not be empty.'
)
        parser.add_argument('-element-to-convert-mode',
                            help = 'Specify the DOM handling when only a part of the document is converted. Allowed values are cut-out, remove-siblings, hide-siblings.'
)
        parser.add_argument('-wait-for-element',
                            help = 'Wait for the specified element in a source document. The element is specified by one or more CSS selectors. The element is searched for in the main document and all iframes. If the element is not found, the conversion fails. Your API license defines the maximum wait time by "Max Delay" parameter. One or more CSS selectors separated by commas. The string must not be empty.'
)
        parser.add_argument('-viewport-width',
                            help = argparse.SUPPRESS
)
        parser.add_argument('-viewport-height',
                            help = argparse.SUPPRESS
)
        multi_args['viewport'] = 2
        parser.add_argument('-viewport',
                            help = 'Set the viewport size. The viewport is the user\'s visible area of the page. VIEWPORT must contain 2 values separated by a semicolon. Set the viewport width in pixels. The viewport is the user\'s visible area of the page. The value must be in a range 96-7680. Set the viewport height in pixels. The viewport is the user\'s visible area of the page. Must be a positive integer number.'
)
        parser.add_argument('-rendering-mode',
                            help = 'Sets the rendering mode. The rendering mode. Allowed values are default, viewport.'
)
        parser.add_argument('-scale-factor',
                            help = 'Set the scaling factor (zoom) for the main page area. The scale factor. The value must be in a range 10-500.'
)
        parser.add_argument('-header-footer-scale-factor',
                            help = 'Set the scaling factor (zoom) for the header and footer. The scale factor. The value must be in a range 10-500.'
)
        parser.add_argument('-disable-smart-shrinking',
                            action = 'store_true',
                            help = 'Disable the intelligent shrinking strategy that tries to optimally fit the HTML contents to a PDF page.'
)
        parser.add_argument('-linearize',
                            action = 'store_true',
                            help = 'Create linearized PDF. This is also known as Fast Web View.'
)
        parser.add_argument('-encrypt',
                            action = 'store_true',
                            help = 'Encrypt the PDF. This prevents search engines from indexing the contents.'
)
        parser.add_argument('-user-password',
                            help = 'Protect the PDF with a user password. When a PDF has a user password, it must be supplied in order to view the document and to perform operations allowed by the access permissions. The user password.'
)
        parser.add_argument('-owner-password',
                            help = 'Protect the PDF with an owner password. Supplying an owner password grants unlimited access to the PDF including changing the passwords and access permissions. The owner password.'
)
        parser.add_argument('-no-print',
                            action = 'store_true',
                            help = 'Disallow printing of the output PDF.'
)
        parser.add_argument('-no-modify',
                            action = 'store_true',
                            help = 'Disallow modification of the ouput PDF.'
)
        parser.add_argument('-no-copy',
                            action = 'store_true',
                            help = 'Disallow text and graphics extraction from the output PDF.'
)
        parser.add_argument('-title',
                            help = 'Set the title of the PDF. The title.'
)
        parser.add_argument('-subject',
                            help = 'Set the subject of the PDF. The subject.'
)
        parser.add_argument('-author',
                            help = 'Set the author of the PDF. The author.'
)
        parser.add_argument('-keywords',
                            help = 'Associate keywords with the document. The string with the keywords.'
)
        parser.add_argument('-page-layout',
                            help = 'Specify the page layout to be used when the document is opened. Allowed values are single-page, one-column, two-column-left, two-column-right.'
)
        parser.add_argument('-page-mode',
                            help = 'Specify how the document should be displayed when opened. Allowed values are full-screen, thumbnails, outlines.'
)
        parser.add_argument('-initial-zoom-type',
                            help = 'Specify how the page should be displayed when opened. Allowed values are fit-width, fit-height, fit-page.'
)
        parser.add_argument('-initial-page',
                            help = 'Display the specified page when the document is opened. Must be a positive integer number.'
)
        parser.add_argument('-initial-zoom',
                            help = 'Specify the initial page zoom in percents when the document is opened. Must be a positive integer number.'
)
        parser.add_argument('-hide-toolbar',
                            action = 'store_true',
                            help = 'Specify whether to hide the viewer application\'s tool bars when the document is active.'
)
        parser.add_argument('-hide-menubar',
                            action = 'store_true',
                            help = 'Specify whether to hide the viewer application\'s menu bar when the document is active.'
)
        parser.add_argument('-hide-window-ui',
                            action = 'store_true',
                            help = 'Specify whether to hide user interface elements in the document\'s window (such as scroll bars and navigation controls), leaving only the document\'s contents displayed.'
)
        parser.add_argument('-fit-window',
                            action = 'store_true',
                            help = 'Specify whether to resize the document\'s window to fit the size of the first displayed page.'
)
        parser.add_argument('-center-window',
                            action = 'store_true',
                            help = 'Specify whether to position the document\'s window in the center of the screen.'
)
        parser.add_argument('-display-title',
                            action = 'store_true',
                            help = 'Specify whether the window\'s title bar should display the document title. If false , the title bar should instead display the name of the PDF file containing the document.'
)
        parser.add_argument('-right-to-left',
                            action = 'store_true',
                            help = 'Set the predominant reading order for text to right-to-left. This option has no direct effect on the document\'s contents or page numbering but can be used to determine the relative positioning of pages when displayed side by side or printed n-up'
)
        parser.add_argument('-debug-log',
                            action = 'store_true',
                            help = 'Turn on the debug logging. Details about the conversion are stored in the debug log.'
)
        parser.add_argument('-tag',
                            help = 'Tag the conversion with a custom value. The tag is used in conversion statistics. A value longer than 32 characters is cut off. A string with the custom tag.'
)
        parser.add_argument('-http-proxy',
                            help = 'A proxy server used by Pdfcrowd conversion process for accessing the source URLs with HTTP scheme. It can help to circumvent regional restrictions or provide limited access to your intranet. The value must have format DOMAIN_OR_IP_ADDRESS:PORT.'
)
        parser.add_argument('-https-proxy',
                            help = 'A proxy server used by Pdfcrowd conversion process for accessing the source URLs with HTTPS scheme. It can help to circumvent regional restrictions or provide limited access to your intranet. The value must have format DOMAIN_OR_IP_ADDRESS:PORT.'
)
        parser.add_argument('-client-certificate',
                            help = 'A client certificate to authenticate Pdfcrowd converter on your web server. The certificate is used for two-way SSL/TLS authentication and adds extra security. The file must be in PKCS12 format. The file must exist and not be empty.'
)
        parser.add_argument('-client-certificate-password',
                            help = 'A password for PKCS12 file with a client certificate if it\'s needed.'
)
        parser.add_argument('-use-http',
                            action = 'store_true',
                            help = 'Specifies if the client communicates over HTTP or HTTPS with Pdfcrowd API.'
)
        parser.add_argument('-user-agent',
                            help = 'Set a custom user agent HTTP header. It can be usefull if you are behind some proxy or firewall. The user agent string.'
)
        multi_args['proxy'] = 4
        parser.add_argument('-proxy',
                            help = 'Specifies an HTTP proxy that the API client library will use to connect to the internet. PROXY must contain 4 values separated by a semicolon. The proxy hostname. The proxy port. The username. The password.'
)
        parser.add_argument('-retry-count',
                            help = 'Specifies the number of retries when the 502 HTTP status code is received. The 502 status code indicates a temporary network issue. This feature can be disabled by setting to 0. Number of retries wanted.'
)

    if converter == 'html2image':
        converter_name = 'HtmlToImageClient'

        parser = argparse.ArgumentParser(usage = usage,
                                         description = 'Conversion from HTML to image.',
                                         add_help = False,
                                         epilog = epilog)

        add_generic_args(parser)

        parser.add_argument('-output-format',
                            help = 'The format of the output file. Allowed values are png, jpg, gif, tiff, bmp, ico, ppm, pgm, pbm, pnm, psb, pct, ras, tga, sgi, sun, webp.'
)
        parser.add_argument('-no-background',
                            action = 'store_true',
                            help = 'Do not print the background graphics.'
)
        parser.add_argument('-disable-javascript',
                            action = 'store_true',
                            help = 'Do not execute JavaScript.'
)
        parser.add_argument('-disable-image-loading',
                            action = 'store_true',
                            help = 'Do not load images.'
)
        parser.add_argument('-disable-remote-fonts',
                            action = 'store_true',
                            help = 'Disable loading fonts from remote sources.'
)
        parser.add_argument('-block-ads',
                            action = 'store_true',
                            help = 'Try to block ads. Enabling this option can produce smaller output and speed up the conversion.'
)
        parser.add_argument('-default-encoding',
                            help = 'Set the default HTML content text encoding. The text encoding of the HTML content.'
)
        parser.add_argument('-http-auth-user-name',
                            help = argparse.SUPPRESS
)
        parser.add_argument('-http-auth-password',
                            help = argparse.SUPPRESS
)
        multi_args['http_auth'] = 2
        parser.add_argument('-http-auth',
                            help = 'Set credentials to access HTTP base authentication protected websites. HTTP_AUTH must contain 2 values separated by a semicolon. Set the HTTP authentication user name. Set the HTTP authentication password.'
)
        parser.add_argument('-use-print-media',
                            action = 'store_true',
                            help = 'Use the print version of the page if available (@media print).'
)
        parser.add_argument('-no-xpdfcrowd-header',
                            action = 'store_true',
                            help = 'Do not send the X-Pdfcrowd HTTP header in Pdfcrowd HTTP requests.'
)
        parser.add_argument('-cookies',
                            help = 'Set cookies that are sent in Pdfcrowd HTTP requests. The cookie string.'
)
        parser.add_argument('-verify-ssl-certificates',
                            action = 'store_true',
                            help = 'Do not allow insecure HTTPS connections.'
)
        parser.add_argument('-fail-on-main-url-error',
                            action = 'store_true',
                            help = 'Abort the conversion if the main URL HTTP status code is greater than or equal to 400.'
)
        parser.add_argument('-fail-on-any-url-error',
                            action = 'store_true',
                            help = 'Abort the conversion if any of the sub-request HTTP status code is greater than or equal to 400 or if some sub-requests are still pending. See details in a debug log.'
)
        parser.add_argument('-custom-javascript',
                            help = 'Run a custom JavaScript after the document is loaded. The script is intended for post-load DOM manipulation (add/remove elements, update CSS, ...). String containing a JavaScript code. The string must not be empty.'
)
        parser.add_argument('-custom-http-header',
                            help = 'Set a custom HTTP header that is sent in Pdfcrowd HTTP requests. A string containing the header name and value separated by a colon.'
)
        parser.add_argument('-javascript-delay',
                            help = 'Wait the specified number of milliseconds to finish all JavaScript after the document is loaded. The maximum value is determined by your API license. The number of milliseconds to wait. Must be a positive integer number or 0.'
)
        parser.add_argument('-element-to-convert',
                            help = 'Convert only the specified element from the main document and its children. The element is specified by one or more CSS selectors. If the element is not found, the conversion fails. If multiple elements are found, the first one is used. One or more CSS selectors separated by commas. The string must not be empty.'
)
        parser.add_argument('-element-to-convert-mode',
                            help = 'Specify the DOM handling when only a part of the document is converted. Allowed values are cut-out, remove-siblings, hide-siblings.'
)
        parser.add_argument('-wait-for-element',
                            help = 'Wait for the specified element in a source document. The element is specified by one or more CSS selectors. The element is searched for in the main document and all iframes. If the element is not found, the conversion fails. Your API license defines the maximum wait time by "Max Delay" parameter. One or more CSS selectors separated by commas. The string must not be empty.'
)
        parser.add_argument('-screenshot-width',
                            help = 'Set the output image width in pixels. The value must be in a range 96-7680.'
)
        parser.add_argument('-screenshot-height',
                            help = 'Set the output image height in pixels. If it\'s not specified, actual document height is used. Must be a positive integer number.'
)
        parser.add_argument('-debug-log',
                            action = 'store_true',
                            help = 'Turn on the debug logging. Details about the conversion are stored in the debug log.'
)
        parser.add_argument('-tag',
                            help = 'Tag the conversion with a custom value. The tag is used in conversion statistics. A value longer than 32 characters is cut off. A string with the custom tag.'
)
        parser.add_argument('-http-proxy',
                            help = 'A proxy server used by Pdfcrowd conversion process for accessing the source URLs with HTTP scheme. It can help to circumvent regional restrictions or provide limited access to your intranet. The value must have format DOMAIN_OR_IP_ADDRESS:PORT.'
)
        parser.add_argument('-https-proxy',
                            help = 'A proxy server used by Pdfcrowd conversion process for accessing the source URLs with HTTPS scheme. It can help to circumvent regional restrictions or provide limited access to your intranet. The value must have format DOMAIN_OR_IP_ADDRESS:PORT.'
)
        parser.add_argument('-client-certificate',
                            help = 'A client certificate to authenticate Pdfcrowd converter on your web server. The certificate is used for two-way SSL/TLS authentication and adds extra security. The file must be in PKCS12 format. The file must exist and not be empty.'
)
        parser.add_argument('-client-certificate-password',
                            help = 'A password for PKCS12 file with a client certificate if it\'s needed.'
)
        parser.add_argument('-use-http',
                            action = 'store_true',
                            help = 'Specifies if the client communicates over HTTP or HTTPS with Pdfcrowd API.'
)
        parser.add_argument('-user-agent',
                            help = 'Set a custom user agent HTTP header. It can be usefull if you are behind some proxy or firewall. The user agent string.'
)
        multi_args['proxy'] = 4
        parser.add_argument('-proxy',
                            help = 'Specifies an HTTP proxy that the API client library will use to connect to the internet. PROXY must contain 4 values separated by a semicolon. The proxy hostname. The proxy port. The username. The password.'
)
        parser.add_argument('-retry-count',
                            help = 'Specifies the number of retries when the 502 HTTP status code is received. The 502 status code indicates a temporary network issue. This feature can be disabled by setting to 0. Number of retries wanted.'
)

    if converter == 'image2image':
        converter_name = 'ImageToImageClient'

        parser = argparse.ArgumentParser(usage = usage,
                                         description = 'Conversion from one image format to another image format.',
                                         add_help = False,
                                         epilog = epilog)

        add_generic_args(parser)

        parser.add_argument('-output-format',
                            help = 'The format of the output file. Allowed values are png, jpg, gif, tiff, bmp, ico, ppm, pgm, pbm, pnm, psb, pct, ras, tga, sgi, sun, webp.'
)
        parser.add_argument('-resize',
                            help = 'Resize the image. The resize percentage or new image dimensions.'
)
        parser.add_argument('-rotate',
                            help = 'Rotate the image. The rotation specified in degrees.'
)
        parser.add_argument('-debug-log',
                            action = 'store_true',
                            help = 'Turn on the debug logging. Details about the conversion are stored in the debug log.'
)
        parser.add_argument('-tag',
                            help = 'Tag the conversion with a custom value. The tag is used in conversion statistics. A value longer than 32 characters is cut off. A string with the custom tag.'
)
        parser.add_argument('-http-proxy',
                            help = 'A proxy server used by Pdfcrowd conversion process for accessing the source URLs with HTTP scheme. It can help to circumvent regional restrictions or provide limited access to your intranet. The value must have format DOMAIN_OR_IP_ADDRESS:PORT.'
)
        parser.add_argument('-https-proxy',
                            help = 'A proxy server used by Pdfcrowd conversion process for accessing the source URLs with HTTPS scheme. It can help to circumvent regional restrictions or provide limited access to your intranet. The value must have format DOMAIN_OR_IP_ADDRESS:PORT.'
)
        parser.add_argument('-use-http',
                            action = 'store_true',
                            help = 'Specifies if the client communicates over HTTP or HTTPS with Pdfcrowd API.'
)
        parser.add_argument('-user-agent',
                            help = 'Set a custom user agent HTTP header. It can be usefull if you are behind some proxy or firewall. The user agent string.'
)
        multi_args['proxy'] = 4
        parser.add_argument('-proxy',
                            help = 'Specifies an HTTP proxy that the API client library will use to connect to the internet. PROXY must contain 4 values separated by a semicolon. The proxy hostname. The proxy port. The username. The password.'
)
        parser.add_argument('-retry-count',
                            help = 'Specifies the number of retries when the 502 HTTP status code is received. The 502 status code indicates a temporary network issue. This feature can be disabled by setting to 0. Number of retries wanted.'
)

    if converter == 'pdf2pdf':
        converter_name = 'PdfToPdfClient'

        parser = argparse.ArgumentParser(usage = usage,
                                         description = 'Conversion from PDF to PDF.',
                                         add_help = False,
                                         epilog = epilog)

        add_generic_args(parser, '+')

        parser.add_argument('-action',
                            help = 'Specifies the action to be performed on the input PDFs. Allowed values are join, shuffle.'
)
        parser.add_argument('-debug-log',
                            action = 'store_true',
                            help = 'Turn on the debug logging. Details about the conversion are stored in the debug log.'
)
        parser.add_argument('-tag',
                            help = 'Tag the conversion with a custom value. The tag is used in conversion statistics. A value longer than 32 characters is cut off. A string with the custom tag.'
)
        parser.add_argument('-use-http',
                            action = 'store_true',
                            help = 'Specifies if the client communicates over HTTP or HTTPS with Pdfcrowd API.'
)
        parser.add_argument('-user-agent',
                            help = 'Set a custom user agent HTTP header. It can be usefull if you are behind some proxy or firewall. The user agent string.'
)
        multi_args['proxy'] = 4
        parser.add_argument('-proxy',
                            help = 'Specifies an HTTP proxy that the API client library will use to connect to the internet. PROXY must contain 4 values separated by a semicolon. The proxy hostname. The proxy port. The username. The password.'
)
        parser.add_argument('-retry-count',
                            help = 'Specifies the number of retries when the 502 HTTP status code is received. The 502 status code indicates a temporary network issue. This feature can be disabled by setting to 0. Number of retries wanted.'
)

    if converter == 'image2pdf':
        converter_name = 'ImageToPdfClient'

        parser = argparse.ArgumentParser(usage = usage,
                                         description = 'Conversion from an image to PDF.',
                                         add_help = False,
                                         epilog = epilog)

        add_generic_args(parser)

        parser.add_argument('-resize',
                            help = 'Resize the image. The resize percentage or new image dimensions.'
)
        parser.add_argument('-rotate',
                            help = 'Rotate the image. The rotation specified in degrees.'
)
        parser.add_argument('-debug-log',
                            action = 'store_true',
                            help = 'Turn on the debug logging. Details about the conversion are stored in the debug log.'
)
        parser.add_argument('-tag',
                            help = 'Tag the conversion with a custom value. The tag is used in conversion statistics. A value longer than 32 characters is cut off. A string with the custom tag.'
)
        parser.add_argument('-http-proxy',
                            help = 'A proxy server used by Pdfcrowd conversion process for accessing the source URLs with HTTP scheme. It can help to circumvent regional restrictions or provide limited access to your intranet. The value must have format DOMAIN_OR_IP_ADDRESS:PORT.'
)
        parser.add_argument('-https-proxy',
                            help = 'A proxy server used by Pdfcrowd conversion process for accessing the source URLs with HTTPS scheme. It can help to circumvent regional restrictions or provide limited access to your intranet. The value must have format DOMAIN_OR_IP_ADDRESS:PORT.'
)
        parser.add_argument('-use-http',
                            action = 'store_true',
                            help = 'Specifies if the client communicates over HTTP or HTTPS with Pdfcrowd API.'
)
        parser.add_argument('-user-agent',
                            help = 'Set a custom user agent HTTP header. It can be usefull if you are behind some proxy or firewall. The user agent string.'
)
        multi_args['proxy'] = 4
        parser.add_argument('-proxy',
                            help = 'Specifies an HTTP proxy that the API client library will use to connect to the internet. PROXY must contain 4 values separated by a semicolon. The proxy hostname. The proxy port. The username. The password.'
)
        parser.add_argument('-retry-count',
                            help = 'Specifies the number of retries when the 502 HTTP status code is received. The 502 status code indicates a temporary network issue. This feature can be disabled by setting to 0. Number of retries wanted.'
)


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

        term_error("Invalid source '{}'. Must be valid file, URL or '-'.".format(source))

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
