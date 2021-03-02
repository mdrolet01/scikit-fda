from typing import Any, Optional, Sequence, Union

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.artist import Artist
from matplotlib.axes import Axes
from matplotlib.backend_bases import Event
from matplotlib.figure import Figure

from ._display import Display
from ._utils import _get_figure_and_axes, _set_figure_layout


class MultipleDisplay:
    def __init__(
        self,
        displays: Union[Display, Sequence[Display]],
    ):
        if isinstance(displays, Display):
            self.displays = [displays]
        else:
            self.displays = displays
        self.point_clicked: Artist = None
        self.num_graphs = len(self.displays)
        self.length_data = self.displays[0].num_instances()

    def plot(
        self,
        chart: Union[Figure, Axes, None] = None,
        *,
        fig: Optional[Figure] = None,
        axes: Optional[Sequence[Axes]] = None,
        **kwargs: Any,
    ):
        fig, axes = self.init_axes(chart=chart, fig=fig, axes=axes)
        self.fig = fig
        self.axes = axes

        if self.num_graphs > 1:
            for display in self.displays[1:]:
                if display.num_instances() != self.length_data:
                    raise ValueError(
                        "Length of some data sets are not equal ",
                    )

        for display, ax in zip(self.displays, self.axes):
            display.plot(axes=ax)

        self.fig.canvas.mpl_connect('pick_event', self.pick)

        return self.fig

    def add_displays(
        self,
        displays: Union[Display, Sequence[Display]],
    ) -> None:
        if isinstance(displays, Display):
            self.displays.append(displays)
        else:
            self.displays.extend(displays)

    def init_axes(
        self,
        chart: Union[Figure, Axes, None] = None,
        fig: Optional[Figure] = None,
        axes: Union[Axes, Sequence[Axes], None] = None,
    ) -> Figure:
        if fig is None:
            fig = plt.figure(figsize=(9, 3))

        fig, axes = _get_figure_and_axes(chart, fig, axes)

        fig, axes = _set_figure_layout(
            fig=fig, axes=axes, n_axes=len(self.displays),
        )

        return fig, axes

    def pick(self, event: Event) -> None:
        if self.point_clicked is None:
            self.point_clicked = event.artist
            self.picked_disp = self.get_display_picked()
            self.reduce_points_intensity()
        elif self.point_clicked == event.artist:
            self.restore_points_intensity()
            self.point_clicked = None
        else:
            self.change_points_intensity(event.artist)
            self.point_clicked = event.artist

    def get_display_picked(self) -> int:
        for i in range(self.num_graphs):
            if self.axes[i] == self.point_clicked.axes:
                return self.displays[i]

    def reduce_points_intensity(self) -> None:
        for i in range(self.length_data):
            if not (
                np.ma.getdata(
                    self.picked_disp.id_function[i].get_offsets(),
                )[0][0]
                == np.ma.getdata(self.point_clicked.get_offsets())[0][0]
                and np.ma.getdata(
                    self.picked_disp.id_function[i].get_offsets(),
                )[0][1]
                == np.ma.getdata(self.point_clicked.get_offsets())[0][1]
            ):
                for display in self.displays:
                    if isinstance(display.id_function[i], list):
                        display.id_function[i][0].set_alpha(0.1)
                    else:
                        display.id_function[i].set_alpha(0.1)

    def restore_points_intensity(self) -> None:
        for i in range(self.length_data):
            for display in self.displays:
                if isinstance(display.id_function[i], list):
                    display.id_function[i][0].set_alpha(1)
                else:
                    display.id_function[i].set_alpha(1)

    def change_points_intensity(self, new_point: Artist) -> None:
        for i in range(self.length_data):
            if (
                np.ma.getdata(
                    self.picked_disp.id_function[i].get_offsets(),
                )[0][0]
                == np.ma.getdata(new_point.get_offsets())[0][0]
            ) and (
                np.ma.getdata(
                    self.picked_disp.id_function[i].get_offsets(),
                )[0][1]
                == np.ma.getdata(new_point.get_offsets())[0][1]
            ):
                intensity = 1
            else:
                intensity = 0.1

            for display in self.displays:
                if isinstance(display.id_function[i], list):
                    display.id_function[i][0].set_alpha(intensity)
                else:
                    display.id_function[i].set_alpha(intensity)