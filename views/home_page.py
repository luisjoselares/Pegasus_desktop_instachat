import qtawesome as qta
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QFrame, QPushButton, QScrollArea)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor

from views.components import PegasusCard, PegasusPrimaryButton

class HomePage(QWidget):
    def __init__(self, main_window_ref, parent=None):
        super().__init__(parent)
        self.main_window = main_window_ref
        self.db = main_window_ref.db_service
        self._build_ui()

    def _build_ui(self):
        # Layout Principal con Scroll para pantallas pequeñas
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")
        
        container = QWidget()
        container.setStyleSheet("background-color: #080808;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(30)

        # --- HEADER SECCIÓN ---
        header_layout = QHBoxLayout()
        
        v_header = QVBoxLayout()
        self.lbl_welcome = QLabel("Ecosistema Pegasus AI")
        self.lbl_welcome.setStyleSheet("color: #FFFFFF; font-size: 36px; font-weight: 900; letter-spacing: 1px;")
        
        tagline = QLabel("Automatización de Élite con Privacidad de Grado Militar.")
        tagline.setStyleSheet("color: #00E5FF; font-size: 14px; font-weight: 600; text-transform: uppercase;")
        
        v_header.addWidget(self.lbl_welcome)
        v_header.addWidget(tagline)
        header_layout.addLayout(v_header)
        header_layout.addStretch()

        # Badge de Licencia Dinámico
        self.lbl_license_status = QLabel("LICENCIA PROFESIONAL ACTIVA")
        self.lbl_license_status.setStyleSheet("""
            background-color: rgba(0, 229, 255, 0.1);
            color: #00E5FF;
            border: 1px solid #00E5FF;
            border-radius: 15px;
            padding: 10px 20px;
            font-weight: 800;
            font-size: 11px;
        """)
        header_layout.addWidget(self.lbl_license_status, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addLayout(header_layout)

        # --- BANNER DE SEGURIDAD (EL RESALTADO QUE QUERÍAS) ---
        security_banner = QFrame()
        security_banner.setStyleSheet("""
            QFrame {
                background-color: #0D0D0D;
                border: 1px solid #1A1A1A;
                border-left: 4px solid #00E5FF;
                border-radius: 12px;
            }
        """)
        sec_layout = QHBoxLayout(security_banner)
        sec_layout.setContentsMargins(25, 25, 25, 25)
        
        sec_icon = QLabel()
        sec_icon.setPixmap(qta.icon('fa5s.user-shield', color='#00E5FF').pixmap(40, 40))
        sec_icon.setFixedWidth(60)
        
        sec_text_v = QVBoxLayout()
        sec_title = QLabel("Protocolo Zero-Knowledge & Almacenamiento Local")
        sec_title.setStyleSheet("color: #FFFFFF; font-size: 18px; font-weight: bold; border: none;")
        
        sec_desc = QLabel(
            "Pegasus opera bajo un esquema de seguridad descentralizada. Tus credenciales de Instagram, "
            "historial de chats y base de datos de clientes se encriptan mediante AES-256 en este equipo. "
            "Nuestros servidores jamás reciben tus contraseñas ni datos privados. La soberanía de tu información es total."
        )
        sec_desc.setWordWrap(True)
        sec_desc.setStyleSheet("color: #A0A0A0; font-size: 13px; border: none; line-height: 1.5;")
        
        sec_text_v.addWidget(sec_title)
        sec_text_v.addWidget(sec_desc)
        
        sec_layout.addWidget(sec_icon, alignment=Qt.AlignmentFlag.AlignTop)
        sec_layout.addLayout(sec_text_v)
        layout.addWidget(security_banner)

        # --- GRID DE FORTALEZAS ---
        features_layout = QHBoxLayout()
        features_layout.setSpacing(20)

        features_layout.addWidget(self._create_card(
            'fa5s.brain', "IA Neuro-Ventas", 
            "Modelos Llama 3 optimizados para el mercado latino. Cierra ventas con lenguaje natural y carisma humano."
        ))
        features_layout.addWidget(self._create_card(
            'fa5s.fingerprint', "Meta-Shield 2.0", 
            "Simulación de comportamiento humano con varianza de tiempos de respuesta para proteger la integridad de tus cuentas."
        ))
        features_layout.addWidget(self._create_card(
            'fa5s.database', "Auditoría Local", 
            "Todo el flujo de trabajo queda registrado en tu base de datos privada para control de calidad y trazabilidad total."
        ))
        layout.addLayout(features_layout)

        # --- ACCIONES RÁPIDAS ---
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(15)
        
        btn_accounts = self._create_action_btn("GESTIONAR CUENTAS", "fa5s.user-plus", True)
        btn_accounts.clicked.connect(lambda: self.main_window.show_page(1))
        
        btn_logs = self._create_action_btn("CONSOLA DE ACTIVIDAD", "fa5s.terminal", False)
        btn_logs.clicked.connect(lambda: self.main_window.show_page(3))
        
        actions_layout.addWidget(btn_accounts)
        actions_layout.addWidget(btn_logs)
        actions_layout.addStretch()
        layout.addLayout(actions_layout)

        layout.addStretch()
        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def _create_card(self, icon_str, title, desc):
        card = PegasusCard()
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(20, 25, 20, 25)
        c_layout.setSpacing(12)
        
        icon_lbl = QLabel()
        icon_lbl.setPixmap(qta.icon(icon_str, color='#00E5FF').pixmap(30, 30))
        icon_lbl.setStyleSheet("background: transparent; border: none;")
        
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("color: #FFFFFF; font-size: 15px; font-weight: 800; background: transparent; border: none;")
        
        desc_lbl = QLabel(desc)
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet("color: #777777; font-size: 12px; background: transparent; border: none; line-height: 1.4;")
        
        c_layout.addWidget(icon_lbl)
        c_layout.addWidget(title_lbl)
        c_layout.addWidget(desc_lbl)
        c_layout.addStretch()
        return card

    def _create_action_btn(self, text, icon_str, primary=True):
        btn = QPushButton(text)
        btn.setIcon(qta.icon(icon_str, color='#000000' if primary else '#FFFFFF'))
        btn.setIconSize(QSize(18, 18))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        if primary:
            btn.setStyleSheet("""
                QPushButton { background-color: #00E5FF; color: #000000; font-weight: 800; 
                              padding: 15px 30px; border-radius: 8px; font-size: 12px; }
                QPushButton:hover { background-color: #00B3CC; }
            """)
        else:
            btn.setStyleSheet("""
                QPushButton { background-color: transparent; color: #FFFFFF; font-weight: 800; 
                              padding: 15px 30px; border-radius: 8px; font-size: 12px; border: 1px solid #333333; }
                QPushButton:hover { background-color: #1A1A1A; border: 1px solid #555555; }
            """)
        return btn