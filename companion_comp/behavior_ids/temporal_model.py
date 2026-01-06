import numpy as np

class FeatureNormalizer:
    def __init__(self):
        self.mean = None
        self.std = None

    def fit(self, X):
        self.mean = np.mean(X, axis=0)
        self.std = np.std(X, axis=0) + 1e-6

    def transform(self, x):
        return (x - self.mean) / self.std
