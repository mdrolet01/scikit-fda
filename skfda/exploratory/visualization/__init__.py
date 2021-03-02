"""Initialization module of visualization folder."""

from . import clustering, representation
from ._boxplot import Boxplot, SurfaceBoxplot
from ._ddplot import DDPlot
from ._display import Display
from ._magnitude_shape_plot import MagnitudeShapePlot
from ._multiple_display import MultipleDisplay
from ._outliergram import Outliergram
from .fpca import plot_fpca_perturbation_graphs
