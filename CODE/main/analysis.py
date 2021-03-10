import math
import sqlite3
import string

from collections import Counter
import csv

from format_data import core_emotions, all_emotions

import nltk
import numpy as np
import scipy.sparse as sp
from nltk.stem.porter import PorterStemmer
from sklearn.externals import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import SGDClassifier
from sklearn.model_selection import cross_val_score
from sklearn.model_selection import train_test_split
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

    def analyze_scripts(self, film_name=None):

        if self.emotions == 'core':
            emotion_order = core_emotions
        else:
            emotion_order = all_emotions

        emotion_order += ('neutral',)

        headers = ('scene',) + emotion_order
        # NOTE: joins would probably be faster but a bit harder to parse afterwards
        with sqlite3.connect('movies.sqlite3') as conn:
            if film_name:
                film_rows = conn.execute("select id, name from films where film_name = ?", (film_name,))
            else:
                film_rows = conn.execute('select id, name from films')


            for film_row in film_rows:
                film_id = film_row[0]
                film_name = film_row[1]

                filepath = '../film_sentiment_predictions/' + film_name + '.csv'

                with open(filepath, 'wb') as csvfile:
                    writer = csv.writer(csvfile, quotechar='|', quoting=csv.QUOTE_MINIMAL)
                    writer.writerow(headers)

                    scene_rows = conn.execute('select id, scene_num from scenes where film_id = ? order by scene_num',
                                              (film_id,))
                    for scene_row in scene_rows:
                        scene_id = scene_row[0]
                        scene_num = scene_row[1]
                        sentence_rows = conn.execute('select data from sentences where scene_id = ? order by sentence_num',
                                                     (scene_id,))

                        num_sentences = 0
                        emotion_counter = Counter()
                        for sentence_row in sentence_rows:
                            sentence = sentence_row[0]
                            emotion = self.predict(sentence)[0]
                            emotion_counter[emotion] += 1.0
                            num_sentences += 1

                        if num_sentences > 0:
                            output_row = [scene_num]
                            for emotion in emotion_order:
                                output_row.append(emotion_counter[emotion] * 100. / num_sentences)

                            writer.writerow(output_row)

if __name__ == '__main__':
    # Driver(emotions='core', use_external_sentiment=False).analyze()
    # text_data = ['I am loving life today', 'I like you']
    model = Driver(emotions='core', use_external_sentiment=False).fit()

    joblib.dump(model, 'driver_model.pkl')
    # model.predict(text_data, print_predictions=True)
    # model = joblib.load('driver_model.pkl')
    model.analyze_scripts()
