import math
import sqlite3
import string

import nltk
import numpy as np
import scipy.sparse as sp
from nltk.stem.porter import PorterStemmer
from sklearn.model_selection import cross_val_score
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.externals import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import SGDClassifier
from sklearn.metrics import classification_report
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
    def __init__(self, emotions='all', use_external_sentiment=False):
        self.emotions = emotions
        self.conn = get_connection(emotions)
        self.data = self.get_data()
        self.use_external_sentiment = use_external_sentiment
        # best so far: huber, log, epsilon_insensitive
        # elasticnet
        self.model = SGDClassifier(loss='hinge', penalty='l2', max_iter=100)
        self.tfidf = TfidfVectorizer(tokenizer=tokenize, stop_words='english')

    def get_data(self):
        with self.conn as conn:
            results = conn.execute(
                "select data, strongest_emotion from strongest_emotions where origin_id < 4 and strength > 50"
            )
            text_data, y = [], []
            for row in results:
                text_data.append(str(row[0]))
                y.append(row[1])
            return np.array(text_data), np.array(y)

    def _get_processed_data(self):
        text_data, y = self.data

        X = self.tfidf.fit_transform(text_data)

        # add sentiment and polarity from external library analysis
        if self.use_external_sentiment:
            new_cols = sp.csr_matrix((X.shape[0], 2))
            for i, data in enumerate(text_data):
                sentiment = TextBlob(data).sentiment
                new_cols[i] = np.array(sentiment)

            X = sp.hstack((X, new_cols), format='csr')
        return X, y

    def analyze(self):
        X, y = self._get_processed_data()

        # used to match train-test split to original X, y
        indices = np.arange(X.shape[0])

        X_train, X_test, y_train, y_test, idx_train, idx_test = train_test_split(X, y, indices, test_size=0.2)

        # self.model = RandomForestClassifier(n_estimators=100)
        self.model.fit(X=X_train, y=y_train)

        joblib.dump(self.model, 'model.pkl')

        # print(self.model.get_params)
        #
        # pred = self.model.predict(X_test)
        # for i in xrange(X_test.shape[0]):
        #     print(self.data[0][idx_test[i]], pred[i], y_test[i])
        #
        # print(classification_report(y_test, pred))
        #
        # print(self.model.score(X_test, y_test))

        print(cross_val_score(self.model, X, y, cv=5))

    def fit(self):
        X, y = self._get_processed_data()
        self.model.fit(X, y)
        return self

    def predict(self, text_data, print_predictions=False):
        if isinstance(text_data, str) or isinstance(text_data, unicode):
            text_data = (text_data,)
        X = self.tfidf.transform(text_data)
        pred = self.model.predict(X)
        if print_predictions:
            for i in xrange(len(text_data)):
                print(text_data[i], pred[i])
        return pred


if __name__ == '__main__':
    # Driver(emotions='core', use_external_sentiment=False).analyze()
    X = ['I am loving life today', 'I like you']
    Driver(emotions='core', use_external_sentiment=False).fit().predict(X, print_predictions=True)

