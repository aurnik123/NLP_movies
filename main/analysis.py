import math
import sqlite3
import string

import nltk
import numpy as np
import scipy.sparse as sp
from nltk.stem.porter import PorterStemmer
from sklearn.ensemble import RandomForestRegressor
from sklearn.externals import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import SGDClassifier
from sklearn.metrics import classification_report
from sklearn.model_selection import cross_val_score
from sklearn.model_selection import train_test_split
from sklearn.multioutput import MultiOutputRegressor
from textblob import TextBlob

stemmer = PorterStemmer()


def tokenize(text):
    return map(stemmer.stem, nltk.word_tokenize(str(text).lower().translate(None, string.punctuation)))


# calculates mse
def calc_rmse(y_pred, y):
    return math.sqrt(np.sum((y_pred - y) ** 2) / y_pred.size)


def get_connection(emotions='all'):
    filename = emotions + '_emotions.sqlite3'
    return sqlite3.connect(filename)


class Driver:
    def __init__(self, method='classification', emotions='all', use_external_sentiment=False):
        self.method = method
        self.emotions = emotions
        self.conn = get_connection(emotions)
        self.data = self.get_data()
        self.use_external_sentiment = use_external_sentiment

    def get_data(self):
        with self.conn as conn:
            if self.method == 'regression':
                results = conn.execute(
                    'select data, anger, disgust, fear, joy, sadness, surprise from texts where origin_id = 3 and strength > 70')
                text_data, y = [], []
                for row in results:
                    text_data.append(str(row[0]))
                    y.append(row[1:])
                return np.array(text_data), np.array(y)
            else:
                results = conn.execute(
                    "select data, strongest_emotion from strongest_emotions where origin_id = 3 and strength > 50"
                )
                text_data, y = [], []
                for row in results:
                    text_data.append(str(row[0]))
                    y.append(row[1])
                return np.array(text_data), np.array(y)

    def print_predictions(self, model, X_test, y_test):
        pred = model.predict(X_test)
        print(classification_report(y_test, pred))
        for i in xrange(X_test.shape[0]):
            print(self.data[0][i], pred[i], y_test[i])

    def analyze(self):

        text_data, y = self.get_data()

        tfidf = TfidfVectorizer(tokenizer=tokenize, stop_words='english')

        X = tfidf.fit_transform(text_data)
        new_cols = sp.csr_matrix((X.shape[0], 2))
        indices = np.arange(X.shape[0])

        # add sentiment and polarity from external library analysis
        if self.use_external_sentiment:
            for i, data in enumerate(text_data):
                sentiment = TextBlob(data).sentiment
                new_cols[i] = np.array(sentiment)

            X = sp.hstack((X, new_cols), format='csr')

        X_train, X_test, y_train, y_test, idx_train, idx_test = train_test_split(X, y, indices, test_size=0.2)

        if self.method == 'regression':
            model = MultiOutputRegressor(RandomForestRegressor(n_estimators=100, min_samples_leaf=50))
            model.fit(X=X_train, y=y_train)
            joblib.dump(model, 'model.pkl')

            # use to load trained model if good trained model is created
            # model = joblib.load('model.pkl')

            print(model.score(X_test, y_test))

            y_pred = model.predict(X_test)
            print(calc_rmse(y_pred, y_test))
        else:
            # best so far: huber, log, epsilon_insensitive
            # elasticnet
            model = SGDClassifier(loss='hinge', penalty='l2', max_iter=50)
            model.fit(X=X_train, y=y_train)

            joblib.dump(model, 'model.pkl')

            # print(model.get_params)
            #
            # pred = model.predict(X_test)
            # for i in xrange(X_test.shape[0]):
            #     print(self.data[0][idx_test[i]], pred[i], y_test[i])
            #
            # print(model.score(X_test, y_test))
            print(cross_val_score(model, X, y, cv=5))


if __name__ == '__main__':
    Driver(method='classification', emotions='core', use_external_sentiment=False).analyze()
