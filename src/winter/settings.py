from __future__ import annotations

import os
from pathlib import Path
import tempfile
from typing import Annotated, Literal, Self

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationError,
)
from pydantic import model_validator
import yaml


HueDegrees = Annotated[float, Field(ge=0, lt=360)]
Percentage = Annotated[float, Field(ge=0, le=100)]
Alpha = Annotated[float, Field(ge=0, le=1)]


def _tuple_from_yaml_sequence(value: object) -> object:
    return tuple(value) if isinstance(value, list) else value


HslaColor = Annotated[
    tuple[HueDegrees, Percentage, Percentage, Alpha],
    BeforeValidator(_tuple_from_yaml_sequence),
]
NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class _ConfigSection(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
    )


class _ConfigDumper(yaml.SafeDumper):
    pass


def _represent_hsla(
    dumper: yaml.SafeDumper,
    value: tuple[float, float, float, float],
) -> yaml.SequenceNode:
    return dumper.represent_sequence(
        "tag:yaml.org,2002:seq",
        value,
        flow_style=True,
    )


_ConfigDumper.add_representer(tuple, _represent_hsla)


class TelemetryConfig(_ConfigSection):
    retention_seconds: Annotated[float, Field(gt=0, le=3600)]
    network_sample_seconds: Annotated[float, Field(gt=0, le=60)]
    system_sample_seconds: Annotated[float, Field(gt=0, le=60)]
    sensor_sample_seconds: Annotated[float, Field(gt=0, le=60)]


class NetworkChartConfig(_ConfigSection):
    series_layout: Literal["shared", "separate"]
    history_seconds: Annotated[float, Field(gt=0, le=600)]
    smoothing_seconds: Annotated[float, Field(gt=0, le=60)]
    minimum_axis_bytes_per_second: Annotated[float, Field(gt=0)]
    scale_down_delay_seconds: Annotated[float, Field(ge=0, le=60)]
    line_width: Annotated[float, Field(gt=0, le=10)]
    line_opacity: Annotated[float, Field(ge=0, le=1)]
    padding_y: Annotated[float, Field(ge=0, le=20)]
    upload_color: HslaColor
    download_color: HslaColor

    @model_validator(mode="after")
    def keep_smoothing_inside_displayed_history(self) -> Self:
        if self.smoothing_seconds > self.history_seconds:
            raise ValueError("smoothing_seconds cannot exceed history_seconds")
        return self


class NetworkConfig(_ConfigSection):
    adapter_selection: Literal["automatic", "named"]
    adapter_name: NonEmptyText | None
    chart: NetworkChartConfig

    @model_validator(mode="after")
    def require_named_adapter(self) -> Self:
        if self.adapter_selection == "named" and self.adapter_name is None:
            raise ValueError(
                "adapter_name is required when adapter_selection is 'named'"
            )
        return self


class TaskbarTextConfig(_ConfigSection):
    metric_family: NonEmptyText
    metric_size: Annotated[int, Field(ge=8, le=24)]
    metric_weight: Annotated[float, Field(ge=300, le=700)]
    memory_family: NonEmptyText
    memory_size: Annotated[int, Field(ge=8, le=24)]
    memory_weight: Annotated[float, Field(ge=300, le=700)]


class TaskbarColorsConfig(_ConfigSection):
    foreground_on_dark: HslaColor
    foreground_on_light: HslaColor
    memory_bar_track_on_dark: HslaColor
    memory_bar_track_on_light: HslaColor
    memory_bar_fill_start: HslaColor
    memory_bar_fill_end: HslaColor


class TaskbarSizeConfig(_ConfigSection):
    row_height: Annotated[int, Field(ge=8, le=40)]
    network_width_full: Annotated[int, Field(ge=20, le=300)]
    network_width_compact: Annotated[int, Field(ge=20, le=300)]
    network_width_minimal: Annotated[int, Field(ge=20, le=300)]
    icons_width: Annotated[int, Field(ge=1, le=100)]
    icon_size: Annotated[int, Field(ge=1, le=100)]
    usage_width: Annotated[int, Field(ge=1, le=100)]
    power_width: Annotated[int, Field(ge=1, le=100)]
    memory_width_full: Annotated[int, Field(ge=20, le=300)]
    memory_width_compact: Annotated[int, Field(ge=20, le=300)]
    memory_width_minimal: Annotated[int, Field(ge=20, le=300)]
    network_unit_width: Annotated[int, Field(ge=1, le=40)]
    memory_bar_height_trim: Annotated[int, Field(ge=0, le=20)]
    memory_bar_radius: Annotated[int, Field(ge=0, le=20)]


class TaskbarPositionConfig(_ConfigSection):
    shift_left_or_up: Annotated[int, Field(ge=-10000, le=10000)]
    padding_x: Annotated[int, Field(ge=0, le=40)]
    row_gap: Annotated[int, Field(ge=0, le=20)]
    network_value_unit_gap: Annotated[int, Field(ge=0, le=40)]
    memory_value_padding_left: Annotated[int, Field(ge=0, le=40)]
    network_icons_gap: Annotated[int, Field(ge=0, le=40)]
    icons_usage_gap: Annotated[int, Field(ge=0, le=40)]
    usage_power_gap: Annotated[int, Field(ge=0, le=40)]
    power_memory_gap: Annotated[int, Field(ge=0, le=40)]
    icon_shift_down: Annotated[int, Field(ge=-20, le=20)]
    memory_bar_shift_down: Annotated[int, Field(ge=-20, le=20)]


class TaskbarConfig(_ConfigSection):
    monitor: NonEmptyText | None
    visible_in_fullscreen: bool
    colors: TaskbarColorsConfig
    text: TaskbarTextConfig
    size: TaskbarSizeConfig
    position: TaskbarPositionConfig

    def total_width(self, display_mode: str) -> int:
        size = self.size
        position = self.position
        network_width = {
            "full": size.network_width_full,
            "compact": size.network_width_compact,
            "minimal": size.network_width_minimal,
        }[display_mode]
        memory_width = {
            "full": size.memory_width_full,
            "compact": size.memory_width_compact,
            "minimal": size.memory_width_minimal,
        }[display_mode]
        return (
            network_width
            + size.icons_width
            + size.usage_width
            + size.power_width
            + memory_width
            + position.padding_x * 2
            + position.network_icons_gap
            + position.icons_usage_gap
            + position.usage_power_gap
            + position.power_memory_gap
        )


class ControlCenterColorConfig(_ConfigSection):
    window: HslaColor
    surface: HslaColor
    surface_raised: HslaColor
    surface_hovered: HslaColor
    heading: HslaColor
    text: HslaColor
    secondary_text: HslaColor
    muted_text: HslaColor
    input: HslaColor
    alternate_input: HslaColor
    button: HslaColor
    button_text: HslaColor
    accent: HslaColor
    accent_text: HslaColor
    placeholder: HslaColor
    panel: HslaColor
    panel_border: HslaColor
    divider: HslaColor
    chart_grid: HslaColor
    chart_axis: HslaColor
    chart_upload: HslaColor
    chart_download: HslaColor
    chart_cpu: HslaColor
    chart_gpu: HslaColor
    chart_temperature: HslaColor
    shadow: HslaColor


class ControlCenterTextConfig(_ConfigSection):
    family: NonEmptyText
    display_family: NonEmptyText
    detail_size: Annotated[int, Field(ge=8, le=24)]
    body_size: Annotated[int, Field(ge=8, le=24)]
    heading_size: Annotated[int, Field(ge=8, le=32)]
    title_size: Annotated[int, Field(ge=8, le=40)]


class ControlCenterConfig(_ConfigSection):
    theme: Literal["dark", "light"]
    history_seconds: Annotated[float, Field(gt=0, le=600)]
    text: ControlCenterTextConfig
    dark: ControlCenterColorConfig
    light: ControlCenterColorConfig


class Config(_ConfigSection):
    version: Literal[1]
    telemetry: TelemetryConfig
    network: NetworkConfig
    taskbar: TaskbarConfig
    control_center: ControlCenterConfig

    @model_validator(mode="after")
    def retain_all_displayed_history(self) -> Self:
        displayed = max(
            self.network.chart.history_seconds,
            self.control_center.history_seconds,
        )
        if self.telemetry.retention_seconds < displayed:
            raise ValueError(
                "telemetry.retention_seconds cannot be shorter than "
                "displayed chart history"
            )
        return self

    @classmethod
    def load(cls, path: Path) -> Self:
        try:
            document = yaml.safe_load(path.read_text(encoding="utf-8"))
            return cls.model_validate(document)
        except OSError as error:
            raise OSError(f"Could not read {path}: {error}") from error
        except (yaml.YAMLError, ValidationError) as error:
            raise OSError(f"Invalid configuration in {path}: {error}") from error

    def save(self, path: Path) -> None:
        payload = yaml.dump(
            self.model_dump(mode="python"),
            Dumper=_ConfigDumper,
            allow_unicode=True,
            sort_keys=False,
        )
        path.parent.mkdir(parents=True, exist_ok=True)

        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="\n",
                prefix=f".{path.name}.",
                suffix=".tmp",
                dir=path.parent,
                delete=False,
            ) as stream:
                temporary = Path(stream.name)
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
