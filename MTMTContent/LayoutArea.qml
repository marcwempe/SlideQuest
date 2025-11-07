import QtQuick
import QtQuick.Controls

Rectangle {
    id: root
    property int areaIndex: -1
    property var data: ({})
    property bool editMode: false

    signal openImageRequested(int areaIndex)
    signal removeImageRequested(int areaIndex)
    signal displayModeRequested(int areaIndex, string mode)
    signal anchorRequested(int areaIndex, string anchor)
    signal dropReceived(int areaIndex, var urls)

    radius: 8
    border.width: 1
    border.color: "#999999"
    color: data && data.imageSource ? "#111111" : "#f6f6f6"
    clip: true

    readonly property string displayMode: data && data.displayMode ? data.displayMode : "Bildfüllend (Vertikal)"
    readonly property string anchor: data && data.anchor ? data.anchor : "Mitte"
    readonly property url imageSource: data && data.imageSource ? data.imageSource : ""

    Image {
        id: previewImage
        anchors.fill: parent
        source: root.imageSource
        fillMode: root.displayMode === "Bildfüllend (Horizontal)" ? Image.PreserveAspectCrop :
                  root.displayMode === "Manueller Zoom" ? Image.Pad : Image.PreserveAspectFit
        visible: source !== ""
        horizontalAlignment: root.anchor.indexOf("links") !== -1 ? Image.AlignLeft :
                              root.anchor.indexOf("rechts") !== -1 ? Image.AlignRight : Image.AlignHCenter
        verticalAlignment: root.anchor.indexOf("oben") !== -1 ? Image.AlignTop :
                            root.anchor.indexOf("unten") !== -1 ? Image.AlignBottom : Image.AlignVCenter
    }

    Text {
        anchors.centerIn: parent
        text: root.imageSource !== "" ? "" : qsTr("Bild hier ablegen")
        color: "#666666"
        font.pixelSize: 16
        visible: root.imageSource === ""
    }

    Column {
        anchors {
            right: parent.right
            bottom: parent.bottom
            margins: 8
        }
        spacing: 4
        visible: root.editMode

        Label {
            text: root.displayMode
            color: "#ffffff"
            background: Rectangle {
                color: "#66000000"
                radius: 4
            }
            padding: 4
        }

        Label {
            text: qsTr("Anker: %1").arg(root.anchor)
            color: "#ffffff"
            background: Rectangle {
                color: "#66000000"
                radius: 4
            }
            padding: 4
        }
    }

    DropArea {
        anchors.fill: parent
        onDropped: function(drop) {
            if (drop && drop.urls && drop.urls.length > 0) {
                root.dropReceived(root.areaIndex, drop.urls);
                drop.acceptProposedAction();
            }
        }
    }

    TapHandler {
        acceptedButtons: Qt.RightButton
        gesturePolicy: TapHandler.WithinBounds
        onTapped: {
            if (areaMenu.visible)
                areaMenu.close();
            areaMenu.popup();
        }
    }

    Menu {
        id: areaMenu
        enabled: root.editMode

        MenuItem {
            text: qsTr("Bild öffnen …")
            onTriggered: root.openImageRequested(root.areaIndex);
        }
        MenuItem {
            text: qsTr("Bild löschen")
            enabled: root.imageSource !== ""
            onTriggered: root.removeImageRequested(root.areaIndex);
        }

        MenuSeparator {}

        Menu {
            title: qsTr("Anzeigemodus")
            Repeater {
                model: [
                    "Bildfüllend (Vertikal)",
                    "Bildfüllend (Horizontal)",
                    "Manueller Zoom"
                ]
                delegate: MenuItem {
                    text: modelData
                    checkable: true
                    checked: root.displayMode === modelData
                    onTriggered: root.displayModeRequested(root.areaIndex, modelData);
                }
            }
        }

        Menu {
            title: qsTr("Zoom Ankerpunkt")
            Repeater {
                model: [
                    "Links oben",
                    "Mitte oben",
                    "Rechts oben",
                    "Links Mitte",
                    "Mitte",
                    "Rechts Mitte",
                    "Links unten",
                    "Mitte unten",
                    "Rechts unten"
                ]
                delegate: MenuItem {
                    text: modelData
                    checkable: true
                    checked: root.anchor === modelData
                    onTriggered: root.anchorRequested(root.areaIndex, modelData);
                }
            }
        }
    }
}
