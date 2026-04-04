import sys
import os
from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox
from PyQt6.QtGui import QIcon
from dotenv import load_dotenv

# Importación de tus vistas
from views.login_window import LoginWindow
from views.main_window import MainWindow

def main():
    # 1. CARGAR VARIABLES DE ENTORNO
    # Es vital hacerlo aquí para que Supabase y el Mailer Service 
    # funcionen correctamente en todas las ventanas.
    load_dotenv()

    app = QApplication(sys.argv)
    app.setApplicationName("Pegasus ERP")
    
    # 2. CONFIGURACIÓN DE ESTILOS (QSS)
    # Usamos una ruta absoluta basada en la ubicación de este archivo
    base_dir = os.path.dirname(__file__)
    # Apuntamos a assets/styles/styles.qss
    qss_path = os.path.join(base_dir, "assets","styles.qss")
    
    if os.path.exists(qss_path):
        try:
            with open(qss_path, "r", encoding="utf-8") as f:
                app.setStyleSheet(f.read())
        except Exception as e:
            print(f"⚠️ Error al leer el archivo de estilos: {e}")
    else:
        print(f"❌ Archivo no encontrado en: {qss_path}")

    # 3. FLUJO DE ACCESO (LOGIN)
    login = LoginWindow()
    
    # exec() detiene la ejecución aquí hasta que login llame a self.accept() o se cierre
    if login.exec() == QDialog.DialogCode.Accepted:
        
        # Extraemos los datos validados del objeto login
        # Estos datos fueron guardados en el LoginPage justo antes del accept()
        cliente_data = getattr(login, 'cliente_autorizado', None)
        
        # El HWID lo obtenemos a través del método que ya tienes en register_page
        hwid = login.register_page.obtener_hwid()

        if cliente_data:
            # 4. INICIO DE LA VENTANA PRINCIPAL
            # Pasamos los dos argumentos que MainWindow exige (cliente_data y hwid)
            try:
                window = MainWindow(cliente_data, hwid)
                window.show()
                
                # Iniciamos el bucle de eventos de la aplicación
                sys.exit(app.exec())
            except Exception as e:
                QMessageBox.critical(None, "Error Crítico", f"No se pudo iniciar la ventana principal:\n{str(e)}")
                sys.exit(1)
        else:
            QMessageBox.critical(None, "Error de Sesión", "No se pudieron recuperar los datos del usuario.")
            sys.exit(1)
            
    else:
        # Si el usuario cierra el login o falla, salimos limpiamente
        print("Saliendo de Pegasus...")
        sys.exit(0)

if __name__ == "__main__":
    main()