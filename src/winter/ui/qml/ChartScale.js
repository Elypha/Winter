.pragma library

function niceMaximum(value, secondStep) {
    if (typeof value !== "number" || !isFinite(value) || value <= 0)
        return 1

    const second = typeof secondStep === "number" ? secondStep : 2
    const exponent = Math.floor(Math.log(value) / Math.LN10)
    const magnitude = Math.pow(10, exponent)
    const fraction = value / magnitude
    let nice = 10
    if (fraction <= 1)
        nice = 1
    else if (fraction <= second)
        nice = second
    else if (fraction <= 5)
        nice = 5
    return nice * magnitude
}

function niceBinaryMaximum(value, secondStep) {
    let unit = 1
    if (value >= 1073741824)
        unit = 1073741824
    else if (value >= 1048576)
        unit = 1048576
    else if (value >= 1024)
        unit = 1024
    return niceMaximum(value / unit, secondStep) * unit
}

function settle(previous, target, nowMilliseconds, downDelayMilliseconds) {
    let maximum = previous && typeof previous.maximum === "number"
                  && isFinite(previous.maximum)
                  ? previous.maximum : target
    let lowerSince = previous && typeof previous.lowerSince === "number"
                     ? previous.lowerSince : -1

    if (target > maximum)
        return { maximum: target, lowerSince: -1 }

    if (target < maximum) {
        if (downDelayMilliseconds <= 0)
            return { maximum: target, lowerSince: -1 }
        if (lowerSince < 0)
            return { maximum: maximum, lowerSince: nowMilliseconds }
        if (nowMilliseconds - lowerSince >= downDelayMilliseconds)
            return { maximum: target, lowerSince: -1 }
        return { maximum: maximum, lowerSince: lowerSince }
    }

    return { maximum: maximum, lowerSince: -1 }
}
