.PHONY: dist
dist:
	@rm -rf dist/* build/* python/MANIFEST
	@python setup.py clean && python setup.py sdist --formats=zip
	@for fname in dist/* ; do mv $$fname "$${fname%.*}-python.$${fname##*.}" ; done

publish:
	@rm -rf dist/* build/* python/MANIFEST
	@python setup.py clean && python setup.py sdist upload

.PHONY: clean
clean:
	rm -rf dist/* build/* python/MANIFEST