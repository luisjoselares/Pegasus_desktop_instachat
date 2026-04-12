import sys
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtQml import QQmlApplicationEngine
from PyQt6.QtCore import QObject, pyqtSlot

# Esta clase es el "Cerebro" que QML podrá usar
class Backend(QObject):
    @pyqtSlot(str)
    def recibir_click(self, mensaje):
        print(f"✅ ¡Conexión exitosa! Python recibió: {mensaje}")
        # Aquí es donde en el futuro llamaremos a self.ai_service o self.insta_service

if __name__ == "__main__":
    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()

    # Instanciamos el backend
    backend = Backend()
    
    # Inyectamos el backend en QML
    engine.rootContext().setContextProperty("backend", backend)

    # Cargamos el archivo visual
    engine.load("instagram_ui.qml")

    if not engine.rootObjects():
        sys.exit(-1)

    sys.exit(app.exec())