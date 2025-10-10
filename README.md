# Simple PDF Editor (PyQt5)

A lightweight PDF editor built with **Python** and **PyQt5** that allows users to:

- Open and view PDF files
- Add movable text with custom fonts and sizes
- Draw and insert signatures
- Undo/Redo actions
- Save edited PDF with all annotations

---

<img width="1087" height="679" alt="image" src="https://github.com/user-attachments/assets/bef3da7a-d1d5-44fd-871e-60628221445d" />


## Features

### PDF Handling
- Open any PDF file and view it at high quality (zoom x2)
- Save your annotations as a new PDF

### Text Annotations
- Add movable and resizable text items
- Select font family and font size from the toolbar
- Change font/size of existing text items dynamically

### Signatures
- Draw your signature on a transparent canvas
- Add movable and resizable signatures to the PDF

### Undo/Redo
- Undo or redo any addition or movement of items

### Toolbar Controls
- Font family dropdown (`QFontComboBox`)
- Font size selector (`QSpinBox`, default 14)
- Undo/Redo buttons
- Add Text, Sign, Open PDF, Save PDF buttons

---

## Installation

1. Clone this repository:

```bash
git clone <repository_url>
cd <repository_folder>
Install dependencies (Python 3.9+ recommended):

bash
Copy
Edit
pip install PyQt5 PyMuPDF
Usage
Run the application:

bash
Copy
Edit
python pdf_editor.py
Open a PDF file using the Open PDF button.

To add text:

Click Add Text

Enter the text

Text will appear where you click in the PDF

Adjust font and size using the toolbar

To add a signature:

Click Sign

Draw your signature in the popup dialog

Signature will appear at the cursor position

Use Undo/Redo buttons for action control.

Save the edited PDF with Save PDF button.

Dependencies
PyQt5 – GUI framework

PyMuPDF / fitz – PDF handling library

Screenshots
(Add screenshots here for clarity)

Notes
Text and signatures are movable and resizable directly on the canvas.

Default font size is 14, adjustable via the toolbar.

Signatures support transparent background for overlaying on PDFs.

License
MIT License. Feel free to use and modify this project.

Author
Hagai Aricha – Python / PyQt5 Developer
