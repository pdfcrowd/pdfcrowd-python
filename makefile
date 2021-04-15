.PHONY: dist clean publish test-publish build

dist:
	@rm -rf dist/* build/* python/MANIFEST
	@python setup.py clean && python setup.py sdist --formats=zip
	@for fname in dist/* ; do mv $$fname "$${fname%.*}-python.$${fname##*.}" ; done

# cat ~/.pypirc
# [distutils]
# index-servers =
#  pypi
#  testpypi
#
# [pypi]
# repository=https://upload.pypi.org/legacy/
# username=$username-at-pypi
# password=$password-at-pypi
#
# [testpypi]
# repository=https://test.pypi.org/legacy/
# username=$username-at-testpypi
# password=$password-at-testpypi

build:
	@rm -rf dist/* build/* python/MANIFEST
	@python setup.py clean && python setup.py sdist bdist_wheel

publish: build
	@twine upload dist/*

publish-to-testpypi: build
	@twine upload --repository testpypi dist/*

clean:
	rm -rf dist/* build/* python/MANIFEST
