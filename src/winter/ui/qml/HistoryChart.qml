pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import "ChartScale.js" as ChartScale

Rectangle {
    id: root

    required property var themeColors
    required property var typography
    required property var points
    required property var series
    required property string title
    required property real windowSeconds
    property string valueFormat: "percent"
    property real fixedMaximum: NaN
    property real minimumMaximum: 0
    property real scaleDownDelaySeconds: 0
    property bool stackedSeries: false
    property bool compact: false
    property var hoveredPoint: null
    property real hoverX: 0
    readonly property int yTickCount: compact ? 3 : 5
    readonly property real plotTop: compact ? 4 : 8
    readonly property real plotBottomMargin: compact ? 15 : 18
    readonly property real plotVerticalInset: plotTop + plotBottomMargin
    readonly property real yAxisWidth: valueFormat === "rate" ? 62 : 48
    readonly property real plotLeft: yAxisWidth + 6
    readonly property var tabularNumeralFeatures: ({ "tnum": 1 })
    property real sharedMaximum: 1
    property var seriesMaximums: ({})
    property var scaleStates: ({})

    radius: 12
    color: hsla(themeColors.panel)
    border.width: 1
    border.color: hsla(themeColors.panel_border)

    function hsla(channels) {
        return Qt.hsla(
            channels[0] / 360,
            channels[1] / 100,
            channels[2] / 100,
            channels[3]
        )
    }

    function isNumber(value) {
        return typeof value === "number" && isFinite(value)
    }

    function formatBytes(value, axis) {
        const gigabyte = 1073741824
        const megabyte = 1048576
        if (value >= gigabyte || value === 0) {
            const amount = value / gigabyte
            const decimals = axis
                ? (Math.abs(amount - Math.round(amount)) < 0.05 ? 0 : 1)
                : (amount < 10 ? 2 : 1)
            return amount.toFixed(decimals) + " GB"
        }
        const amount = value / megabyte
        return amount.toFixed(axis ? 0 : 1) + " MB"
    }

    function formatValue(value, format) {
        if (!isNumber(value))
            return "N/A"
        if (format === "rate") {
            if (value >= 1073741824)
                return (value / 1073741824).toFixed(1) + " GB/s"
            if (value >= 1048576)
                return (value / 1048576).toFixed(
                    value < 10485760 ? 2 : 1
                ) + " MB/s"
            if (value >= 1024)
                return (value / 1024).toFixed(1) + " KB/s"
            return Math.round(value) + " B/s"
        }
        if (format === "bytes")
            return formatBytes(value, false)
        if (format === "watts")
            return value.toFixed(1) + " W"
        if (format === "celsius")
            return value.toFixed(0) + " °C"
        return value.toFixed(1) + "%"
    }

    function formatAxisValue(value, format) {
        if (!isNumber(value))
            return ""
        if (format === "rate") {
            if (value >= 1073741824)
                return (value / 1073741824).toFixed(1) + " GB/s"
            if (value >= 1048576)
                return (value / 1048576).toFixed(1) + " MB/s"
            if (value >= 1024)
                return (value / 1024).toFixed(0) + " KB/s"
            return Math.round(value) + " B/s"
        }
        if (format === "bytes")
            return formatBytes(value, true)
        if (format === "watts")
            return Math.round(value) + " W"
        if (format === "celsius")
            return Math.round(value) + " °C"
        return Math.round(value) + "%"
    }

    function formatAge(age) {
        if (!isNumber(age) || age < 1)
            return "now"
        const seconds = Math.round(age)
        const minutes = Math.floor(seconds / 60)
        const remainder = seconds % 60
        if (minutes === 0)
            return "−" + remainder + "s"
        if (remainder === 0)
            return "−" + minutes + "m"
        return "−" + minutes + "m " + remainder + "s"
    }

    function targetMaximumFor(keys) {
        let maximum = 0
        for (let pointIndex = 0; pointIndex < points.length; ++pointIndex) {
            const point = points[pointIndex]
            for (let keyIndex = 0; keyIndex < keys.length; ++keyIndex) {
                const value = point[keys[keyIndex]]
                if (isNumber(value))
                    maximum = Math.max(maximum, value)
            }
        }
        const target = Math.max(minimumMaximum, maximum)
        if (valueFormat === "bytes")
            return ChartScale.niceMaximum(target / 1073741824) * 1073741824
        if (valueFormat === "rate")
            return ChartScale.niceBinaryMaximum(target, 2.5)
        return ChartScale.niceMaximum(target)
    }

    function refreshMaximums() {
        const keys = []
        for (let index = 0; index < series.length; ++index)
            keys.push(series[index].key)

        if (isNumber(fixedMaximum)) {
            sharedMaximum = fixedMaximum
            const fixedSeriesMaximums = {}
            for (let fixedIndex = 0; fixedIndex < series.length; ++fixedIndex)
                fixedSeriesMaximums[series[fixedIndex].key] = fixedMaximum
            seriesMaximums = fixedSeriesMaximums
            scaleStates = ({})
            chartCanvas.requestPaint()
            return
        }

        const now = Date.now()
        const delay = scaleDownDelaySeconds * 1000
        const nextStates = {}
        const sharedState = ChartScale.settle(
            scaleStates.shared,
            targetMaximumFor(keys),
            now,
            delay
        )
        nextStates.shared = sharedState
        sharedMaximum = sharedState.maximum

        const nextSeriesMaximums = {}
        const previousSeriesStates = scaleStates.series || {}
        const nextSeriesStates = {}
        for (let seriesIndex = 0; seriesIndex < series.length; ++seriesIndex) {
            const key = series[seriesIndex].key
            const state = ChartScale.settle(
                previousSeriesStates[key],
                targetMaximumFor([key]),
                now,
                delay
            )
            nextSeriesStates[key] = state
            nextSeriesMaximums[key] = state.maximum
        }
        nextStates.series = nextSeriesStates
        scaleStates = nextStates
        seriesMaximums = nextSeriesMaximums
        chartCanvas.requestPaint()
    }

    function maximumForSeries(definition) {
        return isNumber(fixedMaximum)
               ? fixedMaximum : seriesMaximums[definition.key] || 1
    }

    function updateHover(mouseX) {
        const left = plotLeft
        const right = chartArea.width - 8
        if (points.length === 0 || mouseX < left || mouseX > right) {
            clearHover()
            return
        }
        const targetAge = (1 - (mouseX - left) / (right - left))
                          * windowSeconds
        let nearest = null
        let distance = Number.POSITIVE_INFINITY
        for (let index = 0; index < points.length; ++index) {
            const point = points[index]
            if (!isNumber(point.age) || point.age < 0
                    || point.age > windowSeconds)
                continue
            const candidateDistance = Math.abs(point.age - targetAge)
            if (candidateDistance < distance) {
                nearest = point
                distance = candidateDistance
            }
        }
        if (nearest === null) {
            clearHover()
            return
        }
        const snappedX = left
                         + (1 - nearest.age / windowSeconds) * (right - left)
        if (Math.abs(snappedX - mouseX) > 24) {
            clearHover()
            return
        }
        hoveredPoint = nearest
        hoverX = snappedX
        chartCanvas.requestPaint()
    }

    function clearHover() {
        hoveredPoint = null
        chartCanvas.requestPaint()
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.leftMargin: root.compact ? 12 : 16
        anchors.rightMargin: root.compact ? 10 : 14
        anchors.topMargin: root.compact ? 7 : 13
        anchors.bottomMargin: root.compact ? 7 : 12
        spacing: root.compact ? 4 : 8

        RowLayout {
            Layout.fillWidth: true
            spacing: 14

            Text {
                Layout.fillWidth: true
                text: root.title
                elide: Text.ElideRight
                color: root.hsla(root.themeColors.heading)
                font.family: root.typography.family
                font.pixelSize: root.compact
                                ? root.typography.body_size
                                : root.typography.heading_size
                font.weight: Font.DemiBold
            }

            Repeater {
                model: root.series
                delegate: RowLayout {
                    id: legendEntry
                    required property var modelData
                    spacing: 6

                    Rectangle {
                        Layout.preferredWidth: 3
                        Layout.preferredHeight: 14
                        radius: 2
                        color: legendEntry.modelData.color
                    }
                    Text {
                        text: legendEntry.modelData.label
                        color: root.hsla(root.themeColors.secondary_text)
                        font.family: root.typography.family
                        font.pixelSize: root.typography.detail_size
                        font.weight: Font.Medium
                    }
                }
            }
        }

        Item {
            id: chartArea
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            Canvas {
                id: chartCanvas
                anchors.fill: parent
                antialiasing: true

                function drawSeries(context, definition, plot, maximum) {
                    let drawing = false
                    context.beginPath()
                    for (let index = 0; index < root.points.length; ++index) {
                        const point = root.points[index]
                        const value = point[definition.key]
                        const age = point.age
                        if (!root.isNumber(value) || !root.isNumber(age)
                                || age < 0 || age > root.windowSeconds) {
                            drawing = false
                            continue
                        }
                        const x = plot.left
                                  + (1 - age / root.windowSeconds) * plot.width
                        const bounded = Math.max(0, Math.min(maximum, value))
                        const y = plot.bottom
                                  - bounded / maximum * plot.height
                        if (drawing)
                            context.lineTo(x, y)
                        else
                            context.moveTo(x, y)
                        drawing = true
                    }
                    context.lineWidth = 1.65
                    context.lineJoin = "round"
                    context.lineCap = "round"
                    context.strokeStyle = definition.color
                    context.stroke()
                }

                function drawHorizontalScale(
                    context,
                    plot,
                    divisions,
                    firstStep
                ) {
                    for (let step = firstStep;
                            step <= divisions; ++step) {
                        const ratio = step / divisions
                        const y = plot.top + ratio * plot.height
                        context.beginPath()
                        context.moveTo(plot.left, y)
                        context.lineTo(plot.right, y)
                        context.lineWidth = 1
                        context.strokeStyle = root.hsla(
                            root.themeColors.chart_grid
                        )
                        context.stroke()
                    }
                }

                function drawHoverMarker(context, definition, plot, maximum) {
                    if (root.hoveredPoint === null)
                        return
                    const value = root.hoveredPoint[definition.key]
                    if (!root.isNumber(value))
                        return
                    const x = plot.left
                              + (1 - root.hoveredPoint.age / root.windowSeconds)
                              * plot.width
                    const bounded = Math.max(0, Math.min(maximum, value))
                    const y = plot.bottom - bounded / maximum * plot.height
                    context.beginPath()
                    context.arc(x, y, 3.2, 0, Math.PI * 2)
                    context.fillStyle = root.hsla(root.themeColors.panel)
                    context.fill()
                    context.lineWidth = 2
                    context.strokeStyle = definition.color
                    context.stroke()
                }

                function drawSharedScale(context, plot) {
                    const maximum = root.sharedMaximum
                    drawHorizontalScale(
                        context,
                        plot,
                        root.yTickCount - 1,
                        0
                    )
                    for (let seriesIndex = 0;
                            seriesIndex < root.series.length; ++seriesIndex) {
                        drawSeries(
                            context,
                            root.series[seriesIndex],
                            plot,
                            maximum
                        )
                    }
                    for (let markerIndex = 0;
                            markerIndex < root.series.length; ++markerIndex) {
                        drawHoverMarker(
                            context,
                            root.series[markerIndex],
                            plot,
                            maximum
                        )
                    }
                }

                function drawStackedSeries(context, plot) {
                    const laneHeight = plot.height / root.series.length
                    for (let index = 0; index < root.series.length; ++index) {
                        const definition = root.series[index]
                        const maximum = root.maximumForSeries(definition)
                        const lane = {
                            left: plot.left,
                            right: plot.right,
                            width: plot.width,
                            top: plot.top + laneHeight * index,
                            bottom: plot.top + laneHeight * (index + 1),
                            height: laneHeight
                        }
                        drawHorizontalScale(
                            context,
                            lane,
                            2,
                            index === 0 ? 0 : 1
                        )
                        drawSeries(context, definition, lane, maximum)
                        drawHoverMarker(context, definition, lane, maximum)
                    }
                }

                onPaint: {
                    const context = getContext("2d")
                    context.clearRect(0, 0, width, height)
                    context.globalAlpha = 1

                    const plot = {
                        left: root.plotLeft,
                        right: width - 8,
                        top: root.plotTop,
                        bottom: height - root.plotBottomMargin,
                        width: width - root.plotLeft - 8,
                        height: height - root.plotVerticalInset
                    }
                    if (plot.width <= 0 || plot.height <= 0)
                        return

                    const ages = [
                        root.windowSeconds,
                        root.windowSeconds * 2 / 3,
                        root.windowSeconds / 3,
                        0
                    ]
                    for (let index = 0; index < ages.length; ++index) {
                        const age = ages[index]
                        const x = plot.left
                                  + (1 - age / root.windowSeconds) * plot.width
                        context.beginPath()
                        context.moveTo(x, plot.top)
                        context.lineTo(x, plot.bottom)
                        context.lineWidth = 1
                        context.strokeStyle = root.hsla(
                            root.themeColors.chart_grid
                        )
                        context.stroke()
                    }

                    if (root.hoveredPoint !== null) {
                        const hoverLineX = plot.left
                                           + (1 - root.hoveredPoint.age
                                              / root.windowSeconds)
                                           * plot.width
                        context.save()
                        context.globalAlpha = 0.72
                        context.beginPath()
                        context.moveTo(hoverLineX, plot.top)
                        context.lineTo(hoverLineX, plot.bottom)
                        context.lineWidth = 1
                        context.strokeStyle = root.hsla(
                            root.themeColors.chart_axis
                        )
                        context.stroke()
                        context.restore()
                    }

                    if (root.stackedSeries && root.series.length > 1)
                        drawStackedSeries(context, plot)
                    else
                        drawSharedScale(context, plot)
                }

                onWidthChanged: requestPaint()
                onHeightChanged: requestPaint()
            }

            Repeater {
                model: root.stackedSeries && root.series.length > 1
                       ? 0 : root.yTickCount
                delegate: Text {
                    required property int index
                    readonly property real ratio:
                        index / (root.yTickCount - 1)
                    x: 0
                    y: root.plotTop
                       + ratio * (chartArea.height - root.plotVerticalInset)
                       - height / 2
                    width: root.plotLeft - 7
                    horizontalAlignment: Text.AlignRight
                    text: root.formatAxisValue(
                        root.sharedMaximum * (1 - ratio),
                        root.valueFormat
                    )
                    color: root.hsla(root.themeColors.chart_axis)
                    font.family: root.typography.family
                    font.pixelSize: root.typography.detail_size
                    font.features: root.tabularNumeralFeatures
                }
            }

            Repeater {
                model: root.stackedSeries && root.series.length > 1
                       ? root.series : []
                delegate: Item {
                    id: stackedAxisLane
                    required property int index
                    required property var modelData
                    readonly property real laneHeight:
                        (chartArea.height - root.plotVerticalInset)
                        / root.series.length
                    readonly property real maximum:
                        root.maximumForSeries(modelData)

                    x: 0
                    y: root.plotTop + laneHeight * index
                    width: root.plotLeft - 7
                    height: laneHeight

                    Repeater {
                        model: 3
                        delegate: Text {
                            required property int index
                            readonly property real ratio: index / 2
                            x: 0
                            y: Math.max(
                                0,
                                Math.min(
                                    stackedAxisLane.height - height,
                                    ratio * stackedAxisLane.height - height / 2
                                )
                            )
                            width: stackedAxisLane.width
                            horizontalAlignment: Text.AlignRight
                            text: root.formatAxisValue(
                                stackedAxisLane.maximum * (1 - ratio),
                                stackedAxisLane.modelData.format
                                    || root.valueFormat
                            )
                            color: stackedAxisLane.modelData.color
                            font.family: root.typography.family
                            font.pixelSize: root.typography.detail_size
                            font.features: root.tabularNumeralFeatures
                        }
                    }
                }
            }

            Repeater {
                model: [
                    root.windowSeconds,
                    root.windowSeconds * 2 / 3,
                    root.windowSeconds / 3,
                    0
                ]
                delegate: Text {
                    required property real modelData
                    readonly property real centerX: root.plotLeft
                        + (1 - modelData / root.windowSeconds)
                          * (chartArea.width - root.plotLeft - 8)
                    x: Math.max(
                        root.plotLeft,
                        Math.min(
                            chartArea.width - 8 - width,
                            centerX - width / 2
                        )
                    )
                    y: chartArea.height - height
                    text: root.formatAge(modelData)
                    color: root.hsla(root.themeColors.chart_axis)
                    font.family: root.typography.family
                    font.pixelSize: root.typography.detail_size
                    font.features: root.tabularNumeralFeatures
                }
            }

            MouseArea {
                objectName: "chartHoverArea"
                anchors.fill: parent
                acceptedButtons: Qt.NoButton
                hoverEnabled: true
                onPositionChanged: mouse => root.updateHover(mouse.x)
                onExited: root.clearHover()
            }

            Rectangle {
                id: hoverCard
                visible: root.hoveredPoint !== null
                z: 2
                x: Math.max(
                    4,
                    Math.min(
                        chartArea.width - width - 4,
                        root.hoverX + 12 + width > chartArea.width
                            ? root.hoverX - width - 12
                            : root.hoverX + 12
                    )
                )
                y: 7
                width: 148
                height: 28 + root.series.length * 20
                radius: 8
                color: root.hsla(root.themeColors.surface_raised)
                border.width: 1
                border.color: root.hsla(root.themeColors.panel_border)

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 8
                    spacing: 4

                    Text {
                        text: root.hoveredPoint === null
                              ? "" : root.formatAge(root.hoveredPoint.age)
                        color: root.hsla(root.themeColors.muted_text)
                        font.family: root.typography.family
                        font.pixelSize: root.typography.detail_size
                        font.weight: Font.DemiBold
                        font.features: root.tabularNumeralFeatures
                    }
                    Repeater {
                        model: root.series
                        delegate: RowLayout {
                            id: hoverRow
                            required property var modelData
                            Layout.fillWidth: true
                            spacing: 5

                            Rectangle {
                                Layout.preferredWidth: 3
                                Layout.preferredHeight: 14
                                radius: 2
                                color: hoverRow.modelData.color
                            }
                            Text {
                                text: hoverRow.modelData.label
                                color: root.hsla(root.themeColors.secondary_text)
                                font.family: root.typography.family
                                font.pixelSize: root.typography.detail_size
                            }
                            Item { Layout.fillWidth: true }
                            Text {
                                text: root.hoveredPoint === null
                                      ? "N/A"
                                      : root.formatValue(
                                            root.hoveredPoint[
                                                hoverRow.modelData.key
                                            ],
                                            hoverRow.modelData.format
                                                || root.valueFormat
                                        )
                                color: root.hsla(root.themeColors.heading)
                                font.family: root.typography.family
                                font.pixelSize: root.typography.detail_size
                                font.weight: Font.DemiBold
                                font.features: root.tabularNumeralFeatures
                            }
                        }
                    }
                }
            }
        }

    }

    Component.onCompleted: refreshMaximums()
    onPointsChanged: refreshMaximums()
    onThemeColorsChanged: chartCanvas.requestPaint()
    onSeriesChanged: refreshMaximums()
    onFixedMaximumChanged: refreshMaximums()
    onMinimumMaximumChanged: refreshMaximums()
    onValueFormatChanged: refreshMaximums()
    onScaleDownDelaySecondsChanged: refreshMaximums()
    onStackedSeriesChanged: chartCanvas.requestPaint()
    onCompactChanged: chartCanvas.requestPaint()
}
