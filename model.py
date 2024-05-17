import pickle
from sklearn.neighbors import NearestNeighbors
from sklearn.decomposition import NMF
import numpy as np

class UserBasedCF:
    def __init__(self):
        self.model = None
        self.user_item_matrix = None
        self.users = None
        self.items = None

    def fit(self, train_data):
        self.user_item_matrix = train_data.pivot(index='user_id', columns='game_id', values='rating').fillna(0)
        self.users = self.user_item_matrix.index.tolist()
        self.items = self.user_item_matrix.columns.tolist()
        self.model = NearestNeighbors(metric='cosine', algorithm='brute')
        self.model.fit(self.user_item_matrix.values)

    def predict(self, user_id, game_id):
        if user_id not in self.users or game_id not in self.items:
            return np.nan
        user_index = self.users.index(user_id)
        distances, indices = self.model.kneighbors(self.user_item_matrix.iloc[user_index, :].values.reshape(1, -1), n_neighbors=5)
        sim_users = indices.flatten()
        sim_scores = self.user_item_matrix.iloc[sim_users, self.items.index(game_id)]
        return sim_scores.mean()

    def save(self, path):
        with open(path, 'wb') as f:
            pickle.dump(self, f)

    @staticmethod
    def load(path):
        with open(path, 'rb') as f:
            return pickle.load(f)

class ItemBasedCF:
    def __init__(self):
        self.model = None
        self.item_user_matrix = None
        self.users = None
        self.items = None

    def fit(self, train_data):
        self.item_user_matrix = train_data.pivot(index='game_id', columns='user_id', values='rating').fillna(0)
        self.items = self.item_user_matrix.index.tolist()
        self.users = self.item_user_matrix.columns.tolist()
        self.model = NearestNeighbors(metric='cosine', algorithm='brute')
        self.model.fit(self.item_user_matrix.values)

    def predict(self, user_id, game_id):
        if user_id not in self.users or game_id not in self.items:
            return np.nan
        item_index = self.items.index(game_id)
        distances, indices = self.model.kneighbors(self.item_user_matrix.iloc[item_index, :].values.reshape(1, -1), n_neighbors=5)
        sim_items = indices.flatten()
        sim_scores = self.item_user_matrix.iloc[sim_items, self.users.index(user_id)]
        return sim_scores.mean()

    def save(self, path):
        with open(path, 'wb') as f:
            pickle.dump(self, f)

    @staticmethod
    def load(path):
        with open(path, 'rb') as f:
            return pickle.load(f)

class MatrixFactorizationCF:
    def __init__(self):
        self.model = None
        self.user_item_matrix = None
        self.users = None
        self.items = None

    def fit(self, train_data):
        self.user_item_matrix = train_data.pivot(index='user_id', columns='game_id', values='rating').fillna(0)
        self.users = self.user_item_matrix.index.tolist()
        self.items = self.user_item_matrix.columns.tolist()
        self.model = NMF(n_components=20, init='random', random_state=42)
        self.W = self.model.fit_transform(self.user_item_matrix.values)
        self.H = self.model.components_

    def predict(self, user_id, game_id):
        if user_id not in self.users or game_id not in self.items:
            return np.nan
        user_index = self.users.index(user_id)
        item_index = self.items.index(game_id)
        prediction = np.dot(self.W[user_index, :], self.H[:, item_index])
        return prediction

    def save(self, path):
        with open(path, 'wb') as f:
            pickle.dump(self, f)

    @staticmethod
    def load(path):
        with open(path, 'rb') as f:
            return pickle.load(f)
