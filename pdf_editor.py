import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QPushButton
from PyQt5.QtGui import QPixmap, QPainter, QPen, QImage
from PyQt5.QtCore import Qt, QPoint
import fitz  # PyMuPDF
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, 
                            QPushButton, QLabel, QFrame)

class DrawingArea(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(380, 160)
        self.canvas = QPixmap(380, 160)
        self.canvas.fill(Qt.white)
        self.last_point = None
        self.is_drawing = False

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.canvas)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_drawing = True
            self.last_point = event.pos()

    def mouseMoveEvent(self, event):
        if self.is_drawing:  # Removed the event.button() check
            painter = QPainter(self.canvas)
            painter.setPen(QPen(Qt.black, 3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            painter.drawLine(self.last_point, event.pos())
            self.last_point = event.pos()
            painter.end()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_drawing = False

    def clear(self):
        self.canvas.fill(Qt.white)
        self.update()

class SignatureDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Draw Signature")
        self.setFixedSize(400, 200)
        
        layout = QVBoxLayout()
        
        # Create drawing area
        self.drawing_area = DrawingArea()
        self.drawing_area.setFixedSize(380, 160)
        
        # Buttons
        button_layout = QHBoxLayout()
        clear_button = QPushButton("Clear")
        done_button = QPushButton("Done")
        cancel_button = QPushButton("Cancel")
        
        clear_button.clicked.connect(self.drawing_area.clear)
        done_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(clear_button)
        button_layout.addWidget(done_button)
        button_layout.addWidget(cancel_button)
        
        layout.addWidget(QLabel("Draw your signature:"))
        layout.addWidget(self.drawing_area)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)

    def get_signature(self):
        return self.drawing_area.canvas.toImage()

class PDFEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simple PDF Editor")
        self.setGeometry(100, 100, 900, 700)

        self.pdf_doc = None
        self.current_page = None
        self.current_page_index = 0
        self.is_drawing = False
        self.last_point = QPoint()

        # PDF display
        self.view = QGraphicsView(self)
        self.view.setGeometry(50, 50, 800, 550)
        self.scene = QGraphicsScene()
        self.view.setScene(self.scene)

        # Buttons
        btn_open = QPushButton("Open PDF", self)
        btn_open.setGeometry(50, 620, 100, 40)
        btn_open.clicked.connect(self.open_pdf)

        btn_save = QPushButton("Save PDF", self)
        btn_save.setGeometry(160, 620, 100, 40)
        btn_save.clicked.connect(self.save_pdf)

        btn_text = QPushButton("Add Text", self)
        btn_text.setGeometry(270, 620, 100, 40)
        btn_text.clicked.connect(self.add_text_mode)

        btn_sign = QPushButton("Sign", self)
        btn_sign.setGeometry(380, 620, 100, 40)
        btn_sign.clicked.connect(self.sign_mode)

        self.mode = None

    def open_pdf(self):
        file, _ = QFileDialog.getOpenFileName(self, "Open PDF", "", "PDF Files (*.pdf)")
        if file:
            self.pdf_doc = fitz.open(file)
            self.current_page_index = 0
            self.show_page()

    def show_page(self):
        if not self.pdf_doc:
            return
        self.current_page = self.pdf_doc[self.current_page_index]
        pix = self.current_page.get_pixmap(matrix=fitz.Matrix(2, 2))  # zoom x2
        qimage = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimage)
        self.scene.clear()
        self.image_item = QGraphicsPixmapItem(pixmap)
        self.scene.addItem(self.image_item)
        self.canvas = QImage(pixmap.size(), QImage.Format_ARGB32_Premultiplied)
        self.canvas.fill(Qt.transparent)

    def add_text_mode(self):
        self.mode = "text"

    def add_text_at_position(self, scene_pos):
        """Handle adding text at the specified position"""
        from PyQt5.QtWidgets import QInputDialog
        text, ok = QInputDialog.getText(self, 'Add Text', 'Enter text:')
        
        if ok and text:
            temp_pixmap = QPixmap(self.canvas.size())
            temp_pixmap.fill(Qt.transparent)
            
            painter = QPainter(temp_pixmap)
            painter.setPen(QPen(Qt.black, 2))
            font = painter.font()
            font.setPointSize(24)
            painter.setFont(font)
            painter.drawText(int(scene_pos.x()), int(scene_pos.y()), text)
            painter.end()
            
            final_painter = QPainter(self.canvas)
            final_painter.drawPixmap(0, 0, temp_pixmap)
            final_painter.end()
            
            self.update_canvas()

    def add_signature_at_position(self, signature, scene_pos):
        """Handle adding signature at the specified position"""
        painter = QPainter(self.canvas)
        scaled_signature = signature.scaled(200, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        
        x = int(scene_pos.x() - scaled_signature.width() / 2)
        y = int(scene_pos.y() - scaled_signature.height() / 2)
        
        painter.drawImage(x, y, scaled_signature)
        painter.end()
        
        self.update_canvas()

    def sign_mode(self):
        dialog = SignatureDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            signature = dialog.get_signature()
            cursor_pos = self.view.mapFromGlobal(self.cursor().pos())
            scene_pos = self.view.mapToScene(cursor_pos)
            self.add_signature_at_position(signature, scene_pos)

    def mousePressEvent(self, event):
        if not self.scene.items():
            return
        if event.button() == Qt.LeftButton:
            if self.mode == "sign":
                self.is_drawing = True
                self.last_point = event.pos()
            elif self.mode == "text":
                view_pos = self.view.mapFrom(self, event.pos())
                scene_pos = self.view.mapToScene(view_pos)
                self.add_text_at_position(scene_pos)

    def mouseMoveEvent(self, event):
        if self.is_drawing and self.mode == "sign":
            painter = QPainter(self.canvas)
            pen = QPen(Qt.blue, 3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(pen)
            painter.drawLine(self.last_point, event.pos())
            painter.end()
            self.last_point = event.pos()
            self.update_canvas()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.is_drawing:
            self.is_drawing = False

    def update_canvas(self):
        # Create a temporary pixmap with the size of the original PDF
        temp_pixmap = QPixmap(self.image_item.pixmap().size())
        temp_pixmap.fill(Qt.transparent)
        
        # First draw the original PDF
        painter = QPainter(temp_pixmap)
        painter.drawPixmap(0, 0, self.image_item.pixmap())
        
        # Then overlay our annotations (text/signatures)
        painter.drawImage(0, 0, self.canvas)
        painter.end()
        
        # Update the view with combined result
        self.image_item.setPixmap(temp_pixmap)
        self.scene.update()

    def save_pdf(self):
        if not self.pdf_doc:
            return
            
        try:
            # Get save location from user
            file, _ = QFileDialog.getSaveFileName(self, "Save PDF", "", "PDF Files (*.pdf)")
            if not file:
                return

            # Get the current pixmap with all annotations
            pixmap = self.image_item.pixmap()
            
            # Save as temporary image first
            temp_image_path = "temp_image.png"
            pixmap.save(temp_image_path)
            
            # Create a new PDF document
            new_doc = fitz.open()
            
            # Get page dimensions
            width = pixmap.width()
            height = pixmap.height()
            
            # Create a new page
            page = new_doc.new_page(width=width, height=height)
            
            # Insert the image
            rect = page.rect
            page.insert_image(rect, filename=temp_image_path)
            
            # Save and close
            new_doc.save(file)
            new_doc.close()
            
            # Clean up temporary file
            import os
            if os.path.exists(temp_image_path):
                os.remove(temp_image_path)
                
            QMessageBox.information(self, "Success", "PDF saved successfully!")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save PDF: {str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PDFEditor()
    window.show()
    sys.exit(app.exec_())
