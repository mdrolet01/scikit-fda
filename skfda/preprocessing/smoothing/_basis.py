# -*- coding: utf-8 -*-
"""Basis smoother.

This module contains the class for the basis smoothing.

"""
from enum import Enum
from typing import Union, Iterable

import scipy.linalg

import numpy as np

from ... import FDataBasis
from ... import FDataGrid
from ..._utils import _cartesian_product
from ._linear import _LinearSmoother


class _Cholesky():
    """Solve the linear equation using cholesky factorization"""

    def __call__(self, *, basis_values, weight_matrix, data_matrix,
                 penalty_matrix, **_):

        common_matrix = basis_values.T

        if weight_matrix is not None:
            common_matrix @= weight_matrix

        right_matrix = common_matrix @ data_matrix
        left_matrix = common_matrix @ basis_values

        # Adds the roughness penalty to the equation
        if penalty_matrix is not None:
            left_matrix += penalty_matrix

        coefficients = scipy.linalg.cho_solve(scipy.linalg.cho_factor(
            left_matrix, lower=True), right_matrix)

        # The ith column is the coefficients of the ith basis for each
        #  sample
        coefficients = coefficients.T

        return coefficients


class _QR():
    """Solve the linear equation using qr factorization"""

    def __call__(self, *, basis_values, weight_matrix, data_matrix,
                 penalty_matrix, **_):

        if weight_matrix is not None:
            # Decompose W in U'U and calculate UW and Uy
            upper = scipy.linalg.cholesky(weight_matrix)
            basis_values = upper @ basis_values
            data_matrix = upper @ data_matrix

        if not np.all(penalty_matrix == 0):
            w, v = np.linalg.eigh(penalty_matrix)

            w = w[::-1]
            v = v[:, ::-1]

            w = np.maximum(w, 0)

            penalty_matrix = v @ np.diag(np.sqrt(w))
            # Augment the basis matrix with the square root of the
            # penalty matrix
            basis_values = np.concatenate([
                basis_values,
                penalty_matrix.T],
                axis=0)
            # Augment data matrix by n zeros
            data_matrix = np.pad(data_matrix,
                                 ((0, len(v)),
                                  (0, 0)),
                                 mode='constant')

        # Resolves the equation
        # B.T @ B @ C = B.T @ D
        # by means of the QR decomposition

        # B = Q @ R
        q, r = np.linalg.qr(basis_values)
        right_matrix = q.T @ data_matrix

        # R @ C = Q.T @ D
        coefficients = np.linalg.solve(r, right_matrix)
        # The ith column is the coefficients of the ith basis for each
        # sample
        coefficients = coefficients.T

        return coefficients


class _Matrix():
    """Solve the linear equation using matrix inversion"""

    def fit(self, estimator, X, y=None):
        if estimator.return_basis:
            estimator._cached_coef_matrix = estimator._coef_matrix(
                estimator.input_points_)
        else:
            # Force caching the hat matrix
            estimator.hat_matrix()

    def fit_transform(self, estimator, X, y=None):
        return estimator.fit(X, y).transform(X, y)

    def __call__(self, *, estimator, **_):
        pass

    def transform(self, estimator, X, y=None):
        if estimator.return_basis:
            coefficients = (X.data_matrix.reshape((X.n_samples, -1))
                            @ estimator._cached_coef_matrix.T)

            fdatabasis = FDataBasis(
                basis=estimator.basis, coefficients=coefficients)

            return fdatabasis
        else:
            # The matrix is cached
            return X.copy(data_matrix=self.hat_matrix() @ X.data_matrix,
                          sample_points=estimator.output_points_)


class BasisSmoother(_LinearSmoother):
    r"""Transform raw data to a smooth functional form.

    Takes functional data in a discrete form and makes an approximates it
    to the closest function that can be generated by the basis.a.

    The fit is made so as to reduce the penalized sum of squared errors
    [RS05-5-2-6]_:

    .. math::

        PENSSE(c) = (y - \Phi c)' W (y - \Phi c) + \lambda c'Rc

    where :math:`y` is the vector or matrix of observations, :math:`\Phi`
    the matrix whose columns are the basis functions evaluated at the
    sampling points, :math:`c` the coefficient vector or matrix to be
    estimated, :math:`\lambda` a smoothness parameter and :math:`c'Rc` the
    matrix representation of the roughness penalty :math:`\int \left[ L(
    x(s)) \right] ^2 ds` where :math:`L` is a linear differential operator.

    Each element of :math:`R` has the following close form:

    .. math::

        R_{ij} = \int L\phi_i(s) L\phi_j(s) ds

    By deriving the first formula we obtain the closed formed of the
    estimated coefficients matrix:

    .. math::

        \hat{c} = \left( \Phi' W \Phi + \lambda R \right)^{-1} \Phi' W y

    The solution of this matrix equation is done using the cholesky
    method for the resolution of a LS problem. If this method throughs a
    rounding error warning you may want to use the QR factorisation that
    is more numerically stable despite being more expensive to compute.
    [RS05-5-2-8]_

    Args:
        basis: (Basis): Basis used.
        weights (array_like, optional): Matrix to weight the
            observations. Defaults to the identity matrix.
        smoothing_parameter (int or float, optional): Smoothing
            parameter. Trying with several factors in a logarithm scale is
            suggested. If 0 no smoothing is performed. Defaults to 1.
        regularization (int, iterable or :class:`Regularization`):
            Regularization object. This allows the penalization of
            complicated models, which applies additional smoothing. By default
            is ``None`` meaning that no additional smoothing has to take
            place.
        method (str): Algorithm used for calculating the coefficients using
            the least squares method. The values admitted are 'cholesky', 'qr'
            and 'matrix' for Cholesky and QR factorisation methods, and matrix
            inversion respectively. The default is 'cholesky'.
        output_points (ndarray, optional): The output points. If ommited,
            the input points are used. If ``return_basis`` is ``True``, this
            parameter is ignored.
        return_basis (boolean): If ``False`` (the default) returns the smoothed
            data as an FDataGrid, like the other smoothers. If ``True`` returns
            a FDataBasis object.

    Examples:

        By default, this smoother returns a FDataGrid, like the other
        smoothers:

        >>> import numpy as np
        >>> import skfda
        >>> t = np.linspace(0, 1, 5)
        >>> x = np.sin(2 * np.pi * t) + np.cos(2 * np.pi * t) + 2
        >>> x
        array([ 3.,  3.,  1.,  1.,  3.])

        >>> fd = skfda.FDataGrid(data_matrix=x, sample_points=t)
        >>> basis = skfda.representation.basis.Fourier((0, 1), n_basis=3)
        >>> smoother = skfda.preprocessing.smoothing.BasisSmoother(
        ...                basis, method='cholesky')
        >>> fd_smooth = smoother.fit_transform(fd)
        >>> fd_smooth.data_matrix.round(2)
        array([[[ 3.],
                [ 3.],
                [ 1.],
                [ 1.],
                [ 3.]]])

        However, the parameter ``return_basis`` can be used to return the data
        in basis form, by default, without extra smoothing:

        >>> fd = skfda.FDataGrid(data_matrix=x, sample_points=t)
        >>> basis = skfda.representation.basis.Fourier((0, 1), n_basis=3)
        >>> smoother = skfda.preprocessing.smoothing.BasisSmoother(
        ...                basis, method='cholesky', return_basis=True)
        >>> fd_basis = smoother.fit_transform(fd)
        >>> fd_basis.coefficients.round(2)
        array([[ 2.  , 0.71, 0.71]])

        >>> smoother = skfda.preprocessing.smoothing.BasisSmoother(
        ...                basis, method='qr', return_basis=True)
        >>> fd_basis = smoother.fit_transform(fd)
        >>> fd_basis.coefficients.round(2)
        array([[ 2.  , 0.71, 0.71]])

        >>> smoother = skfda.preprocessing.smoothing.BasisSmoother(
        ...                basis, method='matrix', return_basis=True)
        >>> fd_basis = smoother.fit_transform(fd)
        >>> fd_basis.coefficients.round(2)
        array([[ 2.  , 0.71, 0.71]])
        >>> smoother.hat_matrix().round(2)
        array([[ 0.43,  0.14, -0.14,  0.14,  0.43],
               [ 0.14,  0.71,  0.29, -0.29,  0.14],
               [-0.14,  0.29,  0.71,  0.29, -0.14],
               [ 0.14, -0.29,  0.29,  0.71,  0.14],
               [ 0.43,  0.14, -0.14,  0.14,  0.43]])

        We can penalize approximations that are not smooth enough using some
        kind of regularization:

        >>> from skfda.misc.regularization import TikhonovRegularization
        >>> from skfda.misc.operators import LinearDifferentialOperator
        >>>
        >>> fd = skfda.FDataGrid(data_matrix=x, sample_points=t)
        >>> basis = skfda.representation.basis.Fourier((0, 1), n_basis=3)
        >>> smoother = skfda.preprocessing.smoothing.BasisSmoother(
        ...                basis, method='cholesky',
        ...                regularization=TikhonovRegularization(
        ...                    LinearDifferentialOperator([0.1, 0.2])),
        ...                return_basis=True)
        >>> fd_basis = smoother.fit_transform(fd)
        >>> fd_basis.coefficients.round(2)
        array([[ 2.04,  0.51,  0.55]])

        >>> fd = skfda.FDataGrid(data_matrix=x, sample_points=t)
        >>> basis = skfda.representation.basis.Fourier((0, 1), n_basis=3)
        >>> smoother = skfda.preprocessing.smoothing.BasisSmoother(
        ...                basis, method='qr',
        ...                regularization=TikhonovRegularization(
        ...                    LinearDifferentialOperator([0.1, 0.2])),
        ...                return_basis=True)
        >>> fd_basis = smoother.fit_transform(fd)
        >>> fd_basis.coefficients.round(2)
        array([[ 2.04,  0.51,  0.55]])

        >>> fd = skfda.FDataGrid(data_matrix=x, sample_points=t)
        >>> basis = skfda.representation.basis.Fourier((0, 1), n_basis=3)
        >>> smoother = skfda.preprocessing.smoothing.BasisSmoother(
        ...                basis, method='matrix',
        ...                regularization=TikhonovRegularization(
        ...                    LinearDifferentialOperator([0.1, 0.2])),
        ...                return_basis=True)
        >>> fd_basis = smoother.fit_transform(fd)
        >>> fd_basis.coefficients.round(2)
        array([[ 2.04,  0.51,  0.55]])

    References:
        .. [RS05-5-2-6] Ramsay, J., Silverman, B. W. (2005). How spline
            smooths are computed. In *Functional Data Analysis*
            (pp. 86-87). Springer.

        .. [RS05-5-2-8] Ramsay, J., Silverman, B. W. (2005). HSpline
            smoothing as an augmented least squares problem. In *Functional
            Data Analysis* (pp. 86-87). Springer.

    """

    _required_parameters = ["basis"]

    class SolverMethod(Enum):
        cholesky = _Cholesky()
        qr = _QR()
        matrix = _Matrix()

    def __init__(self,
                 basis,
                 *,
                 smoothing_parameter: float = 1.,
                 weights=None,
                 regularization: Union[int, Iterable[float],
                                       'LinearDifferentialOperator'] = None,
                 output_points=None,
                 method='cholesky',
                 return_basis=False):
        self.basis = basis
        self.smoothing_parameter = smoothing_parameter
        self.weights = weights
        self.regularization = regularization
        self.output_points = output_points
        self.method = method
        self.return_basis = return_basis

    def _method_function(self):
        """ Return the method function"""
        method_function = self.method
        if not isinstance(method_function, self.SolverMethod):
            method_function = self.SolverMethod[
                method_function.lower()]

        return method_function.value

    def _coef_matrix(self, input_points):
        """Get the matrix that gives the coefficients"""
        from ...misc.regularization import compute_penalty_matrix

        basis_values_input = self.basis.evaluate(
            _cartesian_product(input_points)).reshape(
            (self.basis.n_basis, -1)).T

        # If no weight matrix is given all the weights are one
        if self.weights is not None:
            ols_matrix = (basis_values_input.T @ self.weights
                          @ basis_values_input)
        else:
            ols_matrix = basis_values_input.T @ basis_values_input

        penalty_matrix = compute_penalty_matrix(
            basis_iterable=(self.basis,),
            regularization_parameter=self.smoothing_parameter,
            regularization=self.regularization)

        ols_matrix += penalty_matrix

        right_side = basis_values_input.T
        if self.weights is not None:
            right_side @= self.weights

        return np.linalg.solve(
            ols_matrix, right_side)

    def _hat_matrix(self, input_points, output_points):
        basis_values_output = self.basis.evaluate(_cartesian_product(
            output_points)).reshape(
            (self.basis.n_basis, -1)).T

        return basis_values_output @ self._coef_matrix(input_points)

    def fit(self, X: FDataGrid, y=None):
        """Compute the hat matrix for the desired output points.

        Args:
            X (FDataGrid):
                The data whose points are used to compute the matrix.
            y : Ignored
        Returns:
            self (object)

        """

        self.input_points_ = X.sample_points
        self.output_points_ = (self.output_points
                               if self.output_points is not None
                               else self.input_points_)

        method = self._method_function()
        method_fit = getattr(method, "fit", None)
        if method_fit is not None:
            method_fit(estimator=self, X=X, y=y)

        return self

    def fit_transform(self, X: FDataGrid, y=None):
        """Compute the hat matrix for the desired output points.

        Args:
            X (FDataGrid):
                The data whose points are used to compute the matrix.
            y : Ignored
        Returns:
            self (object)

        """
        from ...misc.regularization import compute_penalty_matrix

        self.input_points_ = X.sample_points
        self.output_points_ = (self.output_points
                               if self.output_points is not None
                               else self.input_points_)

        penalty_matrix = compute_penalty_matrix(
            basis_iterable=(self.basis,),
            regularization_parameter=self.smoothing_parameter,
            regularization=self.regularization)

        # n is the samples
        # m is the observations
        # k is the number of elements of the basis

        # Each sample in a column (m x n)
        data_matrix = X.data_matrix.reshape((X.n_samples, -1)).T

        # Each basis in a column
        basis_values = self.basis.evaluate(
            _cartesian_product(self.input_points_)).reshape(
            (self.basis.n_basis, -1)).T

        # If no weight matrix is given all the weights are one
        weight_matrix = self.weights

        # We need to solve the equation
        # (phi' W phi + lambda * R) C = phi' W Y
        # where:
        #  phi is the basis_values
        #  W is the weight matrix
        #  lambda the smoothness parameter
        #  C the coefficient matrix (the unknown)
        #  Y is the data_matrix

        if(data_matrix.shape[0] > self.basis.n_basis
           or self.smoothing_parameter > 0):

            method = self._method_function()

            # If the method provides the complete transformation use it
            method_fit_transform = getattr(method, "fit_transform", None)
            if method_fit_transform is not None:
                return method_fit_transform(estimator=self, X=X, y=y)

            # Otherwise the method is used to compute the coefficients
            coefficients = method(estimator=self,
                                  basis_values=basis_values,
                                  weight_matrix=weight_matrix,
                                  data_matrix=data_matrix,
                                  penalty_matrix=penalty_matrix)

        elif data_matrix.shape[0] == self.basis.n_basis:
            # If the number of basis equals the number of points and no
            # smoothing is required
            coefficients = np.linalg.solve(basis_values, data_matrix).T

        else:  # data_matrix.shape[0] < basis.n_basis
            raise ValueError(f"The number of basis functions "
                             f"({self.basis.n_basis}) "
                             f"exceed the number of points to be smoothed "
                             f"({data_matrix.shape[0]}).")

        fdatabasis = FDataBasis(
            basis=self.basis, coefficients=coefficients)

        if self.return_basis:
            return fdatabasis
        else:
            return fdatabasis.to_grid(sample_points=self.output_points_)

        return self

    def transform(self, X: FDataGrid, y=None):
        """Apply the smoothing.

        Args:
            X (FDataGrid):
                The data to smooth.
            y : Ignored
        Returns:
            self (object)

        """

        assert all([all(i == s)
                    for i, s in zip(self.input_points_, X.sample_points)])

        method = self._method_function()

        # If the method provides the complete transformation use it
        method_transform = getattr(method, "transform", None)
        if method_transform is not None:
            return method_transform(estimator=self, X=X, y=y)

        # Otherwise use fit_transform over the data
        # Note that data leakage is not possible because the matrix only
        # depends on the input/output points
        return self.fit_transform(X, y)
