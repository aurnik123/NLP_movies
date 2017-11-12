import sqlite3
import string

import nltk
import numpy as np

from nltk.stem.porter import PorterStemmer

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.multioutput import MultiOutputRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LogisticRegression

import math

conn = sqlite3.connect('database.db')

stemmer = PorterStemmer()


def get_data():
    with conn:
        results = conn.execute(
            'select data, anger, disgust, fear, joy, sadness, surprise from texts where origin_id = 3')
        text_data, y = [], []
        for row in results:
            text_data.append(str(row[0]))
            y.append(row[1:])
        return np.array(text_data), np.array(y)


def tokenize(text):
    tokens = nltk.word_tokenize(str(text).lower().translate(None, string.punctuation))
    for i, token in enumerate(tokens):
        tokens[i] = stemmer.stem(token)
    return tokens


# calculates mse
def calc_rmse(y_pred, y):
    return math.sqrt(np.sum((y_pred - y) ** 2) / y_pred.size)


if __name__ == '__main__':
    text_data, y = get_data()

    tfidf = TfidfVectorizer(tokenizer=tokenize, stop_words='english')
    feature_vectors = tfidf.fit_transform(text_data)

    X_train, X_test, y_train, y_test = train_test_split(feature_vectors, y, test_size=0.2, random_state=0)

    model = MultiOutputRegressor(RandomForestRegressor())
    model.fit(X=X_train, y=y_train)
    print(model.score(X_test, y_test))

    y_pred = model.predict(X_test)
    print(calc_rmse(y_pred, y_test))

