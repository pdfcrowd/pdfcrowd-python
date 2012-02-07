import pdfcrowd
import os, sys

outstem = os.path.splitext(os.path.basename(sys.argv[0]))[0]
indir = sys.argv[1]
outdir = sys.argv[2]

def test_runner(fn):
    try:
        fn()
    except pdfcrowd.Error, exc:
        print "[FAILED] Pdfcrowd Error:", exc
        sys.exit(1)        
    except RuntimeError, exc:
        print "[FAILED] Runtime Error:", exc
        sys.exit(1)

def get_client():
    def env(var):
        try:
            return os.environ[var]
        except KeyError:
            raise RuntimeError(var + " env var not found")
    username = env('API_USERNAME')
    apikey = env('API_TOKEN')
    hostname = env('API_HOSTNAME')
    return pdfcrowd.Client(username, apikey, hostname)

def out_stream(name):
    return open(os.path.join(outdir, "%s-%s.pdf" % (outstem, name)), 'wb')

def in_data(name):
    return open(os.path.join(indir, name + '.html')).read()

def in_html_url(name):
    return "http://s3.pdfcrowd.com/test/%s.html" % name
