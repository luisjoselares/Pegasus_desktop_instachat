from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QScrollArea,
    QWidget,
    QFrame,
    QPushButton,
    QHBoxLayout,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor
from services.database_service import LocalDBService

from views.components import PegasusNotificationCard


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
        title.setStyleSheet(
            "font-size: 20px; color: #FFFFFF; font-weight: 900; letter-spacing: 0.5px;"
            "background: transparent; border: none;"
        )
        layout.addWidget(title)

        self.summary_label = QLabel("")
        self.summary_label.setStyleSheet("color: #FFCC00; font-size: 12px; margin-bottom: 10px;")
        self.summary_label.setWordWrap(True)
        self.summary_label.setVisible(False)
        layout.addWidget(self.summary_label)

        self.alerts_area = QScrollArea(self)
        self.alerts_area.setFrameShape(QFrame.Shape.NoFrame)
        self.alerts_area.setStyleSheet("background: transparent;")
        self.alerts_area.setWidgetResizable(True)

        self.alerts_container = QWidget()
        self.alerts_layout = QVBoxLayout(self.alerts_container)
        self.alerts_layout.setContentsMargins(0, 0, 0, 0)
        self.alerts_layout.setSpacing(12)
        self.alerts_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.alerts_layout.addStretch()

        self.alerts_area.setWidget(self.alerts_container)
        layout.addWidget(self.alerts_area)

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

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    def load_alerts(self):
        self._clear_layout(self.alerts_layout)
        self.alerts_layout.addStretch()

        alerts = self.db.get_recent_alerts(account_id=self.account_id, limit=100)
        if not alerts and self.account_id is None:
            alerts = self.db.get_recent_alerts(limit=100)

        if alerts:
            for alert in alerts:
                title = f"{alert.get('alert_type', 'Alerta')} · {alert.get('username', 'Usuario')}"
                message = str(alert.get('details', 'Sin detalles'))
                timestamp = str(alert.get('created_at', ''))
                critical = alert.get('status', '').upper() in ('FAILED', 'CRITICAL')

                card = PegasusNotificationCard(
                    title=title,
                    message=message,
                    timestamp=timestamp,
                    critical=critical,
                )
                self.alerts_layout.insertWidget(self.alerts_layout.count() - 1, card)

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
            empty_label = QLabel("No hay alertas registradas.")
            empty_label.setStyleSheet("color: #BBBBBB; font-size: 14px;")
            self.alerts_layout.insertWidget(self.alerts_layout.count() - 1, empty_label)
