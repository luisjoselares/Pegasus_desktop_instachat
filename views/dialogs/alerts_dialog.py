from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QHBoxLayout,
    QHeaderView,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor
from services.database_service import LocalDBService


class AlertsDialog(QDialog):
    def __init__(self, parent=None, account_id=None, account_name=None):
        super().__init__(parent)
        self.setWindowTitle("Alertas de la cuenta")
        self.setMinimumSize(900, 500)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

        self.db = LocalDBService()
        self.account_id = account_id
        self.account_name = account_name

        layout = QVBoxLayout(self)
        title = QLabel(
            f"Alertas de seguridad para la cuenta: {account_name}" if account_name else "Alertas de seguridad"
        )
        title.setStyleSheet("font-size: 18px; color: #00E5FF; font-weight: bold;")
        layout.addWidget(title)

        self.summary_label = QLabel("")
        self.summary_label.setStyleSheet("color: #FFCC00; font-size: 12px; margin-bottom: 10px;")
        self.summary_label.setWordWrap(True)
        self.summary_label.setVisible(False)
        layout.addWidget(self.summary_label)

        self.table = QTableWidget(0, 7, self)
        self.table.setHorizontalHeaderLabels([
            "Fecha",
            "Hilo",
            "Usuario",
            "Tipo",
            "Estado",
            "Destinatario",
            "Detalles",
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        footer = QHBoxLayout()
        footer.addStretch()
        self.btn_refresh = QPushButton("Actualizar")
        self.btn_refresh.clicked.connect(self.load_alerts)
        footer.addWidget(self.btn_refresh)
        self.btn_close = QPushButton("Cerrar")
        self.btn_close.clicked.connect(self.close)
        footer.addWidget(self.btn_close)
        layout.addLayout(footer)

        self.load_alerts()

    def load_alerts(self):
        self.table.setRowCount(0)
        alerts = self.db.get_recent_alerts(account_id=self.account_id, limit=100)
        if not alerts and self.account_id is None:
            alerts = self.db.get_recent_alerts(limit=100)

        for alert in alerts:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(alert.get('created_at', ''))))
            self.table.setItem(row, 1, QTableWidgetItem(str(alert.get('thread_id', ''))))
            self.table.setItem(row, 2, QTableWidgetItem(str(alert.get('username', ''))))
            self.table.setItem(row, 3, QTableWidgetItem(str(alert.get('alert_type', ''))))
            status_item = QTableWidgetItem(str(alert.get('status', '')))
            status_text = status_item.text().upper()
            if status_text == 'SENT':
                status_item.setForeground(QBrush(QColor('#7CFC00')))
            elif status_text == 'FAILED':
                status_item.setForeground(QBrush(QColor('#FF6666')))
            elif status_text == 'PENDING':
                status_item.setForeground(QBrush(QColor('#FFDD55')))
            else:
                status_item.setForeground(QBrush(QColor('#FFFFFF')))
            self.table.setItem(row, 4, status_item)
            self.table.setItem(row, 5, QTableWidgetItem(str(alert.get('recipient', ''))))
            self.table.setItem(row, 6, QTableWidgetItem(str(alert.get('details', ''))))

        if alerts:
            summary = f"Total: {len(alerts)} alerta(s) mostradas."
            if self.account_id is None:
                stats = self.db.get_alert_stats(cliente_id=None)
            else:
                stats = self.db.get_alert_stats(account_id=self.account_id)
            sent = stats.get('SENT', 0)
            failed = stats.get('FAILED', 0)
            pending = stats.get('PENDING', 0)
            summary += f" ({sent} enviadas, {failed} fallidas, {pending} pendientes)."
            self.summary_label.setText(summary)
            self.summary_label.setVisible(True)
        else:
            self.summary_label.setVisible(False)

        if not alerts:
            self.table.setRowCount(1)
            self.table.setItem(0, 0, QTableWidgetItem("No hay alertas registradas."))
            for col in range(1, self.table.columnCount()):
                self.table.setItem(0, col, QTableWidgetItem("-"))
