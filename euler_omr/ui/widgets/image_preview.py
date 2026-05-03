"""Zoomable/pannable QGraphicsView for template PDF preview."""
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
from PySide6.QtGui import QPixmap, QImage, QWheelEvent
from PySide6.QtCore import Qt
import numpy as np


class ImagePreview(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self._pixmap_item = None
        self._zoom = 1.0
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setRenderHint(self.renderHints())
        self.setStyleSheet("QGraphicsView { background-color: #052221; border: 1px solid #385550; }")
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Placeholder
        self._show_placeholder()

    def _show_placeholder(self):
        self._scene.clear()
        text = self._scene.addText("No preview available\n\nCompile a template to see the PDF preview here")
        text.setDefaultTextColor(Qt.GlobalColor.gray)

    def set_image_from_bytes(self, data: bytes, fmt: str = "PNG"):
        img = QImage()
        img.loadFromData(data, fmt)
        if img.isNull():
            return
        pixmap = QPixmap.fromImage(img)
        self._scene.clear()
        self._pixmap_item = self._scene.addPixmap(pixmap)
        self.setSceneRect(pixmap.rect().toRectF())
        self.fitInView(self._pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)
        self._zoom = 1.0

    def set_pixmap(self, pixmap: QPixmap):
        self._scene.clear()
        self._pixmap_item = self._scene.addPixmap(pixmap)
        self.setSceneRect(pixmap.rect().toRectF())
        self.fitInView(self._pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)
        self._zoom = 1.0

    def set_pdf_preview(self, pdf_bytes: bytes):
        """Render first page of PDF bytes as preview."""
        try:
            import pypdfium2 as pdfium
            doc = pdfium.PdfDocument(pdf_bytes)
            page = doc[0]
            bitmap = page.render(scale=2.0)
            img_np = bitmap.to_numpy()
            doc.close()
            h, w = img_np.shape[:2]
            ch = img_np.shape[2] if len(img_np.shape) > 2 else 1
            if ch == 4:
                qimg = QImage(img_np.data, w, h, w * 4, QImage.Format.Format_RGBA8888)
            else:
                qimg = QImage(img_np.data, w, h, w * 3, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(qimg.copy())
            self.set_pixmap(pixmap)
        except Exception:
            self._show_placeholder()

    def wheelEvent(self, event: QWheelEvent):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self._zoom *= factor
        self.scale(factor, factor)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._pixmap_item:
            self.fitInView(self._pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)
