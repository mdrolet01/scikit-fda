import numpy as np

from ..._utils import _list_of_arrays
from ..._utils import _same_domain
from ._basis import Basis


class Fourier(Basis):
    r"""Fourier basis.

    Defines a functional basis for representing functions on a fourier
    series expansion of period :math:`T`. The number of basis is always odd.
    If instantiated with an even number of basis, they will be incremented
    automatically by one.

    .. math::
        \phi_0(t) = \frac{1}{\sqrt{2}}

    .. math::
        \phi_{2n -1}(t) = sin\left(\frac{2 \pi n}{T} t\right)

    .. math::
        \phi_{2n}(t) = cos\left(\frac{2 \pi n}{T} t\right)

    Actually this basis functions are not orthogonal but not orthonormal. To
    achieve this they are divided by its norm: :math:`\sqrt{\frac{T}{2}}`.

    Attributes:
        domain_range (tuple): A tuple of length 2 containing the initial and
            end values of the interval over which the basis can be evaluated.
        n_basis (int): Number of functions in the basis.
        period (int or float): Period (:math:`T`).

    Examples:
        Constructs specifying number of basis, definition interval and period.

        >>> fb = Fourier((0, np.pi), n_basis=3, period=1)
        >>> fb([0, np.pi / 4, np.pi / 2, np.pi]).round(2)
        array([[[ 1.  ],
                [ 1.  ],
                [ 1.  ],
                [ 1.  ]],
               [[ 0.  ],
                [-1.38],
                [-0.61],
                [ 1.1 ]],
               [[ 1.41],
                [ 0.31],
                [-1.28],
                [ 0.89]]])

        And evaluate second derivative

        >>> deriv2 = fb.derivative(order=2)
        >>> deriv2([0, np.pi / 4, np.pi / 2, np.pi]).round(2)
        array([[[  0.  ],
                [  0.  ],
                [  0.  ],
                [  0.  ]],
               [[  0.  ],
                [ 54.46],
                [ 24.02],
                [-43.37]],
               [[-55.83],
                [-12.32],
                [ 50.4 ],
                [-35.16]]])

    """

    def __init__(self, domain_range=None, n_basis=3, period=None):
        """Construct a Fourier object.

        It forces the object to have an odd number of basis. If n_basis is
        even, it is incremented by one.

        Args:
            domain_range (tuple): Tuple defining the domain over which the
            function is defined.
            n_basis (int): Number of basis functions.
            period (int or float): Period of the trigonometric functions that
                define the basis.

        """

        if domain_range is not None:
            domain_range = _list_of_arrays(domain_range)

            if len(domain_range) != 1:
                raise ValueError("Domain range should be unidimensional.")

            domain_range = domain_range[0]

        self.period = period
        # If number of basis is even, add 1
        n_basis += 1 - n_basis % 2
        super().__init__(domain_range, n_basis)

    @property
    def period(self):
        if self._period is None:
            return self.domain_range[0][1] - self.domain_range[0][0]
        else:
            return self._period

    @period.setter
    def period(self, value):
        self._period = value

    def _evaluate(self, eval_points):

        # Input is scalar
        eval_points = eval_points[..., 0]

        functions = [np.sin, np.cos]
        omega = 2 * np.pi / self.period

        normalization_denominator = np.sqrt(self.period / 2)

        seq = 1 + np.arange((self.n_basis - 1) // 2)
        seq_pairs = np.array([seq, seq]).T
        phase_coefs = omega * seq_pairs

        # Multiply the phase coefficients elementwise
        res = np.einsum('ij,k->ijk', phase_coefs, eval_points)

        # Apply odd and even functions
        for i in [0, 1]:
            functions[i](res[:, i, :], out=res[:, i, :])

        res = res.reshape(-1, len(eval_points))
        res /= normalization_denominator

        constant_basis = np.full(
            shape=(1, len(eval_points)),
            fill_value=1 / (np.sqrt(2) * normalization_denominator))

        res = np.concatenate((constant_basis, res))

        return res

    def _derivative_basis_and_coefs(self, coefs, order=1):

        omega = 2 * np.pi / self.period
        deriv_factor = (np.arange(1, (self.n_basis + 1) / 2) * omega) ** order

        deriv_coefs = np.zeros(coefs.shape)

        cos_sign, sin_sign = ((-1) ** int((order + 1) / 2),
                              (-1) ** int(order / 2))

        if order % 2 == 0:
            deriv_coefs[:, 1::2] = sin_sign * coefs[:, 1::2] * deriv_factor
            deriv_coefs[:, 2::2] = cos_sign * coefs[:, 2::2] * deriv_factor
        else:
            deriv_coefs[:, 2::2] = sin_sign * coefs[:, 1::2] * deriv_factor
            deriv_coefs[:, 1::2] = cos_sign * coefs[:, 2::2] * deriv_factor

        # normalise
        return self.copy(), deriv_coefs

    def _gram_matrix(self):

        # Orthogonal in this case
        if self.period == (self.domain_range[0][1] - self.domain_range[0][0]):
            return np.identity(self.n_basis)
        else:
            return super()._gram_matrix()

    def basis_of_product(self, other):
        """Multiplication of two Fourier Basis"""
        if not _same_domain(self, other):
            raise ValueError("Ranges are not equal.")

        if isinstance(other, Fourier) and self.period == other.period:
            return Fourier(self.domain_range, self.n_basis + other.n_basis - 1,
                           self.period)
        else:
            return other.rbasis_of_product(self)

    def rbasis_of_product(self, other):
        """Multiplication of a Fourier Basis with other Basis"""
        return Basis.default_basis_of_product(other, self)

    def rescale(self, domain_range=None, *, rescale_period=False):
        r"""Return a copy of the basis with a new domain range, with the
            corresponding values rescaled to the new bounds.

            Args:
                domain_range (tuple, optional): Definition of the interval
                    where the basis defines a space. Defaults uses the same as
                    the original basis.
                rescale_period (bool, optional): If true the period will be
                    rescaled using the ratio between the lengths of the new
                    and old interval. Defaults to False.
        """

        rescale_basis = super().rescale(domain_range)

        if rescale_period is False:
            rescale_basis.period = self.period
        else:
            domain_rescaled = rescale_basis.domain_range[0]
            domain = self.domain_range[0]

            rescale_basis.period = (self.period *
                                    (domain_rescaled[1] - domain_rescaled[0]) /
                                    (domain[1] - domain[0]))

        return rescale_basis

    def _to_R(self):
        drange = self.domain_range[0]
        return ("create.fourier.basis(rangeval = c(" + str(drange[0]) + "," +
                str(drange[1]) + "), nbasis = " + str(self.n_basis) +
                ", period = " + str(self.period) + ")")

    def __repr__(self):
        """Representation of a Fourier basis."""
        return (f"{self.__class__.__name__}(domain_range={self.domain_range}, "
                f"n_basis={self.n_basis}, period={self.period})")

    def __eq__(self, other):
        """Equality of Basis"""
        return super().__eq__(other) and self.period == other.period
