all:

dist: dist/pdfcrowd-*.zip dist/pdfcrowd-*.tar.gz

dist/pdfcrowd-*.tar.gz dist/pdfcrowd-*.zip: setup.py pdfcrowd.py
	rm -rf dist/* build/* python/MANIFEST
	python setup.py clean && python setup.py sdist --formats=gztar,zip

test:
	python ./tests.py $(API_USERNAME) $(API_TOKEN) $(API_HOSTNAME) $(API_HTTP_PORT) $(API_HTTPS_PORT)

publish:
	rm -rf dist/* build/* python/MANIFEST
	python setup.py clean && python setup.py sdist upload

init:
	test -d ../test_files/out || mkdir -p ../test_files/out
	test -e test_files || ln -s ../test_files/ test_files

.PHONY: clean
clean:
	rm -rf dist/* build/* python/MANIFEST ./test_files/out/py_client*.pdf
