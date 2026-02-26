zip.exe:
	pyinstaller --onefile zip.py
	mv dist/zip .
	rm -rf dist/ build/ zip.spec

client.zip: zip.exe
	mkdir client.app
	cp *.py run.bat requirements.txt client.app
	./zip zip client.app client.app.zip
	rm -rf client.app
