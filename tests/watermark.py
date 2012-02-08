from pdftools import *

def watermarked_client(x=0, y=0):
    client = get_client()
    client.setWatermark("http://pdfcrowd.com/static/images/logo_transparent_blue.png", x, y)
    client.setHeaderHtml('<div style="text-align:center">Watermarked PDF, %p/%n</div>')
    client.setFooterHtml('<div style="text-align:center">%p/%n</div>')
    return client

def main():
    # default
    client = watermarked_client()
    client.convertHtml(in_data("multipage"), out_stream('simple'))
    # offset
    client = watermarked_client(144,144)
    client.convertHtml(in_data("multipage"), out_stream('offset'))
    # rotate
    client = watermarked_client(144,144)
    client.setWatermarkRotation(45)
    client.convertHtml(in_data("multipage"), out_stream('rotation'))
    # background
    client = watermarked_client(144,144)
    client.setWatermarkInBackground(True)
    client.convertHtml(in_data("multipage"), out_stream('background'))


test_runner(main)
