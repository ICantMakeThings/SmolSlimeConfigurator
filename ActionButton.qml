import QtQuick
import QtQuick.Controls

Button {
    id: control

    property color fillColor: "#2b4938"
    property color labelColor: "#e6efe8"
    property color borderColor: "#45634f"
    property color pressedColor: "#75d49e"
    property color disabledColor: control.palette.window.hslLightness > 0.5 ? "#e5e5e7" : "#3a3a3c"

    implicitWidth: 132
    implicitHeight: 50
    font.pixelSize: 14
    font.weight: Font.DemiBold

    background: Rectangle {
           radius: 8
        color: !control.enabled ? control.disabledColor
               : control.down ? control.pressedColor
               : control.hovered ? Qt.darker(control.fillColor, 1.04) : control.fillColor
        border.width: 1
        border.color: control.borderColor
           Behavior on color { ColorAnimation { duration: 120 } }
    }

    contentItem: Text {
        text: control.text
        font: control.font
        color: control.enabled ? control.labelColor : "#8c8c91"
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        leftPadding: 10
        rightPadding: 10
        elide: Text.ElideRight
    }
}
