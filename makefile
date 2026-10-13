.PHONY: dist clean publish publish-to-testpypi build check

PYTHON ?= python3
TWINE ?= twine

dist:
	@$(MAKE) clean
	@$(PYTHON) setup.py sdist --formats=zip
	@for fname in dist/* ; do mv $$fname "$${fname%.*}-python.$${fname##*.}" ; done

# cat ~/.pypirc
# [distutils]
# index-servers =
#  pypi
#  testpypi
#
# [pypi]
# repository=https://upload.pypi.org/legacy/
# username=__token__
# password=$pypi-api-token
#
# [testpypi]
# repository=https://test.pypi.org/legacy/
# username=__token__
# password=$testpypi-api-token

build:
	@$(MAKE) clean
	@$(PYTHON) setup.py sdist bdist_wheel

check: build
	@$(TWINE) check --strict dist/*

publish: check
	@$(TWINE) upload dist/*

publish-to-testpypi: check
	@$(TWINE) upload --repository testpypi dist/*

clean:
	rm -rf dist build *.egg-info MANIFEST
