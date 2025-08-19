import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QFileDialog, QGraphicsView, 
                            QGraphicsScene, QGraphicsPixmapItem, QPushButton, 
                            QMessageBox, QUndoStack, QUndoCommand, QShortcut,
                            QStyle, QFrame, QVBoxLayout, QHBoxLayout, 
                            QSizePolicy, QInputDialog, QDialog, QLabel)  # Added QDialog and QLabel
from PyQt5.QtGui import (QPixmap, QPainter, QPen, QImage, QKeySequence, 
                        QIcon, QTransform)  # Added QTransform
from PyQt5.QtCore import Qt, QPoint
import fitz  # PyMuPDF
from PyQt5.QtWidgets import (QGraphicsItem, QGraphicsTextItem, 
                           QGraphicsPixmapItem, QGraphicsSceneMouseEvent)
from PyQt5.QtCore import QRectF, QPointF

class DrawingArea(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(380, 160)
        # Create transparent canvas
        self.canvas = QPixmap(380, 160)
        self.canvas.fill(Qt.transparent)  # Changed from white to transparent
        self.last_point = None
        self.is_drawing = False

    def paintEvent(self, event):
        painter = QPainter(self)
        # Set white background for display only
        painter.fillRect(self.rect(), Qt.white)
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
        # Convert to ARGB32_Premultiplied for transparency support
        return self.drawing_area.canvas.toImage().convertToFormat(QImage.Format_ARGB32_Premultiplied)

class MovableTextItem(QGraphicsTextItem):
    def __init__(self, text, undo_stack, parent=None):  # Add undo_stack parameter
        super().__init__(text, parent)
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        self.old_pos = self.pos()
        self.undo_stack = undo_stack  # Store undo_stack reference
        
        self.resizing = False
        self.handle_size = 10
        self.min_font_size = 8  # Add minimum font size limit
        
    def boundingRect(self):
        rect = super().boundingRect()
        return rect.adjusted(-self.handle_size/2, -self.handle_size/2, 
                           self.handle_size/2, self.handle_size/2)
    
    def paint(self, painter, option, widget):
        super().paint(painter, option, widget)
        if self.isSelected():
            # Convert float coordinates to integers
            x = int(self.boundingRect().bottomRight().x() - self.handle_size)
            y = int(self.boundingRect().bottomRight().y() - self.handle_size)
            # Draw resize handle with integer coordinates
            painter.drawRect(x, y, self.handle_size, self.handle_size)
    
    def mousePressEvent(self, event: QGraphicsSceneMouseEvent):
        self.old_pos = self.pos()
        if (event.pos().x() > self.boundingRect().right() - self.handle_size and 
            event.pos().y() > self.boundingRect().bottom() - self.handle_size):
            self.resizing = True
        else:
            super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent):
        if self.resizing:
            # Calculate new scale based on mouse movement
            new_size = event.pos().x() / self.boundingRect().width()
            font = self.font()
            new_point_size = int(font.pointSize() * new_size)
            # Enforce minimum size
            if new_point_size >= self.min_font_size:
                font.setPointSize(new_point_size)
                self.setFont(font)
                # Update the scene immediately for smooth visual feedback
                self.scene().update()
        else:
            super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent):
        if self.resizing:
            self.resizing = False
        elif self.pos() != self.old_pos:
            self.undo_stack.push(  # Use stored undo_stack reference
                MoveItemCommand(self, self.old_pos, self.pos())
            )
        super().mouseReleaseEvent(event)

class MovableSignatureItem(QGraphicsPixmapItem):
    def __init__(self, pixmap, undo_stack, parent=None):  # Add undo_stack parameter
        # Convert pixmap to support transparency
        transparent_pixmap = QPixmap.fromImage(
            pixmap.toImage().convertToFormat(QImage.Format_ARGB32_Premultiplied)
        )
        super().__init__(transparent_pixmap, parent)
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        self.old_pos = self.pos()
        self.undo_stack = undo_stack  # Store undo_stack reference
        
        self.resizing = False
        self.handle_size = 10
        self.original_pixmap = transparent_pixmap  # Store transparent version
        self.min_width = 50  # Add minimum width limit
        
    def paint(self, painter, option, widget):
        super().paint(painter, option, widget)
        if self.isSelected():
            # Convert float coordinates to integers
            x = int(self.boundingRect().bottomRight().x() - self.handle_size)
            y = int(self.boundingRect().bottomRight().y() - self.handle_size)
            # Draw resize handle with integer coordinates
            painter.drawRect(x, y, self.handle_size, self.handle_size)
    
    def mousePressEvent(self, event):
        self.old_pos = self.pos()
        if (event.pos().x() > self.boundingRect().right() - self.handle_size and 
            event.pos().y() > self.boundingRect().bottom() - self.handle_size):
            self.resizing = True
        else:
            super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        if self.resizing:
            # Calculate new size maintaining aspect ratio
            new_width = max(self.min_width, event.pos().x())  # Enforce minimum width
            aspect_ratio = self.original_pixmap.height() / self.original_pixmap.width()
            new_height = new_width * aspect_ratio
            
            # Scale the pixmap with high quality
            scaled_pixmap = self.original_pixmap.scaled(
                int(new_width), 
                int(new_height), 
                Qt.KeepAspectRatio, 
                Qt.SmoothTransformation
            )
            self.setPixmap(scaled_pixmap)
            # Update the scene immediately for smooth visual feedback
            self.scene().update()
        else:
            super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        if self.resizing:
            self.resizing = False
        elif self.pos() != self.old_pos:
            self.undo_stack.push(  # Use stored undo_stack reference
                MoveItemCommand(self, self.old_pos, self.pos())
            )
        super().mouseReleaseEvent(event)

class AddItemCommand(QUndoCommand):
    def __init__(self, scene, item):
        super().__init__()
        self.scene = scene
        self.item = item
        self.setText("Add Item")

    def undo(self):
        self.scene.removeItem(self.item)
        self.scene.update()

    def redo(self):
        self.scene.addItem(self.item)
        self.scene.update()

class MoveItemCommand(QUndoCommand):
    def __init__(self, item, old_pos, new_pos):
        super().__init__()
        self.item = item
        self.old_pos = old_pos
        self.new_pos = new_pos
        self.scene = item.scene()  # Get scene reference from item
        self.setText("Move Item")

    def undo(self):
        self.item.setPos(self.old_pos)
        if self.scene:  # Check if scene exists
            self.scene.update()

    def redo(self):
        self.item.setPos(self.new_pos)
        if self.scene:  # Check if scene exists
            self.scene.update()

class PDFEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simple PDF Editor")
        # Convert float values to integers for geometry
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(
            int(screen.width() * 0.1),  # Convert to int
            int(screen.height() * 0.1), # Convert to int
            int(screen.width() * 0.8),  # Convert to int
            int(screen.height() * 0.8)  # Convert to int
        )

        # Create central widget and main layout
        central_widget = QFrame()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Initialize undo stack
        self.undo_stack = QUndoStack(self)

        self.pdf_doc = None
        self.current_page = None
        self.current_page_index = 0
        self.is_drawing = False
        self.last_point = QPoint()

        # PDF display with size policy
        self.view = QGraphicsView(self)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # Hide horizontal scrollbar
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)     # Show vertical scrollbar
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setRenderHint(QPainter.SmoothPixmapTransform)
        # Remove drag mode to disable clicking and dragging on document
        # self.view.setDragMode(QGraphicsView.ScrollHandDrag)  
        self.scene = QGraphicsScene()
        self.view.setScene(self.scene)
        self.view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.view)

        # Button container
        button_container = QFrame()
        button_layout = QHBoxLayout(button_container)
        button_container.setFixedHeight(50)  # Fixed height for buttons
        
        # Buttons in order: Open PDF, Add Text, Sign, Save PDF
        btn_open = QPushButton("Open PDF")
        btn_text = QPushButton("Add Text")
        btn_sign = QPushButton("Sign")
        btn_save = QPushButton("Save PDF")
        
        # Undo/Redo buttons
        btn_undo = QPushButton()
        btn_undo.setIcon(self.style().standardIcon(QStyle.SP_ArrowLeft))
        btn_undo.setText(" Undo")
        btn_undo.setToolTip("Undo (Ctrl+Z)")
        
        btn_redo = QPushButton()
        btn_redo.setIcon(self.style().standardIcon(QStyle.SP_ArrowRight))
        btn_redo.setText(" Redo")
        btn_redo.setToolTip("Redo (Ctrl+Y)")

        # Add buttons to layout with spacing
        button_layout.addWidget(btn_open)
        button_layout.addWidget(btn_text)
        button_layout.addWidget(btn_sign)
        button_layout.addWidget(btn_save)
        button_layout.addStretch()  # Add spacing between main buttons and undo/redo
        button_layout.addWidget(btn_undo)
        button_layout.addWidget(btn_redo)

        # Connect button signals
        btn_open.clicked.connect(self.open_pdf)
        btn_text.clicked.connect(self.add_text_mode)
        btn_sign.clicked.connect(self.sign_mode)
        btn_save.clicked.connect(self.save_pdf)
        btn_undo.clicked.connect(self.undo_stack.undo)
        btn_redo.clicked.connect(self.undo_stack.redo)

        # Add button container to main layout
        layout.addWidget(button_container)

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
        pix = self.current_page.get_pixmap(matrix=fitz.Matrix(2, 2))  # zoom x2 for better quality
        qimage = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimage)
        
        self.scene.clear()
        self.image_item = QGraphicsPixmapItem(pixmap)
        self.scene.addItem(self.image_item)
        self.canvas = QImage(pixmap.size(), QImage.Format_ARGB32_Premultiplied)
        self.canvas.fill(Qt.transparent)
        
        # Set scene rect to match the pixmap size
        self.scene.setSceneRect(self.image_item.boundingRect())
        
        # Don't auto-fit - show at 100% scale
        self.view.setTransform(QTransform())  # Reset any existing transform
        
        # Center the content
        self.view.centerOn(self.image_item)

    def add_text_mode(self):
        self.mode = "text"

    def add_signature_at_position(self, signature, scene_pos):
        """Handle adding signature at the specified position"""
        signature_pixmap = QPixmap.fromImage(signature)
        scaled_signature = signature_pixmap.scaled(200, 100, Qt.KeepAspectRatio, 
                                             Qt.SmoothTransformation)
        
        signature_item = MovableSignatureItem(scaled_signature, self.undo_stack)  # Pass undo_stack
        signature_item.setPos(scene_pos.x() - scaled_signature.width()/2,
                         scene_pos.y() - scaled_signature.height()/2)
        
        self.undo_stack.push(AddItemCommand(self.scene, signature_item))

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
        
        # Convert the mouse position to scene coordinates
        view_pos = self.view.mapFrom(self, event.pos())
        scene_pos = self.view.mapToScene(view_pos)
        
        # Check if click is within the document bounds
        if self.scene.sceneRect().contains(scene_pos):
            # Show text input dialog
            text, ok = QInputDialog.getText(self, 'Add Text', 'Enter text:')
            if ok and text:
                text_item = MovableTextItem(text, self.undo_stack)
                font = text_item.font()
                font.setPointSize(24)
                text_item.setFont(font)
                text_item.setDefaultTextColor(Qt.black)
                text_item.setPos(scene_pos)
                self.undo_stack.push(AddItemCommand(self.scene, text_item))

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

            # Create a new pixmap to render everything
            pixmap = QPixmap(self.scene.sceneRect().size().toSize())
            pixmap.fill(Qt.white)  # Fill with white background
            
            # Create painter for the new pixmap
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            
            # Render the entire scene (including all items) to the pixmap
            self.scene.render(painter)
            painter.end()
            
            # Save as temporary image
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

    # Add resize event handler
    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Only auto-fit if view is smaller than content
        if hasattr(self, 'scene') and self.scene.items():
            viewRect = self.view.viewport().rect()
            sceneRect = self.view.transform().mapRect(self.scene.sceneRect())
            if sceneRect.width() < viewRect.width() and sceneRect.height() < viewRect.height():
                self.view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)

    # Add this new method to handle wheel events
    def wheelEvent(self, event):
        if self.view.verticalScrollBar().isVisible():
            # Convert the delta calculation to an integer
            delta = int(event.angleDelta().y() / 120)
            current_value = self.view.verticalScrollBar().value()
            new_value = current_value - (delta * 30)
            # Ensure the value is an integer
            self.view.verticalScrollBar().setValue(int(new_value))
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PDFEditor()
    window.show()
    sys.exit(app.exec_())
