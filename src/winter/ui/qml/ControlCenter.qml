pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import QtQuick.Window

ApplicationWindow {
    id: root
    objectName: "controlCenter"

    required property QtObject view
    property int currentTab: 0
    property var historyPoints: []
    readonly property var colors: root.view.controlCenterColors
    readonly property var typography: root.view.controlCenterText
    readonly property int currentThemeIndex:
        root.view.controlCenterTheme === "dark" ? 1 : 0
    readonly property var tabularNumeralFeatures: ({ "tnum": 1 })

    width: 1280
    height: 860
    minimumWidth: 880
    minimumHeight: 660
    visible: false
    color: hsla(colors.window)
    title: "Winter Control Center"
    flags: Qt.Window
    palette.window: hsla(colors.window)
    palette.windowText: hsla(colors.heading)
    palette.base: hsla(colors.input)
    palette.alternateBase: hsla(colors.alternate_input)
    palette.text: hsla(colors.text)
    palette.button: hsla(colors.button)
    palette.buttonText: hsla(colors.button_text)
    palette.highlight: hsla(colors.accent)
    palette.highlightedText: hsla(colors.accent_text)
    palette.placeholderText: hsla(colors.placeholder)

    function hsla(channels) {
        return Qt.hsla(
            channels[0] / 360,
            channels[1] / 100,
            channels[2] / 100,
            channels[3]
        )
    }

    function refreshHistory() {
        if (visible && currentTab === 0)
            historyPoints = view.history.controlCenterWindow()
    }

    Connections {
        target: root.view.history
        enabled: root.visible && root.currentTab === 0
        function onChanged() { root.refreshHistory() }
    }

    onVisibleChanged: {
        if (!visible)
            return
        if (currentTab === 0)
            refreshHistory()
        else
            view.refreshAvailableSources()
    }
    onCurrentTabChanged: {
        if (!visible)
            return
        if (currentTab === 0)
            refreshHistory()
        else
            view.refreshAvailableSources()
    }

    background: Rectangle { color: root.hsla(root.colors.window) }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 64
            color: root.hsla(root.colors.surface)

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 24
                anchors.rightMargin: 20
                spacing: 20

                Rectangle {
                    id: tabControl
                    objectName: "sectionTabs"
                    Layout.preferredWidth: 238
                    Layout.preferredHeight: 38
                    radius: 10
                    color: root.hsla(root.colors.input)
                    border.width: 1
                    border.color: root.hsla(root.colors.panel_border)

                    readonly property real segmentWidth: (width - 9) / 2

                    Rectangle {
                        objectName: "sectionTabThumb"
                        x: 3 + root.currentTab * (tabControl.segmentWidth + 3)
                        y: 3
                        width: tabControl.segmentWidth
                        height: tabControl.height - 6
                        radius: 7
                        color: root.hsla(root.colors.surface_raised)
                        border.width: 1
                        border.color: root.hsla(root.colors.divider)

                        Behavior on x {
                            NumberAnimation {
                                duration: 160
                                easing.type: Easing.OutCubic
                            }
                        }
                    }

                    Row {
                        anchors.fill: parent
                        anchors.margins: 3
                        spacing: 3
                        TabChoice {
                            label: "Charts"
                            tabIndex: 0
                            width: (parent.width - 3) / 2
                            height: parent.height
                        }
                        TabChoice {
                            label: "Settings"
                            tabIndex: 1
                            width: (parent.width - 3) / 2
                            height: parent.height
                        }
                    }
                }

                Item { Layout.fillWidth: true }

                Rectangle {
                    id: themeControl
                    objectName: "themeTabs"
                    Layout.preferredWidth: 160
                    Layout.preferredHeight: 38
                    radius: 10
                    color: root.hsla(root.colors.input)
                    border.width: 1
                    border.color: root.hsla(root.colors.panel_border)

                    readonly property real segmentWidth: (width - 9) / 2

                    Rectangle {
                        objectName: "themeTabThumb"
                        x: 3 + root.currentThemeIndex
                               * (themeControl.segmentWidth + 3)
                        y: 3
                        width: themeControl.segmentWidth
                        height: themeControl.height - 6
                        radius: 7
                        color: root.hsla(root.colors.surface_raised)
                        border.width: 1
                        border.color: root.hsla(root.colors.divider)

                        Behavior on x {
                            NumberAnimation {
                                duration: 160
                                easing.type: Easing.OutCubic
                            }
                        }
                    }

                    Row {
                        anchors.fill: parent
                        anchors.margins: 3
                        spacing: 3
                        ThemeChoice {
                            label: "Light"
                            theme: "light"
                            width: (parent.width - 3) / 2
                            height: parent.height
                        }
                        ThemeChoice {
                            label: "Dark"
                            theme: "dark"
                            width: (parent.width - 3) / 2
                            height: parent.height
                        }
                    }
                }
            }

            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                height: 1
                color: root.hsla(root.colors.divider)
            }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: root.currentTab

            ScrollView {
                id: chartsPage
                clip: true
                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                ScrollBar.vertical.policy: ScrollBar.AsNeeded

                ColumnLayout {
                    width: chartsPage.availableWidth
                    spacing: 0

                    GridLayout {
                        id: chartGrid
                        Layout.fillWidth: true
                        Layout.leftMargin: 22
                        Layout.rightMargin: 22
                        Layout.topMargin: 18
                        Layout.bottomMargin: 18
                        columns: 3
                        columnSpacing: 12
                        rowSpacing: 12
                        readonly property real cardWidth:
                            (width - columnSpacing * 2) / 3
                        readonly property real cardHeight: cardWidth * 2 / 3

                        HistoryChart {
                            objectName: "networkHistoryChart"
                            Layout.row: 0
                            Layout.column: 0
                            Layout.columnSpan: 2
                            Layout.fillWidth: true
                            Layout.preferredHeight: chartGrid.cardHeight
                            themeColors: root.colors
                            typography: root.typography
                            points: root.historyPoints
                            title: "Network throughput"
                            valueFormat: "rate"
                            windowSeconds: root.view.controlCenterHistorySeconds
                            minimumMaximum:
                                root.view.networkChart[
                                    "minimum_axis_bytes_per_second"
                                ]
                            scaleDownDelaySeconds:
                                root.view.networkChart[
                                    "scale_down_delay_seconds"
                                ]
                            stackedSeries:
                                root.view.networkChartSeriesLayout
                                === "separate"
                            series: [
                                {
                                    key: "upload",
                                    label: "Upload",
                                    color: root.hsla(root.colors.chart_upload),
                                    format: "rate"
                                },
                                {
                                    key: "download",
                                    label: "Download",
                                    color: root.hsla(
                                        root.colors.chart_download
                                    ),
                                    format: "rate"
                                }
                            ]
                        }

                        HistoryChart {
                            objectName: "temperatureHistoryChart"
                            Layout.row: 1
                            Layout.column: 2
                            Layout.fillWidth: true
                            Layout.preferredHeight: chartGrid.cardHeight
                            themeColors: root.colors
                            typography: root.typography
                            points: root.historyPoints
                            title: "GPU temperature"
                            valueFormat: "celsius"
                            windowSeconds: root.view.controlCenterHistorySeconds
                            series: [
                                {
                                    key: "gpuCelsius",
                                    label: "GPU",
                                    color: root.hsla(
                                        root.colors.chart_temperature
                                    ),
                                    format: "celsius"
                                }
                            ]
                        }

                        ColumnLayout {
                            Layout.row: 0
                            Layout.column: 2
                            Layout.fillWidth: true
                            Layout.preferredHeight: chartGrid.cardHeight
                            spacing: chartGrid.rowSpacing

                            HistoryChart {
                                objectName: "ramHistoryChart"
                                Layout.fillWidth: true
                                Layout.preferredHeight:
                                    (chartGrid.cardHeight
                                     - chartGrid.rowSpacing) / 2
                                compact: true
                                themeColors: root.colors
                                typography: root.typography
                                points: root.historyPoints
                                title: "RAM usage"
                                valueFormat: "bytes"
                                fixedMaximum: root.view.memoryTotal
                                windowSeconds:
                                    root.view.controlCenterHistorySeconds
                                series: [
                                    {
                                        key: "memoryUsed",
                                        label: "RAM",
                                        color: root.hsla(
                                            root.colors.chart_cpu
                                        )
                                    }
                                ]
                            }

                            HistoryChart {
                                objectName: "vramHistoryChart"
                                Layout.fillWidth: true
                                Layout.preferredHeight:
                                    (chartGrid.cardHeight
                                     - chartGrid.rowSpacing) / 2
                                compact: true
                                themeColors: root.colors
                                typography: root.typography
                                points: root.historyPoints
                                title: "VRAM usage"
                                valueFormat: "bytes"
                                fixedMaximum: root.view.vramTotal
                                windowSeconds:
                                    root.view.controlCenterHistorySeconds
                                series: [
                                    {
                                        key: "vramUsed",
                                        label: "VRAM",
                                        color: root.hsla(
                                            root.colors.chart_gpu
                                        )
                                    }
                                ]
                            }
                        }

                        HistoryChart {
                            objectName: "computeHistoryChart"
                            Layout.row: 1
                            Layout.column: 0
                            Layout.fillWidth: true
                            Layout.preferredHeight: chartGrid.cardHeight
                            themeColors: root.colors
                            typography: root.typography
                            points: root.historyPoints
                            title: "CPU / GPU usage"
                            valueFormat: "percent"
                            fixedMaximum: 100
                            windowSeconds: root.view.controlCenterHistorySeconds
                            series: [
                                {
                                    key: "cpu",
                                    label: "CPU",
                                    color: root.hsla(root.colors.chart_cpu)
                                },
                                {
                                    key: "gpu",
                                    label: "GPU",
                                    color: root.hsla(root.colors.chart_gpu)
                                }
                            ]
                        }

                        HistoryChart {
                            objectName: "powerHistoryChart"
                            Layout.row: 1
                            Layout.column: 1
                            Layout.fillWidth: true
                            Layout.preferredHeight: chartGrid.cardHeight
                            themeColors: root.colors
                            typography: root.typography
                            points: root.historyPoints
                            title: "CPU / GPU power"
                            valueFormat: "watts"
                            windowSeconds: root.view.controlCenterHistorySeconds
                            series: [
                                {
                                    key: "cpuWatts",
                                    label: "CPU",
                                    color: root.hsla(root.colors.chart_cpu),
                                    format: "watts"
                                },
                                {
                                    key: "gpuWatts",
                                    label: "GPU",
                                    color: root.hsla(root.colors.chart_gpu),
                                    format: "watts"
                                }
                            ]
                        }
                    }
                }
            }

            ScrollView {
                id: settingsPage
                clip: true
                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                ScrollBar.vertical.policy: ScrollBar.AsNeeded

                ColumnLayout {
                    width: settingsPage.availableWidth
                    spacing: 14

                    Item { Layout.preferredHeight: 12 }

                    RowLayout {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24

                        ColumnLayout {
                            spacing: 2
                            Text {
                                text: "Configuration"
                                color: root.hsla(root.colors.heading)
                                font.family: root.typography.display_family
                                font.pixelSize: root.typography.title_size
                                font.weight: Font.DemiBold
                            }
                            Text {
                                text: "Runtime and taskbar behaviour"
                                color: root.hsla(root.colors.muted_text)
                                font.family: root.typography.family
                                font.pixelSize: root.typography.body_size
                            }
                        }
                        Item { Layout.fillWidth: true }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        Layout.bottomMargin: 22
                        columns: 2
                        columnSpacing: 14
                        rowSpacing: 14

                        SettingsPanel {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 342
                            heading: "Network"
                            description: "Sampling source and graph behaviour"

                            FormLabel { text: "Adapter selection" }
                            AdapterSelector {
                                objectName: "networkAdapterSelector"
                                Layout.fillWidth: true
                                selection: root.view.networkAdapterSelection
                                automaticAdapter:
                                    root.view.automaticNetworkAdapter
                                adapterName: root.view.networkAdapterName
                                adapterModel: root.view.networkInterfaces
                                onAutomaticActivated:
                                    root.view.setNetworkAdapter("automatic", "")
                                onNamedActivated: adapter =>
                                    root.view.setNetworkAdapter(
                                        "named",
                                        adapter
                                    )
                            }

                            FormLabel { text: "Throughput chart layout" }
                            FormSegmentedControl {
                                id: throughputLayoutChoice
                                Layout.fillWidth: true
                                model: ["Shared", "Separate"]
                                currentIndex: root.view.networkChartSeriesLayout
                                              === "separate" ? 1 : 0
                                onActivated: index =>
                                    root.view.setNetworkChartSeriesLayout(
                                        index === 0 ? "shared" : "separate"
                                    )
                            }
                        }

                        SettingsPanel {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 342
                            heading: "Taskbar"
                            description: "Placement and fullscreen behaviour"

                            FormLabel { text: "Target monitor" }
                            FormComboBox {
                                id: monitorChoice
                                Layout.fillWidth: true
                                model: ["Automatic (primary)"].concat(root.view.monitors)
                                currentIndex: root.view.taskbarMonitor === ""
                                              ? 0
                                              : root.view.monitors.indexOf(
                                                    root.view.taskbarMonitor
                                                ) < 0
                                                ? -1
                                                : root.view.monitors.indexOf(
                                                      root.view.taskbarMonitor
                                                  ) + 1
                                onActivated: index =>
                                    root.view.setTaskbarMonitor(
                                        index === 0 ? null : currentText
                                    )
                            }

                            FormLabel { text: "Fullscreen visibility" }
                            FormToggle {
                                id: fullscreenChoice
                                Layout.fillWidth: true
                                text: "Keep the taskbar readout visible"
                                checked: root.view.visibleInFullscreen
                                onToggled:
                                    root.view.setVisibleInFullscreen(checked)
                            }

                            Item { Layout.fillHeight: true }

                            Rectangle {
                                Layout.fillWidth: true
                                height: 1
                                color: root.hsla(root.colors.divider)
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                Text {
                                    Layout.fillWidth: true
                                    text: "Restore the default taskbar offset"
                                    color: root.hsla(root.colors.muted_text)
                                    font.family: root.typography.family
                                    font.pixelSize: root.typography.detail_size
                                }
                                ActionButton {
                                    text: "Reset position"
                                    onClicked: root.view.resetTaskbarPosition()
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    component TabChoice: Item {
        id: tabChoice
        required property string label
        required property int tabIndex
        readonly property bool active: root.currentTab === tabIndex

        Text {
            anchors.centerIn: parent
            text: tabChoice.label
            color: tabChoice.active
                   ? root.hsla(root.colors.heading)
                   : root.hsla(root.colors.muted_text)
            font.family: root.typography.family
            font.pixelSize: root.typography.body_size
            font.weight: tabChoice.active ? Font.DemiBold : Font.Medium
        }
        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: root.currentTab = tabChoice.tabIndex
        }
    }

    component ThemeChoice: Item {
        id: themeChoice
        required property string label
        required property string theme
        readonly property bool active: root.view.controlCenterTheme === theme

        Text {
            anchors.centerIn: parent
            text: themeChoice.label
            color: themeChoice.active
                   ? root.hsla(root.colors.heading)
                   : root.hsla(root.colors.muted_text)
            font.family: root.typography.family
            font.pixelSize: root.typography.body_size
            font.weight: themeChoice.active ? Font.DemiBold : Font.Medium
        }
        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: root.view.setControlCenterTheme(themeChoice.theme)
        }
    }

    component SettingsPanel: Rectangle {
        id: settingsPanel
        property string heading
        property string description
        default property alias panelContent: contentColumn.data

        radius: 12
        color: root.hsla(root.colors.panel)
        border.width: 1
        border.color: root.hsla(root.colors.panel_border)

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 18
            spacing: 8

            Text {
                text: settingsPanel.heading
                color: root.hsla(root.colors.heading)
                font.family: root.typography.display_family
                font.pixelSize: root.typography.heading_size
                font.weight: Font.DemiBold
            }
            Text {
                text: settingsPanel.description
                color: root.hsla(root.colors.muted_text)
                font.family: root.typography.family
                font.pixelSize: root.typography.detail_size
            }
            Rectangle {
                Layout.fillWidth: true
                Layout.topMargin: 3
                Layout.bottomMargin: 3
                Layout.preferredHeight: 1
                color: root.hsla(root.colors.divider)
            }
            ColumnLayout {
                id: contentColumn
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 7
            }
        }
    }

    component FormLabel: Text {
        Layout.topMargin: 3
        color: root.hsla(root.colors.secondary_text)
        font.family: root.typography.family
        font.pixelSize: root.typography.body_size
        font.weight: Font.Medium
    }

    component AdapterSelector: Rectangle {
        id: adapterSelector
        required property string selection
        required property string automaticAdapter
        required property string adapterName
        required property var adapterModel
        signal automaticActivated()
        signal namedActivated(string adapter)
        readonly property bool automatic: selection === "automatic"
        readonly property int automaticIndex:
            adapterModel.indexOf(automaticAdapter)

        implicitHeight: 88
        radius: 9
        color: root.hsla(root.colors.input)
        border.width: 1
        border.color: root.hsla(root.colors.panel_border)

        Column {
            anchors.fill: parent
            anchors.margins: 4
            spacing: 2

            Item {
                id: automaticOption
                objectName: "automaticAdapterOption"
                width: parent.width
                height: 39

                Rectangle {
                    anchors.fill: parent
                    radius: 6
                    color: adapterSelector.automatic
                           ? root.hsla(root.colors.surface_raised)
                           : automaticMouse.containsMouse
                             ? root.hsla(root.colors.surface_hovered)
                             : "transparent"
                    border.width: adapterSelector.automatic ? 1 : 0
                    border.color: root.hsla(root.colors.divider)
                }

                Rectangle {
                    x: 10
                    anchors.verticalCenter: parent.verticalCenter
                    width: 16
                    height: 16
                    radius: 8
                    color: "transparent"
                    border.width: 1.5
                    border.color: adapterSelector.automatic
                                  ? root.hsla(root.colors.accent)
                                  : root.hsla(root.colors.muted_text)

                    Rectangle {
                        anchors.centerIn: parent
                        width: 8
                        height: 8
                        radius: 4
                        visible: adapterSelector.automatic
                        color: root.hsla(root.colors.accent)
                    }
                }

                Text {
                    id: automaticLabel
                    x: 36
                    anchors.verticalCenter: parent.verticalCenter
                    text: "Automatic"
                    color: root.hsla(root.colors.text)
                    font.family: root.typography.family
                    font.pixelSize: root.typography.body_size
                    font.weight: adapterSelector.automatic
                                 ? Font.DemiBold : Font.Medium
                }

                Text {
                    anchors.left: automaticLabel.right
                    anchors.leftMargin: 5
                    anchors.right: parent.right
                    anchors.rightMargin: 10
                    anchors.verticalCenter: parent.verticalCenter
                    text: "(" + (adapterSelector.automaticAdapter
                                  || "No active route") + ")"
                    color: root.hsla(root.colors.muted_text)
                    elide: Text.ElideMiddle
                    font.family: root.typography.family
                    font.pixelSize: root.typography.detail_size
                    font.features: root.tabularNumeralFeatures
                }

                MouseArea {
                    id: automaticMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: adapterSelector.automaticActivated()
                }
            }

            Item {
                id: namedOption
                objectName: "specificAdapterOption"
                width: parent.width
                height: 39

                Rectangle {
                    anchors.fill: parent
                    radius: 6
                    color: !adapterSelector.automatic
                           ? root.hsla(root.colors.surface_raised)
                           : namedMouse.containsMouse
                             ? root.hsla(root.colors.surface_hovered)
                             : "transparent"
                    border.width: adapterSelector.automatic ? 0 : 1
                    border.color: root.hsla(root.colors.divider)
                }

                Rectangle {
                    x: 10
                    anchors.verticalCenter: parent.verticalCenter
                    width: 16
                    height: 16
                    radius: 8
                    color: "transparent"
                    border.width: 1.5
                    border.color: !adapterSelector.automatic
                                  ? root.hsla(root.colors.accent)
                                  : root.hsla(root.colors.muted_text)

                    Rectangle {
                        anchors.centerIn: parent
                        width: 8
                        height: 8
                        radius: 4
                        visible: !adapterSelector.automatic
                        color: root.hsla(root.colors.accent)
                    }
                }

                Text {
                    id: namedLabel
                    x: 36
                    anchors.verticalCenter: parent.verticalCenter
                    text: "Specific adapter"
                    color: root.hsla(root.colors.text)
                    font.family: root.typography.family
                    font.pixelSize: root.typography.body_size
                    font.weight: !adapterSelector.automatic
                                 ? Font.DemiBold : Font.Medium
                }

                MouseArea {
                    id: namedMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        if (adapterCombo.currentText)
                            adapterSelector.namedActivated(
                                adapterCombo.currentText
                            )
                    }
                }

                FormComboBox {
                    id: adapterCombo
                    objectName: "networkInterfaceChoice"
                    anchors.left: namedLabel.right
                    anchors.leftMargin: 12
                    anchors.right: parent.right
                    anchors.rightMargin: 4
                    anchors.verticalCenter: parent.verticalCenter
                    height: 31
                    enabled: !adapterSelector.automatic
                    model: adapterSelector.adapterModel
                    currentIndex: {
                        if (!adapterSelector.automatic)
                            return adapterSelector.adapterModel.indexOf(
                                adapterSelector.adapterName
                            )
                        return adapterSelector.automaticIndex >= 0
                            ? adapterSelector.automaticIndex : 0
                    }
                    onActivated:
                        adapterSelector.namedActivated(currentText)
                }
            }
        }
    }

    component FormSegmentedControl: Rectangle {
        id: segmented
        property var model: []
        property int currentIndex: 0
        signal activated(int index)
        readonly property int segmentCount: Math.max(1, model.length)
        readonly property real segmentWidth:
            (width - 6 - (segmentCount - 1) * 3) / segmentCount

        implicitHeight: 40
        radius: 9
        color: root.hsla(root.colors.input)
        border.width: 1
        border.color: root.hsla(root.colors.panel_border)

        Rectangle {
            x: 3 + segmented.currentIndex * (segmented.segmentWidth + 3)
            y: 3
            width: segmented.segmentWidth
            height: segmented.height - 6
            radius: 6
            color: root.hsla(root.colors.surface_raised)
            border.width: 1
            border.color: root.hsla(root.colors.divider)

            Behavior on x {
                NumberAnimation {
                    duration: 160
                    easing.type: Easing.OutCubic
                }
            }
        }

        Row {
            anchors.fill: parent
            anchors.margins: 3
            spacing: 3

            Repeater {
                model: segmented.model
                delegate: Item {
                    id: segment
                    required property int index
                    required property var modelData
                    width: segmented.segmentWidth
                    height: parent.height

                    Rectangle {
                        anchors.fill: parent
                        radius: 6
                        visible: segmentMouse.containsMouse
                                 && segmented.currentIndex !== segment.index
                        color: root.hsla(root.colors.surface_hovered)
                    }

                    Text {
                        anchors.centerIn: parent
                        text: segment.modelData
                        color: segmented.currentIndex === segment.index
                               ? root.hsla(root.colors.heading)
                               : root.hsla(root.colors.muted_text)
                        font.family: root.typography.family
                        font.pixelSize: root.typography.body_size
                        font.weight: segmented.currentIndex === segment.index
                                     ? Font.DemiBold : Font.Medium
                    }

                    MouseArea {
                        id: segmentMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            segmented.activated(segment.index)
                        }
                    }
                }
            }
        }
    }

    component FormComboBox: ComboBox {
        id: control
        implicitHeight: 40
        leftPadding: 12
        rightPadding: 34
        opacity: enabled ? 1 : 0.48

        contentItem: Text {
            leftPadding: control.leftPadding
            rightPadding: control.rightPadding
            text: control.displayText
            color: root.hsla(root.colors.text)
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
            font.family: root.typography.family
            font.pixelSize: root.typography.body_size
            font.features: root.tabularNumeralFeatures
        }

        indicator: Text {
            x: control.width - width - 12
            y: (control.height - height) / 2 - 1
            text: "⌄"
            color: root.hsla(root.colors.muted_text)
            font.family: "Segoe UI Symbol"
            font.pixelSize: root.typography.heading_size
        }

        background: Rectangle {
            radius: 8
            color: control.down
                   ? root.hsla(root.colors.surface_hovered)
                   : root.hsla(root.colors.input)
            border.width: 1
            border.color: control.activeFocus
                          ? root.hsla(root.colors.accent)
                          : root.hsla(root.colors.panel_border)
        }

        delegate: ItemDelegate {
            id: delegateItem
            required property var modelData
            required property int index
            width: control.width - 8
            height: 36
            leftPadding: 10
            rightPadding: 10
            hoverEnabled: true
            highlighted: control.highlightedIndex === index
            contentItem: Text {
                text: delegateItem.modelData
                color: root.hsla(root.colors.text)
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
                font.family: root.typography.family
                font.pixelSize: root.typography.body_size
                font.features: root.tabularNumeralFeatures
            }
            background: Rectangle {
                radius: 6
                color: delegateItem.highlighted || delegateItem.hovered
                       ? root.hsla(root.colors.surface_hovered)
                       : "transparent"
            }
        }

        popup: Popup {
            y: control.height + 4
            width: control.width
            padding: 4
            implicitHeight: Math.min(contentItem.implicitHeight + 8, 248)
            contentItem: ListView {
                clip: true
                implicitHeight: contentHeight
                model: control.popup.visible ? control.delegateModel : null
                currentIndex: control.highlightedIndex
                ScrollIndicator.vertical: ScrollIndicator { }
            }
            background: Rectangle {
                radius: 9
                color: root.hsla(root.colors.surface_raised)
                border.width: 1
                border.color: root.hsla(root.colors.panel_border)
            }
        }
    }

    component FormToggle: CheckBox {
        id: toggle
        implicitHeight: 40
        spacing: 10

        indicator: Rectangle {
            implicitWidth: 34
            implicitHeight: 20
            x: 0
            y: (toggle.height - height) / 2
            radius: 10
            color: toggle.checked
                   ? root.hsla(root.colors.accent)
                   : root.hsla(root.colors.button)
            border.width: 1
            border.color: toggle.checked
                          ? root.hsla(root.colors.accent)
                          : root.hsla(root.colors.panel_border)

            Rectangle {
                x: toggle.checked ? parent.width - width - 3 : 3
                anchors.verticalCenter: parent.verticalCenter
                width: 14
                height: 14
                radius: 7
                color: toggle.checked
                       ? root.hsla(root.colors.accent_text)
                       : root.hsla(root.colors.muted_text)
                Behavior on x { NumberAnimation { duration: 110 } }
            }
        }

        contentItem: Text {
            leftPadding: toggle.indicator.width + toggle.spacing
            text: toggle.text
            color: root.hsla(root.colors.text)
            verticalAlignment: Text.AlignVCenter
            font.family: root.typography.family
            font.pixelSize: root.typography.body_size
        }
    }

    component ActionButton: Button {
        id: action
        implicitWidth: 112
        implicitHeight: 38

        contentItem: Text {
            text: action.text
            color: root.hsla(root.colors.button_text)
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            font.family: root.typography.family
            font.pixelSize: root.typography.body_size
            font.weight: Font.DemiBold
        }
        background: Rectangle {
            radius: 8
            color: action.down
                   ? root.hsla(root.colors.surface_hovered)
                   : root.hsla(root.colors.button)
            border.width: 1
            border.color: root.hsla(root.colors.panel_border)
        }
    }
}
