import qtawesome as qta
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QFrame, QPushButton, QTableWidget, QTableWidgetItem,
                             QHeaderView, QSplitter)
from PyQt6.QtCore import Qt, QSize

class SalesPage(QWidget):
    def __init__(self, db_service, parent=None):
        super().__init__(parent)
        self.db = db_service
        self.setObjectName("SalesPage")
        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(35, 35, 35, 35)
        main_layout.setSpacing(25)

        # --- HEADER ---
        header_layout = QHBoxLayout()
        title_vbox = QVBoxLayout()
        title = QLabel("Caja y Validación de Pagos")
        title.setStyleSheet("color: #FFFFFF; font-size: 28px; font-weight: 900;")
        subtitle = QLabel("Auditoría financiera de conversiones realizadas por los agentes.")
        subtitle.setStyleSheet("color: #777777; font-size: 13px;")
        title_vbox.addWidget(title)
        title_vbox.addWidget(subtitle)
        header_layout.addLayout(title_vbox)
        header_layout.addStretch()
        main_layout.addLayout(header_layout)

        # --- KPIs (MÉTRICAS) ---
        kpis_layout = QHBoxLayout()
        kpis_layout.setSpacing(20)
        
        self.kpi_pendientes = self._create_kpi_card("Pendientes", "0", "fa5s.clock", "#FFB300")
        self.kpi_aprobadas = self._create_kpi_card("Aprobadas Hoy", "0", "fa5s.check-circle", "#00E5FF")
        self.kpi_ingresos = self._create_kpi_card("Ingresos (USD)", "$0.00", "fa5s.dollar-sign", "#4CAF50")
        
        kpis_layout.addWidget(self.kpi_pendientes)
        kpis_layout.addWidget(self.kpi_aprobadas)
        kpis_layout.addWidget(self.kpi_ingresos)
        main_layout.addLayout(kpis_layout)

        # --- SPLITTER (MASTER-DETAIL) ---
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # LADO IZQUIERDO: Tabla de Pagos
        left_panel = QFrame()
        left_panel.setObjectName("salesPanelLeft")
        left_layout = QVBoxLayout(left_panel)
        
        lbl_table = QLabel("Transacciones Recientes")
        lbl_table.setStyleSheet("color: #FFFFFF; font-weight: bold; font-size: 14px; margin-bottom: 10px; border: none;")
        left_layout.addWidget(lbl_table)

        self.table = QTableWidget(0, 4)
        self.table.setObjectName("pegasusTable")
        self.table.setHorizontalHeaderLabels(["ID", "Cliente", "Monto", "Estado"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self._on_transaction_selected)
        left_layout.addWidget(self.table)

        # LADO DERECHO: Detalles y Acciones
        self.right_panel = QFrame()
        self.right_panel.setObjectName("salesPanelRight")
        self.right_layout = QVBoxLayout(self.right_panel)
        self.right_layout.setContentsMargins(20, 20, 20, 20)
        
        self.lbl_detail_title = QLabel("Selecciona un pago")
        self.lbl_detail_title.setStyleSheet("color: #777777; font-weight: bold; font-size: 16px; border: none;")
        self.right_layout.addWidget(self.lbl_detail_title, alignment=Qt.AlignmentFlag.AlignCenter)
        
        self.detail_content = QWidget()
        self.detail_content.hide()
        dc_layout = QVBoxLayout(self.detail_content)
        dc_layout.setContentsMargins(0, 20, 0, 0)
        
        # Mockup de datos de detalle
        self.lbl_ref = QLabel("Referencia: ---")
        self.lbl_ref.setStyleSheet("color: #FFFFFF; font-size: 14px; border: none;")
        dc_layout.addWidget(self.lbl_ref)
        
        self.lbl_banco = QLabel("Banco: ---")
        self.lbl_banco.setStyleSheet("color: #A0A0A0; font-size: 13px; border: none; margin-bottom: 20px;")
        dc_layout.addWidget(self.lbl_banco)
        
        btn_row = QHBoxLayout()
        btn_approve = QPushButton("Aprobar Pago")
        btn_approve.setObjectName("primaryButton")
        btn_reject = QPushButton("Rechazar")
        btn_reject.setObjectName("dangerButton")
        btn_row.addWidget(btn_reject)
        btn_row.addWidget(btn_approve)
        
        dc_layout.addLayout(btn_row)
        dc_layout.addStretch()
        self.right_layout.addWidget(self.detail_content)

        splitter.addWidget(left_panel)
        splitter.addWidget(self.right_panel)
        splitter.setSizes([600, 300])
        
        main_layout.addWidget(splitter)

    def _create_kpi_card(self, title, value, icon_str, color):
        card = QFrame()
        card.setObjectName("kpiCard")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        
        vbox = QVBoxLayout()
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("color: #777777; font-size: 12px; font-weight: bold; border: none;")
        lbl_val = QLabel(value)
        lbl_val.setObjectName("KPIValue")
        lbl_val.setStyleSheet(f"color: #FFFFFF; font-size: 24px; font-weight: 900; border: none;")
        vbox.addWidget(lbl_title)
        vbox.addWidget(lbl_val)
        
        icon = QLabel()
        icon.setPixmap(qta.icon(icon_str, color=color).pixmap(30, 30))
        icon.setStyleSheet("border: none; background: transparent;")
        
        layout.addLayout(vbox)
        layout.addStretch()
        layout.addWidget(icon)
        card.value_label = lbl_val
        return card

    def _on_transaction_selected(self):
        selected = self.table.selectedItems()
        if selected:
            self.lbl_detail_title.hide()
            self.detail_content.show()
            self.lbl_ref.setText(f"Referencia: #109283{selected[0].row()}")
            self.lbl_banco.setText("Banco: Pago Móvil / Binance")
        else:
            self.lbl_detail_title.show()
            self.detail_content.hide()

    def refresh_pending_orders(self):
        orders = []
        if hasattr(self.db, 'get_pending_orders'):
            try:
                orders = self.db.get_pending_orders()
            except Exception:
                orders = []

        self.table.setRowCount(0)
        pendientes = len(orders)
        aprobadas = len([order for order in orders if order.get('status') == 'VALIDATED'])
        ingresos = sum(float(order.get('monto', 0) or 0) for order in orders if isinstance(order.get('monto'), (int, float, str)))

        self.kpi_pendientes.value_label.setText(str(pendientes))
        self.kpi_aprobadas.value_label.setText(str(aprobadas))
        self.kpi_ingresos.value_label.setText(f"${ingresos:,.2f}")

        for order in orders:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(order.get('id', 'N/A'))))
            self.table.setItem(row, 1, QTableWidgetItem(str(order.get('cliente_id', 'N/A'))))
            self.table.setItem(row, 2, QTableWidgetItem(str(order.get('monto', '0'))))
            self.table.setItem(row, 3, QTableWidgetItem(str(order.get('status', 'PENDIENTE'))))
