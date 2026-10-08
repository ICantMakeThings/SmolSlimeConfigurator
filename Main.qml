import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts

// Overdone tooltip overlay
ApplicationWindow {
    id: window
    property var backend: null
    property int pageIndex: 0
    property var themes: ({
        "Light": {
            background: "#f5f5f7", panel: "#ffffff", ink: "#1d1d1f", muted: "#707075",
            accent: "#0879f9", line: "#e5e5e8", header: "#ffffff", headerMuted: "#707075",
            headerControl: "#f5f5f7", headerBorder: "#dedee2", action: "#0879f9", actionText: "#ffffff",
            button: "#f5f5f7", buttonText: "#1d1d1f", buttonBorder: "#e5e5e8"
        },
        "Dark": {
            background: "#1c1c1e", panel: "#2c2c2e", ink: "#f5f5f7", muted: "#a1a1a6",
            accent: "#409cff", line: "#3a3a3c", header: "#2c2c2e", headerMuted: "#a1a1a6",
            headerControl: "#3a3a3c", headerBorder: "#48484a", action: "#0a84ff", actionText: "#ffffff",
            button: "#3a3a3c", buttonText: "#f5f5f7", buttonBorder: "#48484a"
        },
        "Dark Blue": {
            background: "#191d22", panel: "#272d34", ink: "#f0f2f5", muted: "#a2aab4",
            accent: "#68b8ff", line: "#39414a", header: "#272d34", headerMuted: "#a2aab4",
            headerControl: "#343c45", headerBorder: "#46515c", action: "#168cff", actionText: "#ffffff",
            button: "#343c45", buttonText: "#f0f2f5", buttonBorder: "#46515c"
        },
        "Dark Green": {
            background: "#191e1a", panel: "#272d29", ink: "#f0f3f0", muted: "#a1aaa3",
            accent: "#75cf8a", line: "#3a433d", header: "#272d29", headerMuted: "#a1aaa3",
            headerControl: "#343c36", headerBorder: "#48534a", action: "#4caf68", actionText: "#ffffff",
            button: "#343c36", buttonText: "#f0f3f0", buttonBorder: "#48534a"
        }
    })[backend.theme] || ({
        background: "#191e1a", panel: "#272d29", ink: "#f0f3f0", muted: "#a1aaa3",
        accent: "#75cf8a", line: "#3a433d", header: "#272d29", headerMuted: "#a1aaa3",
        headerControl: "#343c36", headerBorder: "#48534a", action: "#4caf68", actionText: "#ffffff",
        button: "#343c36", buttonText: "#f0f3f0", buttonBorder: "#48534a"
    })
    property color ink: themes.ink
    property color muted: themes.muted
    property color accent: themes.accent
    property color line: themes.line
    property color paper: themes.panel

    width: 900
    height: 660
    minimumWidth: 820
    minimumHeight: 640
    visible: true
    title: "SmolSlimeConfigurator"
    color: themes.background
    font.family: Qt.platform.os === "osx" ? "SF Pro Text" : "Noto Sans"

    Material.theme: backend.theme === "Light" ? Material.Light : Material.Dark
    Material.background: themes.background
    Material.foreground: themes.ink
    Material.primary: themes.header
    Material.accent: themes.accent

    Connections {
        target: backend
        function onLogMessage(message, kind) {
            const color = kind === "error" ? "#e27770"
                        : kind === "success" ? "#72c997"
                        : kind === "command" ? "#d6b36e" : themes.muted
            const followOutput = consoleScroll.atYEnd
            consoleArea.append("<font color='" + color + "'>" + message.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;") + "</font>")
            if (followOutput) {
                Qt.callLater(function() {
                    consoleScroll.contentY = Math.max(0, consoleScroll.contentHeight - consoleScroll.height)
                })
            }
        }
    }

    // Top UI | Yk the serial buttons
    header: Rectangle {
        implicitHeight: 60
        color: themes.header
        border.color: line
        border.width: 1

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 20
            anchors.rightMargin: 20
            spacing: 12

            Image {
                source: "icon.png"
                sourceSize.width: 36
                sourceSize.height: 36
                fillMode: Image.PreserveAspectFit
            }
            ColumnLayout {
                spacing: 0
                Label { text: "SmolSlime"; color: ink; font.pixelSize: 18; font.bold: true }
                Label { text: "CONFIGURATOR"; color: muted; font.pixelSize: 10; font.bold: true }
            }
            Item { Layout.fillWidth: true }
            Rectangle {
                Layout.preferredWidth: 10
                Layout.preferredHeight: 10
                radius: 5
                color: backend.connected ? accent : muted
            }
            Label {
                text: backend.connected ? "Connected" : "No device"
                color: backend.connected ? accent : muted
                font.pixelSize: 13
            }
            ComboBox {
                id: portSelector
                Layout.preferredWidth: 190
                implicitHeight: 40
                model: backend.ports
                enabled: !backend.connected
                displayText: currentText || "Select port"
                background: Rectangle { color: themes.headerControl; radius: 5; border.color: themes.headerBorder }
                ToolTip.visible: hovered && backend.tooltipsEnabled
                ToolTip.text: "Select the port for your device"
                contentItem: Text {
                    text: portSelector.displayText
                    color: ink
                    verticalAlignment: Text.AlignVCenter
                    leftPadding: 10
                    elide: Text.ElideRight
                }
            }
            ActionButton {
                text: backend.connected ? "Disconnect" : "Connect"
                Layout.minimumWidth: 152
                Layout.preferredWidth: 152
                Layout.preferredHeight: 40
                fillColor: backend.connected ? themes.button : themes.action
                labelColor: backend.connected ? themes.buttonText : themes.actionText
                borderColor: backend.connected ? themes.buttonBorder : themes.action
                pressedColor: accent
                ToolTip.visible: hovered && backend.tooltipsEnabled
                ToolTip.text: "Connect to the selected serial port"
                onClicked: backend.connected ? backend.disconnectSerial() : backend.connectToPort(portSelector.currentText)
            }
        }
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 18

        Rectangle {
            Layout.preferredWidth: 186
            Layout.fillHeight: true
            color: paper
            radius: 11

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 4
                Label {
                    text: "CONFIGURE"
                    color: muted
                    font.pixelSize: 10
                    font.bold: true
                    leftPadding: 10
                    topPadding: 8
                    bottomPadding: 6
                }
                Repeater {
                    model: ["Tracker", "Receiver", "Firmware", "Settings"]
                    delegate: Button {
                        Layout.fillWidth: true
                        implicitHeight: 38
                        text: modelData
                        font.pixelSize: 13
                        font.weight: pageIndex === index ? Font.DemiBold : Font.Normal
                        onClicked: pageIndex = index
                        background: Rectangle {
                            radius: 7
                            color: pageIndex === index ? (backend.theme === "Light" ? "#e8e8ed" : "#414146") : "transparent"
                        }
                        contentItem: Text {
                            text: parent.text
                            font: parent.font
                            color: ink
                            verticalAlignment: Text.AlignVCenter
                            leftPadding: 10
                        }
                    }
                }
                Item { Layout.fillHeight: true }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 12

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: false
            currentIndex: pageIndex

            // Buttons!
            // Make the repetitive stuff less messy
            // Tracker tab
            ScrollView {
                clip: true
                ColumnLayout {
                    width: parent.width
                    spacing: 10
                    Rectangle {
                        Layout.fillWidth: true
                        color: paper
                        radius: 10
                        border.color: line
                        implicitHeight: trackerActions.implicitHeight + 28
                        GridLayout {
                            id: trackerActions
                            anchors.fill: parent
                            anchors.margins: 14
                            columns: 3
                            columnSpacing: 10
                            rowSpacing: 1
                            Repeater {
                                model: [
                                    {label: "Info", cmd: "info"}, {label: "Reboot", cmd: "reboot"},
                                    {label: "Scan", cmd: "scan"}, {label: "Calibrate", cmd: "calibrate"},
                                    {label: "Battery", cmd: "battery"}, {label: "Pair", cmd: "pair"},
                                    {label: "DFU", cmd: "dfu"}
                                ]
                                delegate: ActionButton {
                                    Layout.fillWidth: true
                                    Layout.minimumWidth: 120
                                    Layout.preferredHeight: 44
                                    fillColor: themes.button
                                    labelColor: themes.buttonText
                                    borderColor: themes.buttonBorder
                                    pressedColor: accent
                                    text: modelData.label
                                    enabled: backend.connected
                                    ToolTip.visible: hovered && backend.tooltipsEnabled
                                    ToolTip.text: commandTooltip(modelData.label)
                                    onClicked: backend.sendCommand(modelData.cmd)
                                }
                            }
                            Repeater {
                                model: [
                                    {label: "6-side calibration", cmd: "6-side"}, {label: "Clear magnetometer", cmd: "mag"},
                                    {label: "Clear pairing", cmd: "clear"}, {label: "Uptime", cmd: "uptime"},
                                    {label: "Debug log", cmd: "debug"}, {label: "Meow!", cmd: "meow"}
                                ]
                                delegate: ActionButton {
                                    Layout.fillWidth: true
                                    Layout.minimumWidth: 120
                                    Layout.preferredHeight: 44
                                    fillColor: themes.button
                                    labelColor: themes.buttonText
                                    borderColor: themes.buttonBorder
                                    pressedColor: accent
                                    text: modelData.label
                                    enabled: backend.connected
                                    ToolTip.visible: hovered && backend.tooltipsEnabled
                                    ToolTip.text: commandTooltip(modelData.label)
                                    onClicked: backend.sendCommand(modelData.cmd)
                                }
                            }
                            RowLayout {
                                Layout.columnSpan: 2
                                Layout.fillWidth: true
                                Item {
                                    Layout.minimumWidth: 40
                                    Layout.preferredWidth: 40
                                }
                                Label { text: "Rst calib/stats"; color: muted }
                                ComboBox { id: resetType; Layout.preferredWidth: 100; implicitHeight: 42; model: ["zro", "acc", "mag", "bat", "all"] }
                                ActionButton {
                                    text: "Reset"
                                    Layout.minimumWidth: 120
                                    Layout.preferredWidth: 120
                                    Layout.preferredHeight: 42
                                    enabled: backend.connected
                                    fillColor: themes.button
                                    labelColor: themes.buttonText
                                    borderColor: themes.buttonBorder
                                    pressedColor: accent
                                    onClicked: backend.sendTrackerReset(resetType.currentText)
                                }
                                Item { Layout.fillWidth: true }
                            }
                            RowLayout {
                                Layout.columnSpan: 3
                                Layout.fillWidth: true
                                TextField {
                                    id: receiverAddress
                                    Layout.fillWidth: true
                                    implicitHeight: 42
                                    placeholderText: "Receiver address"
                                }
                                ActionButton {
                                    text: "Set receiver"
                                    Layout.minimumWidth: 160
                                    Layout.preferredWidth: 160
                                    Layout.preferredHeight: 42
                                    enabled: backend.connected
                                    fillColor: themes.button
                                    labelColor: themes.buttonText
                                    borderColor: themes.buttonBorder
                                    pressedColor: accent
                                    onClicked: backend.sendTrackerSet(receiverAddress.text)
                                }
                            }
                        }
                    }
                }
            }

            // Receiver tab
            ScrollView {
                clip: true
                ColumnLayout {
                    width: parent.width
                    spacing: 10
                    Rectangle {
                        Layout.fillWidth: true
                        color: paper
                        radius: 10
                        border.color: line
                        implicitHeight: receiverActions.implicitHeight + 28
                        GridLayout {
                            id: receiverActions
                            anchors.fill: parent
                            anchors.margins: 14
                            columns: 3
                            columnSpacing: 10
                            rowSpacing: 1
                            Repeater {
                                model: [
                                    {label: "Info", cmd: "info"}, {label: "List trackers", cmd: "list"},
                                    {label: "Reboot", cmd: "reboot"}, {label: "Pair", cmd: "pair"},
                                    {label: "DFU", cmd: "dfu"}
                                ]
                                delegate: ActionButton {
                                    Layout.fillWidth: true
                                    Layout.minimumWidth: 120
                                    Layout.preferredHeight: 44
                                    fillColor: themes.button
                                    labelColor: themes.buttonText
                                    borderColor: themes.buttonBorder
                                    pressedColor: accent
                                    text: modelData.label
                                    enabled: backend.connected
                                    ToolTip.visible: hovered && backend.tooltipsEnabled
                                    ToolTip.text: commandTooltip(modelData.label)
                                    onClicked: backend.sendCommand(modelData.cmd)
                                }
                            }
                            Repeater {
                                model: [
                                    {label: "Remove last", cmd: "remove"}, {label: "Exit pairing", cmd: "exit"},
                                    {label: "Clear trackers", cmd: "clear"}, {label: "Uptime", cmd: "uptime"},
                                    {label: "Meow!", cmd: "meow"}
                                ]
                                delegate: ActionButton {
                                    Layout.fillWidth: true
                                    Layout.minimumWidth: 120
                                    Layout.preferredHeight: 44
                                    fillColor: themes.button
                                    labelColor: themes.buttonText
                                    borderColor: themes.buttonBorder
                                    pressedColor: accent
                                    text: modelData.label
                                    enabled: backend.connected
                                    ToolTip.visible: hovered && backend.tooltipsEnabled
                                    ToolTip.text: commandTooltip(modelData.label)
                                    onClicked: backend.sendCommand(modelData.cmd)
                                }
                            }
                            RowLayout {
                                Layout.columnSpan: 3
                                Layout.fillWidth: true
                                TextField {
                                    id: trackerAddress
                                    Layout.fillWidth: true
                                    implicitHeight: 42
                                    placeholderText: "Tracker address to add"
                                }
                                ActionButton {
                                    text: "Add tracker"
                                    Layout.minimumWidth: 160
                                    Layout.preferredWidth: 160
                                    Layout.preferredHeight: 42
                                    enabled: backend.connected
                                    fillColor: themes.button
                                    labelColor: themes.buttonText
                                    borderColor: themes.buttonBorder
                                    pressedColor: accent
                                    onClicked: backend.sendReceiverAdd(trackerAddress.text)
                                }
                            }
                        }
                    }
                }
            }

            ScrollView {
                clip: true
                ColumnLayout {
                    width: parent.width
                    spacing: 10
                    Rectangle {
                        Layout.fillWidth: true
                        color: paper
                        radius: 10
                        border.color: line
                        implicitHeight: firmwareLayout.implicitHeight + 36
                        ColumnLayout {
                            id: firmwareLayout
                            anchors.fill: parent
                            anchors.margins: 18
                            spacing: 12
                            Label { text: "Firmware source"; color: ink; font.pixelSize: 15; font.weight: Font.DemiBold }
                            Label {
                                visible: backend.firmwareSource === "local"
                                text: "Choose a local .uf2 or .hex file when you flash."
                                color: muted
                                wrapMode: Text.Wrap
                                Layout.fillWidth: true
                            }
                            // Firmware repo select
                            ComboBox {
                                id: sourceSelector
                                Layout.fillWidth: true
                                implicitHeight: 42
                                model: ["Main", "Kounocom", "External URL", "Local file"]
                                currentIndex: ["main", "kounocom", "custom", "local"].indexOf(backend.firmwareSource)
                                onActivated: backend.setFirmwareSource(["main", "kounocom", "custom", "local"][currentIndex])
                                ToolTip.visible: hovered && backend.tooltipsEnabled
                                ToolTip.text: currentText === "Main" ? "Main firmware repo"
                                    : currentText === "Kounocom" ? "Backup firmware option"
                                    : currentText === "External URL" ? "Custom firmware repo"
                                    : "Choose a local firmware file"
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                visible: backend.firmwareSource === "local"
                                ActionButton {
                                    text: "Choose firmware file"
                                    Layout.preferredWidth: 190
                                    Layout.preferredHeight: 42
                                    fillColor: themes.button
                                    labelColor: themes.buttonText
                                    borderColor: themes.buttonBorder
                                    pressedColor: accent
                                    onClicked: backend.chooseLocalFirmware()
                                }
                                Label {
                                    Layout.fillWidth: true
                                    text: backend.localFirmwarePath
                                        ? backend.localFirmwarePath.split(/[\\/]/).pop()
                                        : "No file selected"
                                    color: backend.localFirmwarePath ? ink : muted
                                    elide: Text.ElideMiddle
                                }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                visible: backend.firmwareSource === "custom"
                                TextField {
                                    id: customRepo
                                    Layout.fillWidth: true
                                    implicitHeight: 42
                                    placeholderText: "External GitHub latest-release API URL"
                                    text: backend.customFirmwareRepo
                                    ToolTip.visible: hovered && backend.tooltipsEnabled
                                    ToolTip.text: "Custom firmware repo"
                                }
                                ActionButton {
                                    text: "Save URL"
                                    Layout.preferredWidth: 104
                                    Layout.preferredHeight: 42
                                    fillColor: themes.button
                                    labelColor: themes.buttonText
                                    borderColor: themes.buttonBorder
                                    pressedColor: accent
                                    onClicked: backend.setCustomFirmwareRepo(customRepo.text)
                                }
                            }
                            Rectangle { Layout.fillWidth: true; height: 1; color: line }
                            Label {
                                text: "Firmware image"
                                color: ink
                                font.pixelSize: 15
                                font.weight: Font.DemiBold
                                visible: backend.firmwareSource !== "local"
                            }
                            // Fill the dropdown menu with latest releases
                            // Button to open firmware popup
                            ComboBox {
                                id: firmwareSelector
                                Layout.fillWidth: true
                                implicitHeight: 42
                                visible: backend.firmwareSource !== "local"
                                model: {
                                    var query = firmwareSearch.text.trim()
                                    if (!query)
                                        return backend.firmwareOptions
                                    return backend.firmwareOptions.filter(function(name) {
                                        return name !== "Select firmware"
                                            && name.toLowerCase().indexOf(query.toLowerCase()) !== -1
                                    })
                                }
                                currentIndex: model.indexOf(backend.selectedFirmware)
                                onActivated: backend.selectFirmware(currentText)
                                ToolTip.visible: hovered && backend.tooltipsEnabled
                                ToolTip.text: "Select the Firmware version for your smolslime"
                                popup: Popup {
                                    y: firmwareSelector.height
                                    width: firmwareSelector.width
                                    implicitHeight: popupContent.implicitHeight + topPadding + bottomPadding
                                    onOpened: {
                                        firmwareSearch.text = ""
                                        firmwareSearch.forceActiveFocus()
                                    }

                                    background: Rectangle {
                                        color: paper
                                        border.color: line
                                        radius: 6
                                    }

                                    contentItem: ColumnLayout {
                                        id: popupContent
                                        spacing: 6
                                        // Search bar
                                        TextField {
                                            id: firmwareSearch
                                            Layout.fillWidth: true
                                            implicitHeight: 42
                                            placeholderText: "Search firmware or paste a .hex/.uf2 URL"
                                            onTextChanged: {
                                                var pasted = text.trim()
                                                if (!/^https?:\/\//i.test(pasted))
                                                    return
                                                var path = pasted.split(/[?#]/, 1)[0]
                                                var filename = path.substring(path.lastIndexOf("/") + 1)
                                                if (!/\.(uf2|hex)$/i.test(filename))
                                                    return
                                                try {
                                                    text = decodeURIComponent(filename)
                                                } catch (error) {
                                                    text = filename
                                                }
                                            }
                                        }
                                        ListView {
                                            clip: true
                                            Layout.fillWidth: true
                                            Layout.preferredHeight: Math.min(contentHeight, 280)
                                            model: firmwareSelector.model
                                            delegate: firmwareSelector.delegate
                                        }
                                    }
                                }
                                delegate: ItemDelegate {
                                    id: firmwareOption
                                    required property int index
                                    required property string modelData
                                    width: firmwareSelector.popup.width
                                    highlighted: firmwareSelector.highlightedIndex === index

                                    background: Rectangle {
                                        radius: 6
                                        color: backend.firmwareFavorites.indexOf(firmwareOption.modelData) >= 0
                                            ? Qt.rgba(accent.r, accent.g, accent.b, 0.18)
                                            : firmwareOption.highlighted
                                                ? Qt.rgba(accent.r, accent.g, accent.b, 0.08)
                                                : "transparent"
                                    }
                                    onClicked: {
                                        backend.selectFirmware(modelData)
                                        firmwareSelector.popup.close()
                                    }

                                    contentItem: RowLayout {
                                        spacing: 8
                                        Label {
                                            // R-Click Hint (Middle-Click on mac)
                                            visible: firmwareOption.modelData !== "Select firmware"
                                                && firmwareOption.modelData !== "Custom firmware file..."
                                                && !firmwareOption.modelData.toLowerCase().startsWith("http")
                                            text: backend.firmwareFavorites.indexOf(firmwareOption.modelData) >= 0 ? "★" : "☆"
                                            color: backend.firmwareFavorites.indexOf(firmwareOption.modelData) >= 0 ? accent : muted
                                        }
                                        Label {
                                            Layout.fillWidth: true
                                            text: firmwareOption.modelData
                                            color: ink
                                            elide: Text.ElideRight
                                        }
                                    }

                                    // Right click (or middle click on mac)
                                    TapHandler {
                                        acceptedButtons: Qt.RightButton | Qt.MiddleButton
                                        onTapped: backend.toggleFirmwareFavorite(firmwareOption.modelData)
                                    }
                                }
                            }
                            // Loading bar
                            RowLayout {
                                Layout.fillWidth: true
                                ActionButton {
                                    text: "Flash firmware"
                                    Layout.preferredWidth: 156
                                    Layout.preferredHeight: 44
                                    enabled: backend.connected
                                    fillColor: themes.action
                                    labelColor: themes.actionText
                                    borderColor: themes.action
                                    pressedColor: accent
                                    ToolTip.visible: hovered && backend.tooltipsEnabled
                                    ToolTip.text: "Upgrade your firmware!"
                                    onClicked: backend.flashFirmware(firmwareSearch.text, firmwareSelector.currentText)
                                }
                                ProgressBar {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 6
                                    from: 0
                                    to: 1
                                    value: backend.progress
                                    visible: backend.progress > 0 && backend.progress < 1
                                }
                            }
                        }
                    }
                }
            }

            // Settings tab
            ScrollView {
                clip: true
                ColumnLayout {
                    width: parent.width
                    spacing: 10
                    Rectangle {
                        Layout.fillWidth: true
                        color: paper
                        radius: 10
                        border.color: line
                        implicitHeight: settingsLayout.implicitHeight + 28
                        ColumnLayout {
                            id: settingsLayout
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 12
                            Label { text: "Color theme"; color: ink; font.bold: true }
                            ComboBox {
                                id: themeSelector
                                Layout.fillWidth: true
                                implicitHeight: 42
                                model: ["Dark Green", "Dark Blue", "Dark", "Light"]
                                currentIndex: Math.max(0, model.indexOf(backend.theme))
                                onActivated: backend.setTheme(currentText)
                            }
                            // Buttonssss
                            RowLayout {
                                Layout.fillWidth: true
                                ActionButton {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 42
                                    text: backend.tooltipsEnabled ? "Disable Tooltips" : "Enable Tooltips"
                                    fillColor: themes.button
                                    labelColor: themes.buttonText
                                    borderColor: themes.buttonBorder
                                    pressedColor: accent
                                    ToolTip.visible: hovered && backend.tooltipsEnabled
                                    ToolTip.text: "Yk what each button does? Turn off tooltips!"
                                    onClicked: backend.setTooltipsEnabled(!backend.tooltipsEnabled)
                                }
                                ActionButton {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 42
                                    text: "Open GitHub Repo"
                                    fillColor: themes.button
                                    labelColor: themes.buttonText
                                    borderColor: themes.buttonBorder
                                    pressedColor: accent
                                    ToolTip.visible: hovered && backend.tooltipsEnabled
                                    ToolTip.text: "github.com/ICantMakeThings/SmolSlimeConfigurator"
                                    onClicked: backend.openRepository()
                                }
                            }
                            Label {
                                Layout.alignment: Qt.AlignRight
                                text: "SmolSlimeConfigurator Version 11 (" + backend.platformName + ")"
                                color: muted
                                font.pixelSize: 11
                            }
                        }
                    }
                }
            }
        }

        // CLI
        Item {
            id: consolePanel
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumHeight: 150
            Layout.preferredHeight: 150
            Rectangle {
                anchors.fill: parent
                color: themes.background
                radius: 10
                border.color: line
            }
            Flickable {
                id: consoleScroll
                anchors.fill: parent
                anchors.margins: 1
                clip: true
                contentWidth: width
                contentHeight: consoleArea.height
                boundsBehavior: Flickable.StopAtBounds

                TextArea {
                    id: consoleArea
                    width: consoleScroll.width
                    height: Math.max(consoleScroll.height, contentHeight)
                    topPadding: 38
                    rightPadding: 76
                    readOnly: true
                    textFormat: TextEdit.RichText
                    wrapMode: TextEdit.Wrap
                    selectByMouse: true
                    background: Rectangle { color: "transparent" }
                }

                ScrollBar.vertical: ScrollBar {
                    id: consoleScrollBar
                    policy: ScrollBar.AsNeeded
                    width: 8
                    background: Rectangle {
                        color: "transparent"
                        radius: width / 2
                    }
                    contentItem: Rectangle {
                        radius: width / 2
                        color: consoleScrollBar.pressed ? accent : muted
                        opacity: consoleScrollBar.active ? 0.8 : 0.35
                        Behavior on opacity { NumberAnimation { duration: 150 } }
                    }
                }
            }
            ToolButton {
                anchors.top: parent.top
                anchors.right: parent.right
                anchors.topMargin: 4
                anchors.rightMargin: 6
                text: " X "
                font.pixelSize: 12
                onClicked: consoleArea.clear()
                ToolTip.visible: hovered && backend.tooltipsEnabled
                ToolTip.text: "Clear"
                background: Rectangle {
                    color: paper
                    border.color: line
                    radius: 4
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            TextField {
                id: commandInput
                Layout.fillWidth: true
                implicitHeight: 42
                placeholderText: "Send a serial command..."
                enabled: backend.connected
                onAccepted: sendCustomCommand()
            }
            ActionButton {
                text: "↵"
                Layout.preferredWidth: 92
                Layout.preferredHeight: 42
                enabled: backend.connected
                fillColor: themes.action
                labelColor: themes.actionText
                borderColor: themes.action
                pressedColor: accent
                onClicked: sendCustomCommand()
            }
        }
    }
    }

    function sendCustomCommand() {
        backend.sendCommand(commandInput.text)
        commandInput.clear()
    }

    function commandTooltip(label) {
        const tooltips = {
            "Info": "Get device information",
            "Reboot": "Soft reset the device",
            "Scan": "Restart sensor scan",
            "Calibrate": "Calibrate sensor ZRO",
            "6-side calibration": "Calibrate 6-side accelerometer",
            "Clear magnetometer": "Clear magnetometer calibration",
            "Battery": "Get battery information",
            "Pair": "Enter pairing mode",
            "Clear pairing": "Clear pairing data",
            "Clear trackers": "Clear stored devices",
            "DFU": "Enter DFU bootloader (if available)",
            "Uptime": "Get device uptime",
            "Debug log": "Print debug log",
            "Meow!": "Meow!",
            "List trackers": "Get paired devices",
            "Remove last": "Remove last paired device",
            "Exit pairing": "Exit pairing mode"
        }
        return tooltips[label] || ""
    }
}