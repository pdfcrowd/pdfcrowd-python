from pdftools import *

def main():
    client = get_client()
    client.setPageBackgroundColor("eeffdd")
    client.convertHtml(in_data("paragraph"), out_stream('no-transparent1'))
    # -
    client = get_client()
    client.setPageBackgroundColor("eeffdd")
    client.setTransparentBackground(False)
    client.convertHtml(in_data("paragraph"), out_stream('no-transparent2'))
    # - 
    client = get_client()
    client.setPageBackgroundColor("eeffdd")
    client.setTransparentBackground(True)
    client.convertHtml(in_data("paragraph"), out_stream('transparent'))

test_runner(main)
