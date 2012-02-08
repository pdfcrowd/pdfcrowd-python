from pdftools import *

def myclient():
    client = get_client()
    client.setPageWidth("6in")
    client.setPageHeight("6in")
    client.setVerticalMargin("0.5in")
    return client

def main():
    client = myclient()
    client.setHeaderHtml('<i>Logo:</i><img src="http://pdfcrowd.com/static/images/logo_opaque.png">')
    client.convertHtml(in_data("paragraph"), out_stream('headerimg'))
    #
    client = myclient()
    client.setFooterHtml("<i>Footer</i>")
    client.setHeaderHtml("<i>Header</i>")    
    client.convertHtml(in_data("multipage"), out_stream('novars'))
    #
    client = myclient()    
    client.setFooterHtml("<i>Footer %p</i>")
    client.setHeaderHtml("<i>Header %p</i>")    
    client.convertHtml(in_data("multipage"), out_stream('page'))
    #
    client = myclient()    
    client.setFooterHtml("<i>Footer %n</i>")
    client.setHeaderHtml("<i>Header %n</i>")
    client.convertHtml(in_data("multipage"), out_stream('total'))
    #
    client = myclient()    
    client.setFooterHtml("<i>Footer hide:%u</i>")
    client.setHeaderHtml("<i>Header hide:%u</i>")    
    client.convertHtml(in_data("multipage"), out_stream('urlhide'))
    #
    client = myclient()
    client.setFooterHtml("<i>%p/%n</i>")
    client.setHeaderHtml("<i>Source URL: %u</i>")
    client.convertURI(in_html_url('multipage'), out_stream('url'))
    #
    client = myclient()
    client.setHeaderHtml('<div style="text-align:center">page %p - header excluded from the 1st and the last page</div>')
    client.setPageNumberingOffset(1)
    client.setHeaderFooterPageExcludeList("1,-1")
    client.convertHtml(in_data("multipage"), out_stream('covers'))
    #
    client = myclient()
    client.setHeaderHtml("%p/%n")
    client.setPageNumberingOffset(1)
    client.convertHtml(in_data("multipage"), out_stream('numbering_offset'))
    #
    client = myclient()
    client.setHeaderUrl("http://pdfcrowd.com/hub/random/header.html")
    client.setFooterUrl("http://pdfcrowd.com/hub/random/footer.html")
    client.convertHtml(in_data("multipage"), out_stream('fromurl'))    
    #
    client = myclient()
    client.setHeaderHtml('<div style="padding-top:0"><a href="http://seznam.cz">here</a></div>')    
    client.convertHtml(in_data("paragraph"), out_stream('exturl'))
    #
    client = myclient()
    client.setHorizontalMargin(0)
    client.setHeaderHtml('<div style="margin-left:-20px;"><a href="http://seznam.cz">here is a negative link</a></div>')    
    client.convertHtml(in_data("paragraph"), out_stream('neglink'))

test_runner(main)
