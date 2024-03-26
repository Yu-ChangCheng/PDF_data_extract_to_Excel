import sys
import fitz  # PyMuPDF
from PyQt5.QtWidgets import QApplication, QMainWindow, QGraphicsScene, QGraphicsView, QGraphicsRectItem, QInputDialog, QVBoxLayout, QWidget
from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QGraphicsTextItem, QGraphicsItem, QMenu, QAction
from PyQt5.QtGui import QPen, QColor

class CustomGraphicsView(QGraphicsView):
    Mode = {
        "View": 0,
        "Edit": 1,
        "Add": 2
    }
    
    def __init__(self, scene):
        super().__init__(scene)
        self.scene = scene
        self.currentMode = self.Mode["View"]  # Default mode
        self.drawing = False
        self.startPoint = QPointF()
        self.currentRect = None
        self.boxes = {}  # Stores boxes with labels
    
    def setMode(self, mode):
        if mode in self.Mode.values():
            self.currentMode = mode
        else:
            print("Invalid mode")
    
    def mousePressEvent(self, event):
        super().mousePressEvent(event)  # Ensures selection works in all modes
        if self.currentMode == self.Mode["Add"]:
            if event.button() == Qt.LeftButton:
                self.drawing = True
                self.startPoint = self.mapToScene(event.pos())
                self.currentRect = InteractiveBox(QRectF(self.startPoint, self.startPoint), "")
                self.scene.addItem(self.currentRect)
                event.accept()
        elif self.currentMode == self.Mode["Edit"]:
            # Maybe prepare for moving or resizing, but do not start drawing new boxes
            pass

    def mouseMoveEvent(self, event):
        if self.currentMode == self.Mode["Add"] and self.drawing and self.currentRect:
            endPoint = self.mapToScene(event.pos())
            self.currentRect.setRect(QRectF(self.startPoint, endPoint).normalized())
            event.accept()
        elif self.currentMode == self.Mode["Edit"]:
            # Handle resizing or moving the selected box if needed
            pass

    def mouseReleaseEvent(self, event):
        if self.currentMode == self.Mode["Add"] and self.drawing and self.currentRect:
            self.drawing = False
            self.finalizeBox()
            event.accept()
        elif self.currentMode == self.Mode["Edit"]:
            # Finalize any move or resize actions
            pass

    def finalizeBox(self):
        name, ok = QInputDialog.getText(self, "Box Label", "Enter the box label:")
        if ok and name:
            rect = self.currentRect.rect()
            # Replace the temporary rectangle with an InteractiveBox
            self.scene.removeItem(self.currentRect)
            interactiveBox = InteractiveBox(rect, name)
            self.scene.addItem(interactiveBox)
            self.boxes[name] = interactiveBox
            print(f"Box '{name}' saved with coordinates: {rect}")
        else:
            self.scene.removeItem(self.currentRect)
        self.currentRect = None

class PDFBoxDrawer(QMainWindow):
    def __init__(self, pdf_path, page_number=0):
        super().__init__()
        self.pdf_path = pdf_path
        self.page_number = page_number
        self.initUI()
    
    def contextMenuEvent(self, event):
       contextMenu = QMenu(self)
       viewModeAction = contextMenu.addAction("View Mode")
       editModeAction = contextMenu.addAction("Edit Mode")
       addModeAction = contextMenu.addAction("Add Mode")
       
       action = contextMenu.exec_(self.mapToGlobal(event.pos()))
       
       if action == viewModeAction:
           self.view.setMode(CustomGraphicsView.Mode["View"])
       elif action == editModeAction:
           self.view.setMode(CustomGraphicsView.Mode["Edit"])
       elif action == addModeAction:
           self.view.setMode(CustomGraphicsView.Mode["Add"])
    
    def addModeButtons(self):
        viewButton = QAction('View Mode', self)
        viewButton.triggered.connect(lambda: self.view.setMode(CustomGraphicsView.Mode["View"]))
        self.toolbar.addAction(viewButton)

        editButton = QAction('Edit Mode', self)
        editButton.triggered.connect(lambda: self.view.setMode(CustomGraphicsView.Mode["Edit"]))
        self.toolbar.addAction(editButton)

        addButton = QAction('Add Mode', self)
        addButton.triggered.connect(lambda: self.view.setMode(CustomGraphicsView.Mode["Add"]))
        self.toolbar.addAction(addButton)
    
    def initUI(self):
        # Initialize the scene and view as before
        self.scene = QGraphicsScene()
        self.view = CustomGraphicsView(self.scene)
        self.loadPDFPage(self.pdf_path, self.page_number)

        # Toolbar for mode switching
        self.toolbar = self.addToolBar('Modes')
        self.addModeButtons()

        # Layout setup
        layout = QVBoxLayout()
        layout.addWidget(self.view)  # Add the view to the layout

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def loadPDFPage(self, pdf_path, page_number):
        doc = fitz.open(pdf_path)
        page = doc.load_page(page_number)
        pix = page.get_pixmap()
        img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(img)
        self.scene.addPixmap(pixmap)
        self.scene.setSceneRect(0, 0, pixmap.width(), pixmap.height())

        # Display text bounding boxes from the PDF
        for text_instance in page.get_text("dict")["blocks"]:
            if "lines" in text_instance:  # Check if the block contains lines of text
                for line in text_instance["lines"]:
                    for span in line["spans"]:  # Each 'span' contains a piece of text
                        x0, y0, x1, y1 = span["bbox"]
                        rect = QRectF(x0, y0, x1 - x0, y1 - y0)
                        pen = QPen(QColor(Qt.red))  # Create a red pen
                        self.scene.addRect(rect, pen=pen)

class InteractiveBox(QGraphicsRectItem):
    def __init__(self, rect, label, *args, **kwargs):
        super().__init__(rect, *args, **kwargs)
        self.label = QGraphicsTextItem(label, self)
        self.label.setPos(rect.topLeft().x(), rect.topLeft().y() - 16)
        self.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemSendsGeometryChanges)
        self.setBrush(QColor(255, 255, 255, 0))  # Transparent fill
        self.setPen(QPen(QColor(Qt.blue), 2))  # Blue outline for unselected state
        self.selectedPen = QPen(QColor(Qt.green), 3)  # Green outline for selected state
        self.unselectedPen = QPen(QColor(Qt.blue), 2)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemSelectedChange:
            self.setPen(self.selectedPen if value else self.unselectedPen)
        return super().itemChange(change, value)
    
    def mousePressEvent(self, event):
        super().mousePressEvent(event)  # Call the parent method to handle item selection
        if event.button() == Qt.LeftButton:
            item = self.itemAt(event.pos())
            if isinstance(item, InteractiveBox):
                # Item is a selected box, potentially handle resizing or moving here
                print(f"Selected Box: {item.label}")
            else:
                self.drawing = True
                self.startPoint = self.mapToScene(event.pos())
                self.currentRect = InteractiveBox(QRectF(self.startPoint, self.startPoint), "Label")
                self.scene.addItem(self.currentRect)
                event.accept()

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)  # Ensure item movement is handled
        if self.drawing and self.currentRect:
            endPoint = self.mapToScene(event.pos())
            self.currentRect.setRect(QRectF(self.startPoint, endPoint).normalized())
            event.accept()
        
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.drawing and self.currentRect:
            self.drawing = False
            self.finalizeBox()
            event.accept()
    
    def contextMenuEvent(self, event):
        contextMenu = QMenu()
        editAction = contextMenu.addAction("Edit Label")
        action = contextMenu.exec_(event.screenPos())
        if action == editAction:
            self.editLabel()

    def editLabel(self):
        newName, ok = QInputDialog.getText(None, "Edit Label", "Enter new label:", text=self.label.toPlainText())
        if ok:
            self.label.setPlainText(newName)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    pdf_path = r'C:\Users\lcheng\Downloads\MPD 2.pdf'  # Update this path to your PDF file
    ex = PDFBoxDrawer(pdf_path, page_number=0)
    ex.show()
    sys.exit(app.exec_())
