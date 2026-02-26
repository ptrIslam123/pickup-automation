.PHONY: build-client clean

build-client:
	rm -rf build 2>/dev/null || true
	mkdir build
	pyarmor gen *.py
	mv dist/* build
	cp requirements.txt run.bat build
	rm -rf dist

clean:
	rm -rf build 2>/dev/null || true