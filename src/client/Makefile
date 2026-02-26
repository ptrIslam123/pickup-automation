.PHONY: build-client clean

build-client: build-client-win

build-client-win:
	rm -rf build-win 2>/dev/null || true
	mkdir build-win
	pyarmor gen *.py
	mv dist/* build-win
	cp requirements.txt run.bat build-win
	rm -rf dist

clean:
	rm -rf build-* 2>/dev/null || true