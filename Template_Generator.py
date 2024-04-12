import sys
import fitz  # PyMuPDF
import json
from PyQt5.QtWidgets import QApplication, QMainWindow, QGraphicsScene, QGraphicsView, QGraphicsRectItem, QInputDialog, \
    QVBoxLayout, QWidget
from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QGraphicsTextItem, QGraphicsItem, QMenu, QAction
from PyQt5.QtGui import QPen, QColor


class CustomGraphicsView(QGraphicsView):
    Mode = {
        "View": 0,
        "Add": 1,
        "Edit": 2
    }

    def __init__(self, scene):
        super().__init__(scene)
        self.scene = scene
        self.currentMode = self.Mode["Add"]  # Start in Add mode
        self.drawing = False
        self.startPoint = QPointF()
        self.currentRect = None
        self.boxes = {}
        self.setMouseTracking(True)  # Enable mouse tracking

    def setMode(self, mode):
        if mode in self.Mode.values():
            # Change mode and update box appearances
            self.currentMode = mode
            for item in self.scene.items():
                if isinstance(item, InteractiveBox):
                    item.updateAppearanceBasedOnMode(self.currentMode)
        else:
            print("Invalid mode")

    def mousePressEvent(self, event):
        if self.currentMode == self.Mode["Add"] and event.button() == Qt.LeftButton:
            self.drawing = True
            self.startPoint = self.mapToScene(event.pos())
            rect = QRectF(self.startPoint, self.startPoint)
            self.currentRect = InteractiveBox(rect, "")
            self.scene.addItem(self.currentRect)
            event.accept()
        else:
            # In "Edit" mode or "View" mode, let the event propagate to allow selection and interaction.
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.currentMode == self.Mode["Add"] and self.drawing and self.currentRect:
            endPoint = self.mapToScene(event.pos())
            self.currentRect.setRect(QRectF(self.startPoint, endPoint))
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.currentMode == self.Mode["Add"] and self.drawing and self.currentRect:
            self.drawing = False
            self.finalizeBox()
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def finalizeBox(self):
        name, ok = QInputDialog.getText(self, "Box Label", "Enter the box label:")
        if ok and name:
            self.currentRect.label.setPlainText(name)
            self.boxes[name] = self.currentRect  # Save box with its name
        else:
            self.scene.removeItem(self.currentRect)
        self.currentRect = None

    def keyPressEvent(self, event):
        if self.currentMode == self.Mode["Edit"] and event.key() == Qt.Key_Delete:
            for item in self.scene.selectedItems():
                if isinstance(item, InteractiveBox):
                    boxLabel = item.label.toPlainText()
                    if boxLabel in self.boxes:
                        del self.boxes[boxLabel]  # Delete from dictionary
                    self.scene.removeItem(item)  # Remove from scene


class PDFBoxDrawer(QMainWindow):
    def __init__(self, pdf_path, page_number=0):
        super().__init__()
        self.pdf_path = pdf_path
        self.page_number = page_number
        self.initUI()

    def contextMenuEvent(self, event):
        contextMenu = QMenu(self)
        addModeAction = contextMenu.addAction("Add Mode")
        editModeAction = contextMenu.addAction("Edit Mode")
        viewModeAction = contextMenu.addAction("View Mode")

        action = contextMenu.exec_(self.mapToGlobal(event.pos()))

        if action == viewModeAction:
            self.view.setMode(CustomGraphicsView.Mode["View"])
        elif action == editModeAction:
            self.view.setMode(CustomGraphicsView.Mode["Edit"])
        elif action == addModeAction:
            self.view.setMode(CustomGraphicsView.Mode["Add"])

    def addModeButtons(self):
        # Adjusted order to 'Add mode', 'Edit mode', 'View mode'
        addButton = QAction('Add Mode', self)
        addButton.triggered.connect(lambda: self.view.setMode(CustomGraphicsView.Mode["Add"]))
        self.toolbar.addAction(addButton)

        editButton = QAction('Edit Mode', self)
        editButton.triggered.connect(lambda: self.view.setMode(CustomGraphicsView.Mode["Edit"]))
        self.toolbar.addAction(editButton)

        viewButton = QAction('View Mode', self)
        viewButton.triggered.connect(lambda: self.view.setMode(CustomGraphicsView.Mode["View"]))
        self.toolbar.addAction(viewButton)

        saveButton = QAction('Save', self)  # Corrected button label with '&' for shortcut key
        saveButton.triggered.connect(self.save)  # Connect to the method that saves settings and exits
        self.toolbar.addAction(saveButton)

    def save(self):
        # Get the height of the scene to adjust y-coordinates
        scene_height = self.scene.sceneRect().height()
        settings = {}
        for name, box in self.view.boxes.items():
            # Convert Qt's top-left origin to PDF's bottom-left origin
            x1 = box.rect().x()
            y1 = scene_height - (box.rect().y() + box.rect().height())
            x2 = box.rect().width() + x1
            y2 = scene_height - box.rect().y()
            settings[name] = (x1, y1, x2, y2)

        with open('settings.json', 'w') as file:
            json.dump(settings, file, indent=4)
        print("Settings saved to settings.json with adjusted y-coordinates.")

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
        self.label.setPos(rect.topLeft().x() - 5, rect.topLeft().y() - 20)
        self.setAcceptHoverEvents(True)  # Accept hover events
        self.setFlags(
            QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemSendsGeometryChanges)
        self.setBrush(QColor(255, 255, 255, 0))  # Transparent fill
        self.drawing = True
        self.currentRect = QPointF()

        # Pen styles
        self.defaultPen = QPen(QColor(Qt.blue), 2)
        self.hoverPen = QPen(QColor(Qt.yellow), 3)
        self.selectedPen = QPen(QColor(Qt.green), 3)
        self.setPen(self.defaultPen)

    def updateAppearanceBasedOnMode(self, mode):
        # Adjust the appearance based on the mode
        if mode == CustomGraphicsView.Mode["Edit"]:
            self.setPen(self.hoverPen)  # Edit mode might show hover effects
            # Optionally, show resize handles or other indicators
        elif mode == CustomGraphicsView.Mode["View"]:
            self.setPen(self.defaultPen)  # Solid line in View mode, no dashes
            # Optionally, hide resize handles or other indicators
        else:
            self.setPen(self.defaultPen)  # Default appearance otherwise

    def hoverEnterEvent(self, event):
        if self.scene().views()[0].currentMode == CustomGraphicsView.Mode["Edit"]:
            self.setPen(self.hoverPen)

    def hoverLeaveEvent(self, event):
        if self.isSelected():
            self.setPen(self.selectedPen)
        else:
            self.setPen(self.defaultPen)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemSelectedChange:
            self.setPen(self.selectedPen if value else self.defaultPen)
        return super().itemChange(change, value)

    def mousePressEvent(self, event):
        if self.scene().views()[0].currentMode != CustomGraphicsView.Mode["Edit"]:
            event.ignore()
        else:
            super().mousePressEvent(event)

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
        deleteAction = contextMenu.addAction("Delete")
        editAction = contextMenu.addAction("Edit Label")
        action = contextMenu.exec_(event.screenPos())
        if action == deleteAction:
            self.deleteBox()
        elif action == editAction:
            self.editLabel()

    def deleteBox(self):
        # Remove this box from the scene and boxes dictionary
        view = self.scene().views()[0]
        boxLabel = self.label.toPlainText()
        if boxLabel in view.boxes:
            del view.boxes[boxLabel]
        self.scene().removeItem(self)

    def editLabel(self):
        newName, ok = QInputDialog.getText(None, "Edit Label", "Enter new label:", text=self.label.toPlainText())
        if ok:
            self.label.setPlainText(newName)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    pdf_path = r'/Users/lcheng/Downloads/Example.pdf'  # Update this path to your PDF file
    ex = PDFBoxDrawer(pdf_path, page_number=0)
    ex.show()
    sys.exit(app.exec_())