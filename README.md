# postocr
Script for post-processing text from OCR machines in libreoffice

### Capabilities (can be disabled by user)
* Strip empty paragraphs
* Strip paragraphs with custom function
* Find and replace footnotes on each page (using custom iterator) as built-in footnote
* Merge paragraphs (if next comes not with an upper letter)
* Keep only basic formatting: bold, italic, underlined
* Replace dash between digits to middle-sized dash
* Replace canonical links like (1 Паралип. 28, 5–7) to (1Пар.28:5–7)
* Convert pre-reform spelling to contemporary
* Change 'е' to 'ё' (yofication) based on dictionary

### Running

* soffice --writer --accept="socket,host=localhost,port=2002;urp;StarOffice.ServiceManager"
* Open a document
* Run script.py

### Current limitations / TODO

* doesn't recognise footnotes continuing on other page
* doesn't reconize links with romanian numbers