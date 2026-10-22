"""Statistics written with the Python standard library only.

Everything here is written out from the published formulas, so the
standard-library route depends on nothing but Python 3.9 or later:

* the regularized incomplete beta function (continued fraction, evaluated
  with the modified Lentz method), which gives the t and F distributions;
* the t quantile, found by bisection on that distribution;
* the Shapiro-Wilk W test, following Royston's algorithm AS R94 (1995),
  the method behind R's shapiro.test and jamovi's normality check.
"""

import math
from statistics import NormalDist

_NORMAL = NormalDist()


# ----------------------------------------------------------------- summaries

def mean(values):
    return math.fsum(values) / len(values)


def sample_sd(values):
    m = mean(values)
    return math.sqrt(math.fsum((x - m) ** 2 for x in values) / (len(values) - 1))


def median(values):
    s = sorted(values)
    n = len(s)
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2.0


# ------------------------------------------------- incomplete beta, t and F

def _beta_continued_fraction(a, b, x):
    """Continued fraction for I_x(a, b), modified Lentz method."""
    tiny = 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    d = tiny if abs(d) < tiny else d
    d = 1.0 / d
    h = d
    for m in range(1, 10001):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        d = tiny if abs(d) < tiny else d
        c = 1.0 + aa / c
        c = tiny if abs(c) < tiny else c
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        d = tiny if abs(d) < tiny else d
        c = 1.0 + aa / c
        c = tiny if abs(c) < tiny else c
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-16:
            return h
    raise ArithmeticError("incomplete beta continued fraction did not converge")


def incomplete_beta(a, b, x):
    """Regularized incomplete beta function I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    log_front = (math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
                 + a * math.log(x) + b * math.log1p(-x))
    if x < (a + 1.0) / (a + b + 2.0):
        return math.exp(log_front) * _beta_continued_fraction(a, b, x) / a
    return 1.0 - math.exp(log_front) * _beta_continued_fraction(b, a, 1.0 - x) / b


def t_two_sided_p(t, df):
    """P(|T| >= |t|) for Student's t with df degrees of freedom."""
    return incomplete_beta(df / 2.0, 0.5, df / (df + t * t))


def t_cdf(t, df):
    tail = 0.5 * t_two_sided_p(t, df)
    return 1.0 - tail if t > 0 else tail


def t_quantile(prob, df):
    """Quantile of Student's t, by bisection on t_cdf (0.5 < prob < 1)."""
    lo, hi = 0.0, 1.0
    while t_cdf(hi, df) < prob:
        hi *= 2.0
    for _ in range(200):
        mid = (lo + hi) / 2.0
        if t_cdf(mid, df) < prob:
            lo = mid
        else:
            hi = mid
        if hi - lo < 1e-15 * max(1.0, hi):
            break
    return (lo + hi) / 2.0


def f_upper_p(f, df1, df2):
    """P(F >= f) for the F distribution with df1 and df2 degrees of freedom."""
    return incomplete_beta(df2 / 2.0, df1 / 2.0, df2 / (df2 + df1 * f))


# ------------------------------------------------- Shapiro-Wilk (AS R94)

def _poly(coefficients, x):
    """c[0] + c[1] x + c[2] x^2 + ..."""
    result = 0.0
    for c in reversed(coefficients):
        result = result * x + c
    return result


def shapiro_wilk(values):
    """Return (W, p) for 3 <= n <= 5000, following Royston (1995), AS R94."""
    x = sorted(values)
    n = len(x)
    if n < 3 or n > 5000:
        raise ValueError("Shapiro-Wilk needs 3 to 5000 values")
    nn2 = n // 2
    a = [0.0] * (nn2 + 1)  # 1-based, as in the published algorithm
    if n == 3:
        a[1] = math.sqrt(0.5)
    else:
        an25 = n + 0.25
        summ2 = 0.0
        for i in range(1, nn2 + 1):
            # Blom-type normal scores; negative here, made positive below.
            a[i] = _NORMAL.inv_cdf((i - 0.375) / an25)
            summ2 += a[i] * a[i]
        summ2 *= 2.0
        ssumm2 = math.sqrt(summ2)
        rsn = 1.0 / math.sqrt(n)
        c1 = [0.0, 0.221157, -0.147981, -2.07119, 4.434685, -2.706056]
        c2 = [0.0, 0.042981, -0.293762, -1.752461, 5.682633, -3.582633]
        a1 = _poly(c1, rsn) - a[1] / ssumm2
        if n > 5:
            first = 3
            a2 = -a[2] / ssumm2 + _poly(c2, rsn)
            fac = math.sqrt((summ2 - 2.0 * a[1] ** 2 - 2.0 * a[2] ** 2)
                            / (1.0 - 2.0 * a1 ** 2 - 2.0 * a2 ** 2))
            a[2] = a2
        else:
            first = 2
            fac = math.sqrt((summ2 - 2.0 * a[1] ** 2) / (1.0 - 2.0 * a1 ** 2))
        a[1] = a1
        for i in range(first, nn2 + 1):
            a[i] /= -fac

    rng = x[-1] - x[0]
    if rng < 1e-19:
        raise ValueError("all values are identical")

    # Coefficient for the i-th smallest value (0-based): -a[i+1] in the lower
    # half, +a[n-i] in the upper half, 0 for the middle value when n is odd.
    def coefficient(i):
        j = n - 1 - i
        if i == j:
            return 0.0
        return -a[1 + i] if i < j else a[1 + j]

    coef = [coefficient(i) for i in range(n)]
    scaled = [v / rng for v in x]
    sa = math.fsum(coef) / n
    sx = math.fsum(scaled) / n
    ssa = math.fsum((c - sa) ** 2 for c in coef)
    ssx = math.fsum((v - sx) ** 2 for v in scaled)
    sax = math.fsum((c - sa) * (v - sx) for c, v in zip(coef, scaled))
    ssassx = math.sqrt(ssa * ssx)
    w1 = (ssassx - sax) * (ssassx + sax) / (ssa * ssx)
    w = 1.0 - w1

    if n == 3:
        p = (6.0 / math.pi) * (math.asin(math.sqrt(w)) - math.pi / 3.0)
        return w, max(p, 0.0)
    y = math.log(w1)
    if n <= 11:
        gamma = _poly([-2.273, 0.459], n)
        if y >= gamma:
            return w, 1e-99
        y = -math.log(gamma - y)
        m = _poly([0.544, -0.39978, 0.025054, -6.714e-4], n)
        s = math.exp(_poly([1.3822, -0.77857, 0.062767, -0.0020322], n))
    else:
        ln_n = math.log(n)
        m = _poly([-1.5861, -0.31082, -0.083751, 0.0038915], ln_n)
        s = math.exp(_poly([-0.4803, -0.082676, 0.0030302], ln_n))
    p = 0.5 * math.erfc((y - m) / (s * math.sqrt(2.0)))
    return w, p
