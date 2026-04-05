import csv
import csv
import importlib
import qtawesome as qta
from PyQt6.QtWidgets import (
    QDialog,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QComboBox,
    QTimeEdit,
    QStackedWidget,
    QWidget,
    QFileDialog,
)
from PyQt6.QtGui import QTransform
from PyQt6.QtCore import Qt, QTime, QThread, pyqtSignal, QTimer
from services.instagram_service import InstagramService


class LoginWorker(QThread):
    finished = pyqtSignal(bool, str)

    def __init__(self, service, username, password):
        super().__init__()
        self.service = service
        self.username = username
        self.password = password

    def run(self):
        if self.isInterruptionRequested():
            self.finished.emit(False, "Login cancelado.")
            return
        try:
            success = self.service.login(self.username, self.password)
            self.finished.emit(success, "" if success else "No se pudo validar la cuenta.")
        except Exception as e:
            self.finished.emit(False, str(e))


class ProfileScanWorker(QThread):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, service, username):
        super().__init__()
        self.service = service
        self.username = username

    def run(self):
        if self.isInterruptionRequested():
            self.finished.emit(None)
            return
        try:
            profile = self.service.analyze_profile(self.username)
            self.finished.emit(profile)
        except Exception as e:
            self.error.emit(str(e))


class AddAccountDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuración de Agente Pegasus")
        self.setFixedWidth(620)
        self.setObjectName("ModernDialog")

        self.insta_service = InstagramService()
        self.login_worker = None
        self.profile_worker = None
        self.csv_path = ""
        self.inventory_connected = False
        self.inventory_headers = []
        self.inventory_rows = 0
        self.inventory_type = ""
        self.inventory_headers = []
        self.inventory_rows = 0

        self.setStyleSheet("""
            QDialog#ModernDialog { background-color: #0A0A0A; }
            QLabel { color: #FFFFFF; font-size: 12px; font-weight: bold; }
            QLineEdit, QTextEdit, QComboBox, QTimeEdit {
                background-color: #161616;
                color: #FFFFFF;
                border: 1px solid #333;
                padding: 10px;
                border-radius: 6px;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QTimeEdit:focus {
                border: 1px solid #00E5FF;
            }
            QPushButton {
                background-color: #1A1A1A;
                color: white;
                border: 1px solid #333;
                padding: 10px 18px;
                border-radius: 6px;
            }
            QPushButton:hover {
                border: 1px solid #00E5FF;
            }
            QTextEdit#PromptArea {
                background-color: #121212;
                border: 1px solid #00E5FF;
            }
        """)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(30, 30, 30, 30)
        self.layout.setSpacing(16)

        self.title = QLabel("CONFIGURAR AGENTE DE TIENDA")
        self.title.setStyleSheet("font-size: 20px; font-weight: 900; color: #00E5FF;")
        self.layout.addWidget(self.title, alignment=Qt.AlignmentFlag.AlignCenter)

        self.stacked = QStackedWidget()
        self.page1 = QWidget()
        self.page2 = QWidget()
        self.page3 = QWidget()
        self.page4 = QWidget()

        self._build_page1()
        self._build_page2()
        self._build_page3()
        self._build_page4()

        self.stacked.addWidget(self.page1)
        self.stacked.addWidget(self.page2)
        self.stacked.addWidget(self.page3)
        self.stacked.addWidget(self.page4)
        self.stacked.currentChanged.connect(self.on_page_changed)

        self.layout.addWidget(self.stacked)
        self._create_loading_overlay()
        self.update_role_logic()

    def _create_loading_overlay(self):
        self.loading_overlay = QWidget(self)
        self.loading_overlay.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.loading_overlay.setStyleSheet("background-color: rgba(0, 0, 0, 0);")
        overlay_layout = QVBoxLayout(self.loading_overlay)
        overlay_layout.setContentsMargins(0, 0, 0, 0)
        overlay_layout.setSpacing(12)
        overlay_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.spinner_label = QLabel()
        self.spinner_label.setFixedSize(48, 48)
        self.spinner_label.setScaledContents(True)
        self.spinner_label.setStyleSheet("background: transparent;")
        self.spinner_pixmap = qta.icon('fa5s.spinner', color='#00E5FF').pixmap(48, 48)
        self.spinner_label.setPixmap(self.spinner_pixmap)
        overlay_layout.addWidget(self.spinner_label, alignment=Qt.AlignmentFlag.AlignCenter)

        self.spinner_text = QLabel("Procesando...")
        self.spinner_text.setStyleSheet("color: #FFFFFF; font-size: 14px; background: transparent;")
        overlay_layout.addWidget(self.spinner_text, alignment=Qt.AlignmentFlag.AlignCenter)

        self.loading_overlay.hide()
        self.spinner_timer = QTimer(self)
        self.spinner_timer.timeout.connect(self._rotate_spinner)
        self.spinner_timer.setInterval(120)
        self.spinner_angle = 0

    def _rotate_spinner(self):
        self.spinner_angle = (self.spinner_angle + 12) % 360
        transform = QTransform().rotate(self.spinner_angle)
        rotated = self.spinner_pixmap.transformed(transform, Qt.TransformationMode.SmoothTransformation)
        rotated = rotated.scaled(self.spinner_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.spinner_label.setPixmap(rotated)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.loading_overlay.setGeometry(self.rect())

    def _build_page1(self):
        layout = QVBoxLayout(self.page1)
        layout.setSpacing(14)

        layout.addWidget(QLabel("PASO 1: CONEXIÓN"))
        layout.addWidget(QLabel("Login de Instagram para iniciar el asistente sin bloquear la UI."))

        layout.addWidget(QLabel("USUARIO DE INSTAGRAM"))
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("@usuario_tienda")
        layout.addWidget(self.user_input)

        layout.addWidget(QLabel("CONTRASEÑA"))
        self.pass_input = QLineEdit()
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass_input.setPlaceholderText("Contraseña de Instagram")
        layout.addWidget(self.pass_input)

        self.page1_status = QLabel("Introduce tus credenciales y valida para continuar.")
        self.page1_status.setStyleSheet("color: #00E5FF;")
        layout.addWidget(self.page1_status)

        button_row = QHBoxLayout()
        self.btn_validate = QPushButton(qta.icon('fa5s.check', color='#00E5FF'), "VALIDAR Y CONTINUAR")
        self.btn_validate.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_validate.clicked.connect(self.validate_credentials)
        button_row.addStretch()
        button_row.addWidget(self.btn_validate)
        layout.addLayout(button_row)

    def _build_page2(self):
        layout = QVBoxLayout(self.page2)
        layout.setSpacing(14)

        layout.addWidget(QLabel("PASO 2: IDENTIDAD"))
        layout.addWidget(QLabel("Escaneo de perfil para autorrellenar Nombre de Tienda y ADN/Bio."))

        layout.addWidget(QLabel("NOMBRE DE LA TIENDA"))
        self.store_input = QLineEdit()
        self.store_input.setPlaceholderText("Tienda detectada automáticamente")
        layout.addWidget(self.store_input)

        layout.addWidget(QLabel("ADN / BIO"))
        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("Biografía y ADN de la tienda")
        self.description_input.setMinimumHeight(120)
        layout.addWidget(self.description_input)

        self.page2_status = QLabel("En la siguiente fase se completará el escaneo automático de perfil.")
        self.page2_status.setStyleSheet("color: #00E5FF;")
        layout.addWidget(self.page2_status)

        nav = QHBoxLayout()
        self.btn_prev2 = QPushButton("ATRÁS")
        self.btn_prev2.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_prev2.clicked.connect(self.prev_step)
        self.btn_next2 = QPushButton("SIGUIENTE")
        self.btn_next2.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_next2.clicked.connect(self.next_step)
        self.btn_next2.setEnabled(False)
        nav.addWidget(self.btn_prev2)
        nav.addStretch()
        nav.addWidget(self.btn_next2)
        layout.addLayout(nav)

    def _build_page3(self):
        layout = QVBoxLayout(self.page3)
        layout.setSpacing(14)

        layout.addWidget(QLabel("PASO 3: INVENTARIO"))
        layout.addWidget(QLabel("Elige si quieres cargar un inventario CSV o continuar sin inventario."))

        cards = QHBoxLayout()
        cards.setSpacing(16)

        self.btn_load_csv = QPushButton(qta.icon('fa5s.file-upload', color='#00E5FF'), "Cargar Inventario")
        self.btn_load_csv.setObjectName("InventoryLoadButton")
        self.btn_load_csv.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_load_csv.setMinimumHeight(120)
        self.btn_load_csv.setStyleSheet(
            "QPushButton#InventoryLoadButton { text-align: left; padding: 18px; font-size: 14px; border-radius: 10px; background-color: #121212; border: 1px solid #00E5FF; }"
            "QPushButton#InventoryLoadButton:hover { background-color: #1A1A1A; }"
        )
        self.btn_load_csv.clicked.connect(self.browse_inventory_file)
        cards.addWidget(self.btn_load_csv)

        layout.addLayout(cards)

        self.page3_status = QLabel("Si no subes inventario, el botón siguiente seguirá adelante sin inventario.")
        self.page3_status.setStyleSheet("color: #00E5FF;")
        layout.addWidget(self.page3_status)

        self.inventory_summary = QLabel("No se ha cargado inventario todavía.")
        self.inventory_summary.setWordWrap(True)
        self.inventory_summary.setStyleSheet("color: #FFFFFF; border: 1px solid #333; padding: 12px; border-radius: 8px; background-color: #121212;")
        layout.addWidget(self.inventory_summary)

        nav = QHBoxLayout()
        self.btn_prev3 = QPushButton("ATRÁS")
        self.btn_prev3.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_prev3.clicked.connect(self.prev_step)
        self.btn_next3 = QPushButton("CONTINUAR SIN INVENTARIO")
        self.btn_next3.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_next3.clicked.connect(self.next_step)
        self.btn_next3.setEnabled(False)
        nav.addWidget(self.btn_prev3)
        nav.addStretch()
        nav.addWidget(self.btn_next3)
        layout.addLayout(nav)

    def _build_page4(self):
        layout = QVBoxLayout(self.page4)
        layout.setSpacing(14)

        layout.addWidget(QLabel("PASO 4: CONFIGURACIÓN"))
        layout.addWidget(QLabel("Selecciona el rol, el horario y revisa el system prompt generado."))

        self.schedule_notice = QLabel(
            "Recomendado: establece un periodo de trabajo de 8 a 12 horas y evita configurar 24 horas continuas para reducir el riesgo de sanciones de la plataforma."
        )
        self.schedule_notice.setWordWrap(True)
        self.schedule_notice.setStyleSheet(
            "color: #FFB300; background-color: #1F1F2B; border: 1px solid #FFB300; padding: 12px; border-radius: 8px;"
        )
        layout.addWidget(self.schedule_notice)

        layout.addWidget(QLabel("ROL DEL AGENTE"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Encargado de tienda", "Atención General", "Personalizado"])
        self.type_combo.currentTextChanged.connect(self.update_role_logic)
        layout.addWidget(self.type_combo)

        row = QHBoxLayout()
        v_time = QVBoxLayout()
        v_time.addWidget(QLabel("HORARIO DE ATENCIÓN (24h)"))
        h_time_inner = QHBoxLayout()
        self.start_time = QTimeEdit(QTime(8, 0))
        self.start_time.setDisplayFormat("HH:mm")
        self.end_time = QTimeEdit(QTime(18, 0))
        self.end_time.setDisplayFormat("HH:mm")
        self.start_time.timeChanged.connect(self.update_role_logic)
        self.end_time.timeChanged.connect(self.update_role_logic)
        h_time_inner.addWidget(self.start_time)
        h_time_inner.addWidget(QLabel("-"))
        h_time_inner.addWidget(self.end_time)
        v_time.addLayout(h_time_inner)
        row.addLayout(v_time)
        layout.addLayout(row)

        self.schedule_hint = QLabel("Ejemplo: 05:00 - 06:00. El horario se guarda en formato 24h.")
        self.schedule_hint.setStyleSheet("color: #BBBBBB; font-size: 11px; margin-top: 6px;")
        v_time.addWidget(self.schedule_hint)

        self.schedule_warning = QLabel("")
        self.schedule_warning.setStyleSheet("color: #FF5E00; font-size: 12px;")
        layout.addWidget(self.schedule_warning)

        layout.addWidget(QLabel("SYSTEM PROMPT"))
        self.context_input = QTextEdit()
        self.context_input.setObjectName("PromptArea")
        self.context_input.setReadOnly(True)
        self.context_input.setMinimumHeight(160)
        layout.addWidget(self.context_input)
        layout.addStretch()

        nav = QHBoxLayout()
        self.btn_prev4 = QPushButton("ATRÁS")
        self.btn_prev4.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_prev4.clicked.connect(self.prev_step)
        self.btn_finish = QPushButton(qta.icon('fa5s.check-circle', color='#00E5FF'), "FINALIZAR")
        self.btn_finish.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_finish.clicked.connect(self.finish_and_save)
        nav.addWidget(self.btn_prev4)
        nav.addStretch()
        nav.addWidget(self.btn_finish)
        layout.addLayout(nav)

    def on_page_changed(self, index):
        if index == 1:
            self.page2_status.setText("Preparando la identidad de la tienda...")
        elif index == 2:
            self.page3_status.setText("Elige tu flujo de inventario o continúa sin inventario.")
            self._update_inventory_button_text()
        elif index == 3:
            self.update_role_logic()

    def next_step(self):
        current = self.stacked.currentIndex()
        if current < self.stacked.count() - 1:
            self.stacked.setCurrentIndex(current + 1)

    def prev_step(self):
        current = self.stacked.currentIndex()
        if current > 0:
            self.stacked.setCurrentIndex(current - 1)

    def validate_credentials(self):
        user = self.user_input.text().strip()
        password = self.pass_input.text().strip()
        if not user or not password:
            self.page1_status.setText("Usuario y contraseña son obligatorios.")
            return
        self.page1_status.setText("Validando credenciales...")
        self.show_loading("Validando Instagram...")
        self.btn_validate.setEnabled(False)

        self.login_worker = LoginWorker(self.insta_service, user, password)
        self.login_worker.finished.connect(self.on_login_finished)
        self.login_worker.start()

    def on_login_finished(self, success, message):
        self.hide_loading()
        self.btn_validate.setEnabled(True)
        if success:
            self.page1_status.setText("Cuenta validada. Avanzando...")
            self.stacked.setCurrentIndex(1)
            self.page2_status.setText("Escaneando perfil automáticamente...")
            self.btn_next2.setEnabled(False)
            self.start_profile_scan()
        else:
            self.page1_status.setText(message)

    def closeEvent(self, event):
        if self.login_worker and self.login_worker.isRunning():
            self.login_worker.requestInterruption()
            self.login_worker.quit()
            self.login_worker.wait(500)
        if self.profile_worker and self.profile_worker.isRunning():
            self.profile_worker.requestInterruption()
            self.profile_worker.quit()
            self.profile_worker.wait(500)
        super().closeEvent(event)

    def start_profile_scan(self):
        username = self.user_input.text().strip().lstrip('@')
        if not username:
            self.page2_status.setText("Debes validar el usuario antes de escanear.")
            self.btn_next2.setEnabled(True)
            return

        self.page2_status.setText("Escaneando perfil de Instagram...")
        self.show_loading("Escaneando perfil...")
        self.profile_worker = ProfileScanWorker(self.insta_service, username)
        self.profile_worker.finished.connect(self.on_profile_scan_finished)
        self.profile_worker.error.connect(self.on_profile_scan_error)
        self.profile_worker.start()

    def on_profile_scan_finished(self, profile):
        self.hide_loading()
        self.btn_next2.setEnabled(True)
        if not profile:
            self.page2_status.setText("No se pudo obtener el perfil. Completa la información manualmente.")
            return
        self.store_input.setText(profile.get('full_name') or self.store_input.text())
        description = (
            f"{profile.get('category_name') or 'Tienda General'}\n"
            f"{profile.get('biography') or 'Sin biografía disponible.'}"
        )
        if profile.get('recent_captions'):
            description += "\n\n" + "\n".join(profile.get('recent_captions'))
        self.description_input.setPlainText(description)
        self.page2_status.setText("Identidad cargada. Revisa y pulsa Siguiente.")

    def on_profile_scan_error(self, message):
        self.hide_loading()
        self.btn_next2.setEnabled(True)
        self.page2_status.setText(f"Error al escanear el perfil: {message}")

    def browse_inventory_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar inventario",
            "",
            "CSV Files (*.csv);;Excel Files (*.xlsx *.xls);;Todos los archivos (*.*)",
        )
        if path:
            self.csv_path = path
            self.inventory_connected = True
            self._analyze_inventory_file(path)

    def _update_inventory_button_text(self):
        if self.inventory_connected:
            self.btn_next3.setText("SIGUIENTE")
        else:
            self.btn_next3.setText("CONTINUAR SIN INVENTARIO")

    def _analyze_inventory_file(self, path):
        try:
            lower = path.lower()
            if lower.endswith('.csv'):
                headers, rows = self._read_csv(path)
                self.inventory_type = 'CSV'
            elif lower.endswith('.xlsx') or lower.endswith('.xls'):
                headers, rows = self._read_excel(path)
                self.inventory_type = 'Excel'
            else:
                raise ValueError('Formato no soportado. Usa CSV, XLSX o XLS.')

            self.inventory_headers = headers
            self.inventory_rows = len(rows)
            file_name = path.replace('\\', '/').split('/')[-1]
            self.inventory_summary.setText(
                f"✅ {self.inventory_type} detectado con éxito.\n"
                f"- Productos detectados: {self.inventory_rows}\n"
                f"- Columnas encontradas: {', '.join(self.inventory_headers) if self.inventory_headers else 'Ninguna'}"
            )
            self.page3_status.setText("Inventario analizado. Ya puedes continuar.")
            self._update_inventory_button_text()
            self.btn_next3.setEnabled(True)
        except Exception as e:
            self.inventory_connected = False
            self.inventory_headers = []
            self.inventory_rows = 0
            self.inventory_summary.setText(f"Error al analizar el archivo: {e}")
            self.page3_status.setText("No se pudo analizar el archivo. Intenta con otro inventario.")
            self.btn_next3.setEnabled(False)

    def _read_csv(self, path):
        with open(path, newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            headers = next(reader, [])
            rows = [row for row in reader if any(cell.strip() for cell in row)]
        return headers, rows

    def _read_excel(self, path):
        try:
            pd = importlib.import_module('pandas')
            df = pd.read_excel(path, engine='openpyxl' if path.lower().endswith('.xlsx') else None)
            headers = list(df.columns.astype(str))
            rows = df.dropna(how='all').values.tolist()
            return headers, rows
        except ModuleNotFoundError:
            if path.lower().endswith('.xlsx'):
                try:
                    openpyxl = importlib.import_module('openpyxl')
                    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
                    sheet = wb.active
                    rows = list(sheet.iter_rows(values_only=True))
                    headers = [str(cell) if cell is not None else '' for cell in rows[0]] if rows else []
                    return headers, rows[1:]
                except Exception as excel_error:
                    raise ValueError(f'Error leyendo Excel: {excel_error}')
            if path.lower().endswith('.xls'):
                try:
                    xlrd = importlib.import_module('xlrd')
                    workbook = xlrd.open_workbook(path)
                    sheet = workbook.sheet_by_index(0)
                    headers = [str(sheet.cell_value(0, col)) for col in range(sheet.ncols)]
                    rows = [sheet.row_values(row) for row in range(1, sheet.nrows)]
                    return headers, rows
                except Exception as excel_error:
                    raise ValueError(f'Error leyendo XLS: {excel_error}')
            raise ValueError('Pandas no está instalado y no se pudo leer el archivo Excel.')
        except Exception as e:
            raise ValueError(f'Error leyendo Excel: {e}')

    def skip_inventory(self):
        self.csv_path = ""
        self.inventory_connected = False
        self.inventory_headers = []
        self.inventory_rows = 0
        self.inventory_type = ""
        self.inventory_summary.setText("Continuar sin inventario. El bot usará solo el contexto de la tienda.")
        self.page3_status.setText("Has decidido continuar sin inventario.")
        self.btn_next3.setEnabled(True)

    def show_loading(self, text="Procesando..."):
        self.loading_overlay.setGeometry(self.rect())
        self.spinner_text.setText(text)
        self.loading_overlay.show()
        self.spinner_timer.start()
        self.loading_overlay.raise_()

    def hide_loading(self):
        if self.spinner_timer.isActive():
            self.spinner_timer.stop()
        self.loading_overlay.hide()

    def update_role_logic(self, _=None):
        tienda = self.store_input.text().strip() or "tu tienda"
        adn = self.description_input.toPlainText().strip() or "un negocio profesional"
        role = self.type_combo.currentText()
        inventario = "sin inventario vinculado" if not self.inventory_connected else f"un catálogo con {self.inventory_rows} productos"
        start = self.start_time.time()
        end = self.end_time.time()
        horario_valido = end > start

        if not horario_valido:
            self.schedule_warning.setText("El horario de cierre debe ser posterior al de apertura")
        else:
            self.schedule_warning.setText("")

        prompt = (
            f"Eres un humano real, parte del equipo de atención de la empresa. "
            f"NUNCA admitas ser una IA o un bot. Si te preguntan, di que eres el encargado digital. "
            f"Si no hay inventario vinculado (Paso 3 omitido), responde basándote solo en la descripción de la tienda, sin inventar precios. "
            f"Eres el encargado de ventas de {tienda}. "
            f"ADN de la tienda: {adn}. Inventario: {inventario}. "
            f"Horario de atención: de {self.start_time.time().toString('HH:mm')} a {self.end_time.time().toString('HH:mm')}."
        )
        prompt += (
            " Usa un lenguaje natural, evita listas numeradas robóticas a menos que el cliente pida un catálogo. "
            "Si el cliente pregunta algo que no está en la descripción ni en el inventario, di: 'Déjame consultar con el encargado del área para darte la información exacta' "
            "y no respondas más hasta que el dueño intervenga. "
            "Si hay stock, anima al cliente; si el stock es bajo (menos de 3), menciona que quedan pocas unidades para generar urgencia."
        )

        if self.inventory_connected:
            prompt += (
                f" Tienes un catálogo de productos. Usa la información de las columnas detectadas ({', '.join(self.inventory_headers)}) "
                "para dar respuestas precisas y humanas. Si el stock es 0, informa que no hay disponibilidad."
            )

        if role == "Encargado de tienda":
            prompt += " Atiende con foco en el cliente y en las necesidades de la tienda."
        elif role == "Atención General":
            prompt += " Atiende con cortesía y orientación general, manteniendo un vínculo humano."
        elif role == "Personalizado":
            prompt += " Adapta tu tono de acuerdo al estilo de la tienda y al cliente."

        self.context_input.setPlainText(prompt)

    def finish_and_save(self):
        self.update_role_logic()
        if self.end_time.time() <= self.start_time.time():
            self.schedule_warning.setText("El horario de cierre debe ser posterior al de apertura")
            return
        self.accept()

    def get_data(self):
        inventory_summary = ", ".join(self.inventory_headers) if self.inventory_headers else "Sin encabezados detectados"
        return {
            "user": self.user_input.text().strip(),
            "pass": self.pass_input.text().strip(),
            "store_name": self.store_input.text().strip(),
            "description": self.description_input.toPlainText().strip(),
            "inventory_path": self.csv_path,
            "inventory_connected": self.inventory_connected,
            "inventory_metadata": {
                "headers": self.inventory_headers,
                "summary": inventory_summary,
            },
            "inventory_rows": self.inventory_rows,
            "type": self.type_combo.currentText(),
            "start": self.start_time.time().toString("HH:mm"),
            "end": self.end_time.time().toString("HH:mm"),
            "proxy": "Auto",
            "prompt": self.context_input.toPlainText().strip(),
            "security_level": "High",
            "system_prompt_final": self.context_input.toPlainText().strip(),
        }
