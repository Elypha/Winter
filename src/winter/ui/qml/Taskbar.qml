pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Effects
import QtQuick.Window
import "ChartScale.js" as ChartScale

Window {
    id: root
    objectName: "taskbarOverlay"

    required property QtObject view
    property string displayMode: "full"
    property bool vertical: false
    property string taskbarEdge: "bottom"
    property bool useLightForeground: true
    readonly property var chart: root.view.networkChart
    readonly property var colors: root.view.taskbarColors
    readonly property var textStyle: root.view.taskbarText
    readonly property var size: root.view.taskbarSize
    readonly property var position: root.view.taskbarPosition
    readonly property var menuColors: root.view.controlCenterColors
    readonly property var menuTextStyle: root.view.controlCenterText
    readonly property color foregroundColor: hsla(
        useLightForeground
            ? colors.foreground_on_dark
            : colors.foreground_on_light
    )
    readonly property int rowHeight: size.row_height
    readonly property var tabularNumeralFeatures: ({ "tnum": 1 })

    visible: false
    color: "transparent"
    title: "Winter"
    flags: Qt.FramelessWindowHint
           | Qt.Tool
           | Qt.WindowStaysOnTopHint
           | Qt.WindowDoesNotAcceptFocus

    function hsla(channels) {
        return Qt.hsla(
            channels[0] / 360,
            channels[1] / 100,
            channels[2] / 100,
            channels[3]
        )
    }

    function rate(value) {
        const megabytes = value / 1048576
        if (megabytes >= 0.1) {
            return {
                number: megabytes.toFixed(megabytes < 10 ? 2 : 1),
                unit: "M"
            }
        }
        return {
            number: (value / 1024).toFixed(1),
            unit: "K"
        }
    }

    function percent(value) {
        return isNaN(value) ? "--" : Math.round(value) + "%"
    }

    function watts(value) {
        return isNaN(value) ? "--" : Math.round(value) + "W"
    }

    function memory(value) {
        return isNaN(value) ? "--" : (value / 1073741824).toFixed(1)
    }

    function memoryFraction(used, total) {
        if (isNaN(used) || isNaN(total) || total <= 0)
            return 0
        return Math.max(0, Math.min(1, used / total))
    }

    function usageFraction(value) {
        return isNaN(value) ? 0 : Math.max(0, Math.min(1, value / 100))
    }

    function usageColor(value) {
        const lower = root.colors.memory_bar_fill_start
        const upper = root.colors.memory_bar_fill_end
        const bounded = isNaN(value) ? 10 : Math.max(10, Math.min(90, value))
        const amount = (bounded - 10) / 80
        return Qt.hsla(
            (lower[0] + (upper[0] - lower[0]) * amount) / 360,
            (lower[1] + (upper[1] - lower[1]) * amount) / 100,
            (lower[2] + (upper[2] - lower[2]) * amount) / 100,
            lower[3] + (upper[3] - lower[3]) * amount
        )
    }

    Rectangle {
        id: surface
        anchors.centerIn: parent
        width: root.vertical ? root.height : root.width
        height: root.vertical ? root.width : root.height
        rotation: root.taskbarEdge === "right" ? 90 : (root.vertical ? -90 : 0)
        transformOrigin: Item.Center
        color: "transparent"

        Row {
            anchors.fill: parent
            anchors.leftMargin: root.position.padding_x
            anchors.rightMargin: anchors.leftMargin
            spacing: 0

            NetworkBlock {
                width: root.displayMode === "full"
                       ? root.size.network_width_full
                       : root.displayMode === "compact"
                         ? root.size.network_width_compact
                         : root.size.network_width_minimal
                height: parent.height
            }

            Item { width: root.position.network_icons_gap; height: 1 }

            HardwareIcons {
                width: root.size.icons_width
                height: parent.height
            }

            Item { width: root.position.icons_usage_gap; height: 1 }

            UsageColumn {
                width: root.size.usage_width
                height: parent.height
            }

            Item { width: root.position.usage_power_gap; height: 1 }

            MetricColumn {
                width: root.size.power_width
                height: parent.height
                topValue: root.watts(root.view.cpuWatts)
                bottomValue: root.watts(root.view.gpuWatts)
            }

            Item { width: root.position.power_memory_gap; height: 1 }

            MemoryColumn {
                width: root.displayMode === "full"
                       ? root.size.memory_width_full
                       : root.displayMode === "compact"
                         ? root.size.memory_width_compact
                         : root.size.memory_width_minimal
                height: parent.height
            }
        }

        TapHandler {
            acceptedButtons: Qt.LeftButton
            onDoubleTapped: root.view.openControlCenter()
        }

        TapHandler {
            acceptedButtons: Qt.RightButton
            onTapped: taskbarMenu.popup()
        }

        DragHandler {
            acceptedButtons: Qt.LeftButton
            target: null
            onActiveChanged: {
                if (active)
                    root.view.beginTaskbarDrag()
                else
                    root.view.endTaskbarDrag()
            }
            onActiveTranslationChanged: {
                if (active)
                    root.view.updateTaskbarDrag()
            }
        }
    }

    Menu {
        id: taskbarMenu
        popupType: Popup.Window
        implicitWidth: 184
        padding: 4
        spacing: 1

        TaskbarMenuItem {
            text: "Open Control Center"
            onTriggered: root.view.openControlCenter()
        }
        MenuSeparator {
            topPadding: 3
            bottomPadding: 3
            leftPadding: 6
            rightPadding: 6
            contentItem: Rectangle {
                implicitHeight: 1
                color: root.hsla(root.menuColors.divider)
            }
        }
        TaskbarMenuItem {
            text: "Exit"
            onTriggered: root.view.exitWinter()
        }

        background: Rectangle {
            radius: 8
            color: root.hsla(root.menuColors.surface_raised)
            border.width: 1
            border.color: root.hsla(root.menuColors.panel_border)
        }
    }

    component TaskbarMenuItem: MenuItem {
        id: menuItem
        implicitWidth: 176
        implicitHeight: 32
        leftPadding: 10
        rightPadding: 10
        hoverEnabled: true

        contentItem: Text {
            text: menuItem.text
            color: root.hsla(root.menuColors.text)
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
            font.family: root.menuTextStyle.family
            font.pixelSize: root.menuTextStyle.body_size
            font.weight: Font.Medium
        }

        background: Rectangle {
            radius: 5
            color: menuItem.highlighted || menuItem.hovered
                   ? root.hsla(root.menuColors.surface_hovered)
                   : "transparent"
        }
    }

    component NetworkBlock: Item {
        id: networkBlock

        property var samples: []
        property var scaleStates: ({})

        function maximum(fields) {
            let result = root.chart.minimum_axis_bytes_per_second
            for (let i = 0; i < samples.length; ++i) {
                for (let j = 0; j < fields.length; ++j)
                    result = Math.max(result, samples[i][fields[j]])
            }
            return ChartScale.niceBinaryMaximum(result, 2.5)
        }

        function refreshGraph() {
            samples = root.view.history.networkWindow()
            const now = Date.now()
            const delay = root.chart.scale_down_delay_seconds * 1000
            scaleStates = {
                upload: ChartScale.settle(
                    scaleStates.upload, maximum(["upload"]), now, delay
                ),
                download: ChartScale.settle(
                    scaleStates.download, maximum(["download"]), now, delay
                ),
                shared: ChartScale.settle(
                    scaleStates.shared,
                    maximum(["upload", "download"]),
                    now,
                    delay
                )
            }
            graph.requestPaint()
        }

        Canvas {
            id: graph
            anchors.fill: parent
            opacity: root.chart.line_opacity

            function coordinates(points, field, top, areaHeight, scale) {
                const result = []
                for (let j = 0; j < points.length; ++j) {
                    result.push({
                        x: width
                           - Math.min(root.chart.history_seconds,
                                      points[j].age)
                             / root.chart.history_seconds * width,
                        y: top + areaHeight - root.chart.padding_y
                           - points[j][field] / scale
                             * (areaHeight - root.chart.padding_y * 2)
                    })
                }
                return result
            }

            function trace(context, points) {
                context.beginPath()
                context.moveTo(points[0].x, points[0].y)
                for (let i = 1; i < points.length - 1; ++i) {
                    const middleX = (points[i].x + points[i + 1].x) / 2
                    const middleY = (points[i].y + points[i + 1].y) / 2
                    context.quadraticCurveTo(points[i].x, points[i].y, middleX, middleY)
                }
                const last = points[points.length - 1]
                context.lineTo(last.x, last.y)
            }

            function drawSeries(context, samples, field, colour, top, areaHeight, scale) {
                const points = coordinates(samples, field, top, areaHeight, scale)
                if (points.length < 2)
                    return

                trace(context, points)
                context.lineWidth = root.chart.line_width
                context.lineJoin = "round"
                context.lineCap = "round"
                context.strokeStyle = colour
                context.stroke()
            }

            onPaint: {
                const context = getContext("2d")
                context.clearRect(0, 0, width, height)
                if (networkBlock.samples.length < 2)
                    return
                if (root.view.networkChartSeriesLayout === "separate") {
                    const chartHalfHeight = root.rowHeight
                                            + root.position.row_gap
                    const chartTop = (height - chartHalfHeight * 2) / 2
                    drawSeries(context, networkBlock.samples, "upload",
                               root.hsla(root.chart.upload_color),
                               chartTop, chartHalfHeight,
                               networkBlock.scaleStates.upload.maximum)
                    drawSeries(context, networkBlock.samples, "download",
                               root.hsla(root.chart.download_color),
                               chartTop + chartHalfHeight, chartHalfHeight,
                               networkBlock.scaleStates.download.maximum)
                } else {
                    const sharedScale = networkBlock.scaleStates.shared.maximum
                    drawSeries(context, networkBlock.samples, "download",
                               root.hsla(root.chart.download_color), 0, height,
                               sharedScale)
                    drawSeries(context, networkBlock.samples, "upload",
                               root.hsla(root.chart.upload_color), 0, height,
                               sharedScale)
                }
            }

            Connections {
                target: root.view.history
                function onChanged() { networkBlock.refreshGraph() }
            }
            Connections {
                target: root.view
                function onConfigurationChanged() { networkBlock.refreshGraph() }
            }
        }

        Component.onCompleted: refreshGraph()

        Column {
            anchors.verticalCenter: parent.verticalCenter
            width: parent.width
            spacing: root.position.row_gap

            NetworkLine { formatted: root.rate(root.view.uploadRate) }
            NetworkLine { formatted: root.rate(root.view.downloadRate) }
        }
    }

    component NetworkLine: Item {
        required property var formatted
        width: parent.width
        height: root.rowHeight

        Text {
            anchors.left: parent.left
            anchors.right: unitText.left
            anchors.rightMargin: root.position.network_value_unit_gap
            height: parent.height
            verticalAlignment: Text.AlignVCenter
            horizontalAlignment: Text.AlignRight
            color: root.foregroundColor
            font.family: root.textStyle.metric_family
            font.pixelSize: root.textStyle.metric_size
            font.variableAxes: { "wght": root.textStyle.metric_weight }
            font.features: root.tabularNumeralFeatures
            font.hintingPreference: Font.PreferFullHinting
            renderType: Text.NativeRendering
            text: parent.formatted.number
        }
        Text {
            id: unitText
            anchors.right: parent.right
            width: root.size.network_unit_width
            height: parent.height
            verticalAlignment: Text.AlignVCenter
            horizontalAlignment: Text.AlignLeft
            color: root.foregroundColor
            font.family: root.textStyle.metric_family
            font.pixelSize: root.textStyle.metric_size
            font.variableAxes: { "wght": root.textStyle.metric_weight }
            font.features: root.tabularNumeralFeatures
            font.hintingPreference: Font.PreferFullHinting
            renderType: Text.NativeRendering
            text: parent.formatted.unit
        }
    }

    component HardwareIcons: Item {
        Column {
            anchors.verticalCenter: parent.verticalCenter
            width: parent.width
            spacing: root.position.row_gap

            HardwareIcon { sourceName: "cpu" }
            HardwareIcon { sourceName: "gpu" }
        }
    }

    component HardwareIcon: Item {
        required property string sourceName
        width: parent.width
        height: root.rowHeight

        Image {
            id: iconSource
            anchors.centerIn: parent
            anchors.verticalCenterOffset: root.position.icon_shift_down
            width: root.size.icon_size
            height: root.size.icon_size
            fillMode: Image.PreserveAspectFit
            smooth: true
            source: "assets/" + parent.sourceName + ".svg"
            visible: false
        }

        MultiEffect {
            anchors.fill: iconSource
            source: iconSource
            colorization: 1
            colorizationColor: root.foregroundColor
        }
    }

    component MetricColumn: Item {
        required property string topValue
        required property string bottomValue

        Column {
            anchors.verticalCenter: parent.verticalCenter
            width: parent.width
            spacing: root.position.row_gap

            MetricText { value: parent.parent.topValue }
            MetricText { value: parent.parent.bottomValue }
        }
    }

    component UsageColumn: Item {
        Column {
            anchors.verticalCenter: parent.verticalCenter
            width: parent.width
            spacing: root.position.row_gap

            UsageMeter { value: root.view.cpuPercent }
            UsageMeter { value: root.view.gpuPercent }
        }
    }

    component UsageMeter: Item {
        id: usageMeter
        required property real value
        width: parent.width
        height: root.rowHeight

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            anchors.verticalCenterOffset: root.position.memory_bar_shift_down
            height: parent.height - root.size.memory_bar_height_trim
            radius: root.size.memory_bar_radius
            color: root.hsla(
                root.useLightForeground
                    ? root.colors.memory_bar_track_on_dark
                    : root.colors.memory_bar_track_on_light
            )
            clip: true

            Rectangle {
                width: parent.width * root.usageFraction(usageMeter.value)
                height: parent.height
                radius: parent.radius
                color: root.usageColor(usageMeter.value)
            }
        }

        Item {
            anchors.right: parent.right
            anchors.rightMargin: root.position.memory_value_padding_left
            width: root.textStyle.memory_size * 2
            height: parent.height

            MeterText {
                anchors.right: parent.right
                width: implicitWidth
                height: parent.height
                text: root.percent(usageMeter.value)
            }
        }
    }

    component MetricText: Item {
        required property string value
        width: parent.width
        height: root.rowHeight

        Text {
            anchors.fill: parent
            verticalAlignment: Text.AlignVCenter
            horizontalAlignment: Text.AlignRight
            color: root.foregroundColor
            font.family: root.textStyle.metric_family
            font.pixelSize: root.textStyle.metric_size
            font.variableAxes: { "wght": root.textStyle.metric_weight }
            font.features: root.tabularNumeralFeatures
            font.hintingPreference: Font.PreferFullHinting
            renderType: Text.NativeRendering
            text: parent.value
        }
    }

    component MemoryColumn: Item {
        Column {
            anchors.verticalCenter: parent.verticalCenter
            width: parent.width
            spacing: root.position.row_gap

            MemoryMeter {
                value: root.view.memoryUsed
                total: root.view.memoryTotal
            }
            MemoryMeter {
                value: root.view.vramUsed
                total: root.view.vramTotal
            }
        }
    }

    component MemoryMeter: Item {
        id: memoryMeter
        required property real value
        required property real total
        width: parent.width
        height: root.rowHeight

        Rectangle {
            id: track
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            anchors.verticalCenterOffset: root.position.memory_bar_shift_down
            height: parent.height - root.size.memory_bar_height_trim
            radius: root.size.memory_bar_radius
            color: root.hsla(
                root.useLightForeground
                    ? root.colors.memory_bar_track_on_dark
                    : root.colors.memory_bar_track_on_light
            )
            clip: true

            Rectangle {
                width: parent.width * root.memoryFraction(
                    memoryMeter.value,
                    memoryMeter.total
                )
                height: parent.height
                radius: parent.radius
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop {
                        position: 0.0
                        color: root.hsla(root.colors.memory_bar_fill_start)
                    }
                    GradientStop {
                        position: 1.0
                        color: root.hsla(root.colors.memory_bar_fill_end)
                    }
                }
            }

        }

        MeterText {
            anchors.fill: parent
            anchors.leftMargin: root.position.memory_value_padding_left
            horizontalAlignment: Text.AlignLeft
            text: root.memory(memoryMeter.value)
        }
    }

    component MeterText: Text {
        verticalAlignment: Text.AlignVCenter
        color: root.foregroundColor
        font.family: root.textStyle.memory_family
        font.pixelSize: root.textStyle.memory_size
        font.variableAxes: { "wght": root.textStyle.memory_weight }
        font.features: root.tabularNumeralFeatures
        font.hintingPreference: Font.PreferFullHinting
        renderType: Text.NativeRendering
    }
}
