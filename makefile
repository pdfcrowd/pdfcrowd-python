.PHONY: dist
dist:
	@rm -rf dist/* build/* python/MANIFEST
	@python setup.py clean && python setup.py sdist --formats=zip
	@for fname in dist/* ; do mv $$fname "$${fname%.*}-python.$${fname##*.}" ; done

# cat ~/.pypirc
# [distutils]
# index-servers =
#  pypi
# 
# [pypi]
# repository=https://upload.pypi.org/legacy/
# username=$username-at-pypi
# password=$password-at-pypi
publish:
	@rm -rf dist/* build/* python/MANIFEST
	@python setup.py clean && python setup.py sdist
	@twine upload dist/*

.PHONY: clean
clean:
	rm -rf dist/* build/* python/MANIFEST
