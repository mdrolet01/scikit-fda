import unittest

from skfda.misc.regularization import L2Regularization
from skfda.misc.regularization import LinearDifferentialOperatorRegularization
from skfda.ml.regression import MultivariateLinearRegression
from skfda.representation.basis import (FDataBasis, Monomial,
                                        Fourier,  BSpline)

import numpy as np


class TestMultivariateLinearRegression(unittest.TestCase):

    def test_regression_single_explanatory(self):

        x_basis = Monomial(n_basis=7)
        x_fd = FDataBasis(x_basis, np.identity(7))

        beta_basis = Fourier(n_basis=5)
        beta_fd = FDataBasis(beta_basis, [1, 1, 1, 1, 1])
        y = [1.0000684777229512,
             0.1623672257830915,
             0.08521053851548224,
             0.08514200869281137,
             0.09529138749665378,
             0.10549625973303875,
             0.11384314859153018]

        scalar = MultivariateLinearRegression(coef_basis=[beta_basis])
        scalar.fit(x_fd, y)
        np.testing.assert_allclose(scalar.coef_[0].coefficients,
                                   beta_fd.coefficients)
        np.testing.assert_allclose(scalar.intercept_,
                                   0.0, atol=1e-6)

        y_pred = scalar.predict(x_fd)
        np.testing.assert_allclose(y_pred, y)

        scalar = MultivariateLinearRegression(coef_basis=[beta_basis],
                                              fit_intercept=False)
        scalar.fit(x_fd, y)
        np.testing.assert_allclose(scalar.coef_[0].coefficients,
                                   beta_fd.coefficients)
        np.testing.assert_equal(scalar.intercept_,
                                0.0)

        y_pred = scalar.predict(x_fd)
        np.testing.assert_allclose(y_pred, y)

    def test_regression_multiple_explanatory(self):
        y = [1, 2, 3, 4, 5, 6, 7]

        X = FDataBasis(Monomial(n_basis=7), np.identity(7))

        beta1 = BSpline(domain_range=(0, 1), n_basis=5)

        scalar = MultivariateLinearRegression(coef_basis=[beta1])

        scalar.fit(X, y)

        np.testing.assert_allclose(scalar.intercept_.round(4),
                                   np.array([32.6518]))

        np.testing.assert_allclose(
            scalar.coef_[0].coefficients.round(4),
            np.array([[-28.6443,
                       80.3996,
                       -188.587,
                       236.5832,
                       -481.3449]]))

        y_pred = scalar.predict(X)
        np.testing.assert_allclose(y_pred, y, atol=0.01)

    def test_regression_mixed(self):

        multivariate = np.array([[0, 0], [2, 7], [1, 7], [3, 9],
                                 [4, 16], [2, 14], [3, 5]])

        X = [multivariate,
             FDataBasis(Monomial(n_basis=3), [[1, 0, 0], [0, 1, 0], [0, 0, 1],
                                              [1, 0, 1], [1, 0, 0], [0, 1, 0],
                                              [0, 0, 1]])]

        # y = 2 + sum([3, 1] * array) + int(3 * function)
        intercept = 2
        coefs_multivariate = np.array([3, 1])
        coefs_functions = FDataBasis(
            Monomial(n_basis=3), [[3, 0, 0]])
        y_integral = np.array([3, 3 / 2, 1, 4, 3, 3 / 2, 1])
        y_sum = multivariate @ coefs_multivariate
        y = 2 + y_sum + y_integral

        scalar = MultivariateLinearRegression()
        scalar.fit(X, y)

        np.testing.assert_allclose(scalar.intercept_,
                                   intercept, atol=0.01)

        np.testing.assert_allclose(
            scalar.coef_[0],
            coefs_multivariate, atol=0.01)

        np.testing.assert_allclose(
            scalar.coef_[1].coefficients,
            coefs_functions.coefficients, atol=0.01)

        y_pred = scalar.predict(X)
        np.testing.assert_allclose(y_pred, y, atol=0.01)

    def test_regression_mixed_regularization(self):

        multivariate = np.array([[0, 0], [2, 7], [1, 7], [3, 9],
                                 [4, 16], [2, 14], [3, 5]])

        X = [multivariate,
             FDataBasis(Monomial(n_basis=3), [[1, 0, 0], [0, 1, 0], [0, 0, 1],
                                              [1, 0, 1], [1, 0, 0], [0, 1, 0],
                                              [0, 0, 1]])]

        # y = 2 + sum([3, 1] * array) + int(3 * function)
        intercept = 2
        coefs_multivariate = np.array([3, 1])
        y_integral = np.array([3, 3 / 2, 1, 4, 3, 3 / 2, 1])
        y_sum = multivariate @ coefs_multivariate
        y = 2 + y_sum + y_integral

        scalar = MultivariateLinearRegression(
            regularization_parameter=1,
            regularization=[L2Regularization(),
                            LinearDifferentialOperatorRegularization(2)])
        scalar.fit(X, y)

        np.testing.assert_allclose(scalar.intercept_,
                                   intercept, atol=0.01)

        np.testing.assert_allclose(
            scalar.coef_[0],
            [2.536739, 1.072186], atol=0.01)

        np.testing.assert_allclose(
            scalar.coef_[1].coefficients,
            [[2.125676, 2.450782, 5.808745e-4]], atol=0.01)

        y_pred = scalar.predict(X)
        np.testing.assert_allclose(
            y_pred,
            [5.349035, 16.456464, 13.361185, 23.930295,
                32.650965, 23.961766, 16.29029],
            atol=0.01)

    def test_regression_regularization(self):

        x_basis = Monomial(n_basis=7)
        x_fd = FDataBasis(x_basis, np.identity(7))

        beta_basis = Fourier(n_basis=5)
        beta_fd = FDataBasis(beta_basis, [1.0403, 0, 0, 0, 0])
        y = [1.0000684777229512,
             0.1623672257830915,
             0.08521053851548224,
             0.08514200869281137,
             0.09529138749665378,
             0.10549625973303875,
             0.11384314859153018]

        y_pred_compare = [0.890341,
                          0.370162,
                          0.196773,
                          0.110079,
                          0.058063,
                          0.023385,
                          -0.001384]

        scalar = MultivariateLinearRegression(
            coef_basis=[beta_basis],
            regularization_parameter=1,
            regularization=LinearDifferentialOperatorRegularization())
        scalar.fit(x_fd, y)
        np.testing.assert_allclose(scalar.coef_[0].coefficients,
                                   beta_fd.coefficients, atol=1e-3)
        np.testing.assert_allclose(scalar.intercept_,
                                   -0.15, atol=1e-4)

        y_pred = scalar.predict(x_fd)
        np.testing.assert_allclose(y_pred, y_pred_compare, atol=1e-4)

        x_basis = Monomial(n_basis=3)
        x_fd = FDataBasis(x_basis, [[1, 0, 0],
                                    [0, 1, 0],
                                    [0, 0, 1],
                                    [2, 0, 1]])

        beta_fd = FDataBasis(x_basis, [3, 2, 1])
        y = [1 + 13 / 3, 1 + 29 / 12, 1 + 17 / 10, 1 + 311 / 30]

        # Non regularized
        scalar = MultivariateLinearRegression(regularization_parameter=0)
        scalar.fit(x_fd, y)
        np.testing.assert_allclose(scalar.coef_[0].coefficients,
                                   beta_fd.coefficients)
        np.testing.assert_allclose(scalar.intercept_,
                                   1)

        y_pred = scalar.predict(x_fd)
        np.testing.assert_allclose(y_pred, y)

        # Regularized
        beta_fd_reg = FDataBasis(x_basis, [2.812, 3.043, 0])
        y_reg = [5.333, 3.419, 2.697, 11.366]

        scalar_reg = MultivariateLinearRegression(
            regularization_parameter=1,
            regularization=LinearDifferentialOperatorRegularization())
        scalar_reg.fit(x_fd, y)
        np.testing.assert_allclose(scalar_reg.coef_[0].coefficients,
                                   beta_fd_reg.coefficients, atol=0.001)
        np.testing.assert_allclose(scalar_reg.intercept_,
                                   0.998, atol=0.001)

        y_pred = scalar_reg.predict(x_fd)
        np.testing.assert_allclose(y_pred, y_reg, atol=0.001)

    def test_error_X_not_FData(self):
        """Tests that at least one of the explanatory variables
        is an FData object. """

        x_fd = np.identity(7)
        y = np.zeros(7)

        scalar = MultivariateLinearRegression(coef_basis=[Fourier(n_basis=5)])

        with np.testing.assert_warns(UserWarning):
            scalar.fit([x_fd], y)

    def test_error_y_is_FData(self):
        """Tests that none of the explained variables is an FData object
        """
        x_fd = FDataBasis(Monomial(n_basis=7), np.identity(7))
        y = list(FDataBasis(Monomial(n_basis=7), np.identity(7)))

        scalar = MultivariateLinearRegression(coef_basis=[Fourier(n_basis=5)])

        with np.testing.assert_raises(ValueError):
            scalar.fit([x_fd], y)

    def test_error_X_beta_len_distinct(self):
        """ Test that the number of beta bases and explanatory variables
        are not different """

        x_fd = FDataBasis(Monomial(n_basis=7), np.identity(7))
        y = [1 for _ in range(7)]
        beta = Fourier(n_basis=5)

        scalar = MultivariateLinearRegression(coef_basis=[beta])
        with np.testing.assert_raises(ValueError):
            scalar.fit([x_fd, x_fd], y)

        scalar = MultivariateLinearRegression(coef_basis=[beta, beta])
        with np.testing.assert_raises(ValueError):
            scalar.fit([x_fd], y)

    def test_error_y_X_samples_different(self):
        """ Test that the number of response samples and explanatory samples
        are not different """

        x_fd = FDataBasis(Monomial(n_basis=7), np.identity(7))
        y = [1 for _ in range(8)]
        beta = Fourier(n_basis=5)

        scalar = MultivariateLinearRegression(coef_basis=[beta])
        with np.testing.assert_raises(ValueError):
            scalar.fit([x_fd], y)

        x_fd = FDataBasis(Monomial(n_basis=8), np.identity(8))
        y = [1 for _ in range(7)]
        beta = Fourier(n_basis=5)

        scalar = MultivariateLinearRegression(coef_basis=[beta])
        with np.testing.assert_raises(ValueError):
            scalar.fit([x_fd], y)

    def test_error_beta_not_basis(self):
        """ Test that all beta are Basis objects. """

        x_fd = FDataBasis(Monomial(n_basis=7), np.identity(7))
        y = [1 for _ in range(7)]
        beta = FDataBasis(Monomial(n_basis=7), np.identity(7))

        scalar = MultivariateLinearRegression(coef_basis=[beta])
        with np.testing.assert_raises(TypeError):
            scalar.fit([x_fd], y)

    def test_error_weights_lenght(self):
        """ Test that the number of weights is equal to the
        number of samples """

        x_fd = FDataBasis(Monomial(n_basis=7), np.identity(7))
        y = [1 for _ in range(7)]
        weights = [1 for _ in range(8)]
        beta = Monomial(n_basis=7)

        scalar = MultivariateLinearRegression(coef_basis=[beta])
        with np.testing.assert_raises(ValueError):
            scalar.fit([x_fd], y, weights)

    def test_error_weights_negative(self):
        """ Test that none of the weights are negative. """

        x_fd = FDataBasis(Monomial(n_basis=7), np.identity(7))
        y = [1 for _ in range(7)]
        weights = [-1 for _ in range(7)]
        beta = Monomial(n_basis=7)

        scalar = MultivariateLinearRegression(coef_basis=[beta])
        with np.testing.assert_raises(ValueError):
            scalar.fit([x_fd], y, weights)


if __name__ == '__main__':
    print()
    unittest.main()
