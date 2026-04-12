import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Window 2.15

Window {
    id: mainWindow
    width: 520
    height: 680
    visible: true
    title: "Configuración de Agente Pegasus (QML)"
    color: "#080808" // El fondo Deep Dark

    // El cerebro de Python que conectaremos
    property var backend

    Flickable {
        anchors.fill: parent
        anchors.margins: 25
        contentHeight: mainColumn.height
        clip: true

        Column {
            id: mainColumn
            width: parent.width
            spacing: 20

            Text {
                text: "Operaciones Pegasus"
                color: "#FFFFFF"
                font.pixelSize: 24
                font.bold: true
            }

            Text {
                text: "Interfaz acelerada por hardware. Cero saltos."
                color: "#777777"
                font.pixelSize: 14
                wrapMode: Text.WordWrap
                width: parent.width
            }

            // --- COMPONENTE ACORDEÓN ---
            Rectangle {
                width: parent.width
                height: header.height + content.height
                color: "transparent"
                clip: true

                // Animación fluida de expansión
                Behavior on height {
                    NumberAnimation { duration: 300; easing.type: Easing.InOutQuad }
                }

                Rectangle {
                    id: header
                    width: parent.width
                    height: 50
                    color: mouseArea.containsMouse ? "rgba(0, 229, 255, 0.08)" : "rgba(255, 255, 255, 0.03)"
                    radius: 8
                    border.color: mouseArea.containsMouse ? "#00E5FF" : "#222222"
                    border.width: 1

                    Text {
                        text: "💰 Finanzas, Moneda y Pagos"
                        color: "#FFFFFF"
                        font.bold: true
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.left: parent.left
                        anchors.leftMargin: 15
                    }

                    MouseArea {
                        id: mouseArea
                        anchors.fill: parent
                        hoverEnabled: true
                        onClicked: content.isOpen = !content.isOpen
                    }
                }

                Rectangle {
                    id: content
                    width: parent.width
                    anchors.top: header.bottom
                    anchors.topMargin: 10
                    
                    // Propiedad que controla si está abierto
                    property bool isOpen: false
                    height: isOpen ? 120 : 0
                    color: "transparent"
                    visible: height > 0

                    Column {
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 10

                        TextField {
                            width: parent.width
                            placeholderText: "País (Ej: Venezuela)"
                            color: "#FFFFFF"
                            background: Rectangle {
                                color: "rgba(255, 255, 255, 0.03)"
                                radius: 8
                                border.color: "#222222"
                            }
                        }

                        Button {
                            text: "Probar Conexión con Python"
                            width: parent.width
                            contentItem: Text {
                                text: parent.text
                                color: "#000000"
                                font.bold: true
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }
                            background: Rectangle {
                                color: parent.hovered ? "#00B3CC" : "#00E5FF"
                                radius: 20
                            }
                            // Cuando hacemos clic, llamamos a Python
                            onClicked: backend.recibir_click("¡Hola desde QML, Luis!")
                        }
                    }
                }
            }
        }
    }
}