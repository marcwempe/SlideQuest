import QtQuick
import QtQuick.Controls
import "LayoutParser.js" as LayoutParser

Item {
    id: root
    property string layoutDefinition: ""
    property var areaData: []
    property bool editMode: false

    signal openImage(int areaIndex)
    signal removeImage(int areaIndex)
    signal displayModeChange(int areaIndex, string mode)
    signal anchorChange(int areaIndex, string anchor)
    signal dropOnArea(int areaIndex, var urls)

    readonly property var layoutContent: LayoutParser.parseLayout(layoutDefinition)

    clip: true

    function areaInfo(index) {
        return areaData && index >= 0 && index < areaData.length ? areaData[index] : ({});
    }

    Rectangle {
        anchors.fill: parent
        color: "#2b2b2b"
        radius: 12
        border.width: 1
        border.color: "#3f3f3f"
    }

    Loader {
        anchors.fill: parent
        sourceComponent: layoutContent.columns.length > 0 ? columnView : emptyState
    }

    Component {
        id: columnView

        Row {
            anchors.fill: parent
            spacing: 0

            Repeater {
                model: layoutContent.columns.length
                delegate: Item {
                    required property int index
                    readonly property var columnData: layoutContent.columns[index]

                    width: root.width * columnData.widthPercent / 100
                    height: parent.height

                    Column {
                        anchors.fill: parent
                        spacing: 0

                        Repeater {
                            model: columnData.rows.length
                            delegate: Item {
                                required property int index
                                readonly property var rowData: columnData.rows[index]

                                width: parent.width
                                height: parent.height * rowData.heightPercent / 100

                                LayoutArea {
                                    anchors.fill: parent
                                    anchors.margins: 8
                                    areaIndex: rowData.areaIndex
                                    editMode: root.editMode
                                    data: root.areaInfo(rowData.areaIndex)

                                    onOpenImageRequested: root.openImage(areaIndex)
                                    onRemoveImageRequested: root.removeImage(areaIndex)
                                    onDisplayModeRequested: root.displayModeChange(areaIndex, mode)
                                    onAnchorRequested: root.anchorChange(areaIndex, anchor)
                                    onDropReceived: root.dropOnArea(areaIndex, urls)
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    Component {
        id: emptyState

        Item {
            anchors.fill: parent

            Column {
                anchors.centerIn: parent
                spacing: 12

                Label {
                    text: qsTr("Noch kein Layout ausgewählt")
                    font.pixelSize: 20
                    color: "#f0f0f0"
                }

                Label {
                    text: qsTr("Wähle ein Layout in der Detailansicht aus.")
                    color: "#cccccc"
                }
            }
        }
    }
}
