all:

dist: dist/pdfcrowd-*.zip dist/pdfcrowd-*.tar.gz

dist/pdfcrowd-*.tar.gz dist/pdfcrowd-*.zip: setup.py pdfcrowd.py
	grep "__version__ = \""`grep -oE "version='[0-9.]+" setup.py | sed "s/version='//"` pdfcrowd.py > /dev/null
	rm -rf dist/* build/* python/MANIFEST
	python setup.py clean && python setup.py sdist --formats=gztar,zip

test:
	python ./tests.py $(API_USERNAME) $(API_TOKEN) $(API_HOSTNAME) $(API_HTTP_PORT) $(API_HTTPS_PORT)

publish:
	rm -rf dist/* build/* python/MANIFEST
	python setup.py clean && python setup.py sdist upload

.PHONY: clean
clean:
	rm -rf dist/* build/* python/MANIFEST

