# Pdfcrowd HTML to PDF API client

The Pdfcrowd API lets you easily create PDF from web pages or raw HTML
code in your Python applications.

To use the API, you need an account on
[http://pdfcrowd.com](https://pdfcrowd.com), if you don't have one you
can sign up [here](https://pdfcrowd.com/pricing/api/). This will give
you a username and an API key.

## Installation

The package can be retrieved from
[pypi](http://pypi.python.org/pypi/pdfcrowd/). You can install it with pip/easy_install:

    pip install pdfcrowd
    
Or you can download/clone the client and run

    git clone git@github.com:pdfcrowd/pdfcrowd-python.git    
    cd pdfcrowd-python/
    python setup.py install

## Example

(don't forget to use your `"username"` and `"apikey"`)

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
    
    except pdfcrowd.Error as why:
        print('Failed: {}'.format(why))
    
## Links

API Home:
 <https://pdfcrowd.com/html-to-pdf-api/>
 
API Reference:
 <https://pdfcrowd.com/web-html-to-pdf-python/>
