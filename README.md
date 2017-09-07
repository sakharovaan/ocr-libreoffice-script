# ocr-libreoffice-script
Script for post-processing text from OCR machines in libreoffice


### Running

* soffice --writer --accept="socket,host=localhost,port=2002;urp;StarOffice.ServiceManager"
* Open a document
* Run script.py

### Current limitations / TODO

* doesn't recognise footnotes continuing on other page
* recognizes style (B, I, U) only of the whole word
