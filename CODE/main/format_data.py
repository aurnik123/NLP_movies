import csv
import os
import sqlite3
import xml.etree.cElementTree as ET
from collections import Counter

import numpy as np

# TODO: consider consolidating 'neutral', 'empty', and 'ambiguous'
core_emotions = ('anger', 'disgust', 'fear', 'joy', 'sadness', 'surprise')
all_emotions = ('anger', 'disgust', 'fear', 'joy', 'sadness', 'surprise', 'awe', 'optimism', 'ambiguous',
                'love', 'submission', 'anticipation', 'contempt', 'trust', 'aggression', 'disapproval', 'remorse',
                'relief', 'empty', 'fun', 'enthusiasm', 'hate', 'worry', 'boredom')


def init_db(emotions='core', include_neutral=True):
    if emotions == 'core':
        emotion_list = core_emotions
    else:
        emotion_list = all_emotions

    if include_neutral:
        emotion_list += ('neutral',)

    db_name = Data.get_db_name(emotions)
    conn = sqlite3.connect(db_name)

    # db schema:
    # (Table) Texts = (id int, data text, emotion numeric, origin_id int) for all emotions
    # emotions = core_emotions if emotions = 'core', all_emotions otherwise
    # origin_id: 1 = Affective (headlines), 2 = Potter (storybook/fairy tales), 3 = Plutchik (text), 4 = Tweet
    # (View) Strongest_Emotions = (data_id int, data text, strongest_emotion text, strength numeric, origin_id int)
    with conn:
        query = """
                    drop table if exists Texts;
                    create table Texts  (
                        id integer primary key autoincrement not null,
                        data text not null"""

        for emotion in emotion_list:
            query += ',\n{} numeric default 0 not null'.format(emotion)

        query += """,\norigin_id int not null
                    );

                    drop view if exists Strongest_Emotions;
                    create view Strongest_Emotions
                    as
                    select id as data_id, data,
                        case strongest_emotion
                 """
        for emotion in emotion_list:
            query += "\nwhen {0} then '{0}'".format(emotion)

        query += """
                     end as strongest_emotion,
                        strongest_emotion as strength, origin_id
                      from (
                    select max(
                """

        query += ','.join(emotion_list)

        query += """
                    ) as strongest_emotion, * from texts
                                );
                 """
        conn.executescript(query)


class Data:
    def __init__(self, emotions='core', include_neutral=True):
        self.emotions = emotions
        self.include_neutral = include_neutral
        self.db = self.get_db_name(emotions)
        self.conn = sqlite3.connect(self.db)

    @staticmethod
    def get_db_name(emotions):
        return emotions + '_emotions.sqlite3'

    def load_all(self):
        init_db(self.emotions)
        class_list = [AffectiveData, PotterData, PlutchikData, TweetData]
        for clazz in class_list:
            clazz(self.emotions, self.include_neutral).load()


# headline data
# emotions = core_emotions
class AffectiveData(Data):
    emotion_order = ('anger', 'disgust', 'fear', 'joy', 'sadness', 'surprise')

    def __init__(self, emotions='core', include_neutral=True, strength_threshold=50):
        Data.__init__(self, emotions, include_neutral)
        self.text_dict = {}
        self.strength_threshold = strength_threshold

    def _load_xml(self, filepath):
        tree = ET.parse(filepath)
        root = tree.getroot()
        # NOTE: not directly using ids as may conflict with other files later if not loaded in correct order
        # maps xml id to db id
        for child in root:
            with self.conn:
                self.conn.execute('insert into Texts (data, origin_id) values (?, 1)', (child.text,))
                insert_id = self.conn.execute('select last_insert_rowid()').fetchone()[0]
                self.text_dict[child.attrib['id']] = insert_id

    def _load_emotions(self, filepath):
        def emotion_generator():
            with open(filepath) as f:
                reader = csv.reader(f, delimiter=' ', quotechar='|')
                with self.conn:
                    for row in reader:
                        text_id = self.text_dict[row[0]]
                        output_row = map(float, row[1:7])

                        # if strongest emotion weaker than threshold, include as neutral (or don't include if neutral invalid)
                        if max(output_row) < self.strength_threshold:
                            # neutral emotion not possible in core emotions
                            if self.include_neutral:
                                self.conn.execute('update texts set neutral = 100 where id = ?', (text_id,))
                        else:
                            # converts strengths to relative strengths (out of 100)
                            output_row = np.array(output_row) * 100 / sum(output_row)
                            output_row = np.append(output_row, text_id)
                            yield output_row

        with self.conn:
            self.conn.executemany("""update texts set anger = ?, disgust = ?, fear = ?, joy = ?, sadness = ?, surprise = ?
                                        where id = ?;
                                     """,
                                  emotion_generator())

    def load(self):

        self._load_xml('../labeled_data/AffectiveText.Semeval.2007/AffectiveText.trial/affectivetext_trial.xml')
        self._load_xml('../labeled_data/AffectiveText.Semeval.2007/AffectiveText.test/affectivetext_test.xml')

        self._load_emotions(
            '../labeled_data/AffectiveText.Semeval.2007/AffectiveText.trial/affectivetext_trial.emotions.gold')
        self._load_emotions(
            '../labeled_data/AffectiveText.Semeval.2007/AffectiveText.test/affectivetext_test.emotions.gold')


# storybook sentences
# emotions = core_emotions with some minor conversion (see emotion_dict)
class PotterData(Data):
    detailed_data_directory = '../labeled_data/Potter/emmood'
    consolidated_data_directory = '../labeled_data/Potter/agree-sent'

    emotion_dict = {
        'A': 1,
        'D': 2,
        'F': 3,
        'H': 4,
        'N': 7,
        'S': 5,
        'Sa': 5,
        # TODO: consider differentiating between positive/negative surprised (maybe add to strength of angry/happy?)
        'Su+': 6,
        '+': 6,
        'Su-': 6,
        '-': 6
    }

    all_emotions = ('anger', 'disgust', 'fear', 'joy', 'sadness', 'surprise', 'neutral', 'awe', 'ambiguous',
                    'love', 'submission', 'anticipation', 'contempt', 'trust', 'aggression', 'disapproval', 'remorse',
                    'relief', 'empty', 'fun', 'enthusiasm', 'hate', 'worry', 'boredom')

    def __init__(self, emotions='core', include_neutral=True):
        Data.__init__(self, emotions, include_neutral)

    def _process_emotion_labels(self, labels):
        emotion_strengths = Counter()
        for label in labels:
            emotions = label.split(':')
            for emotion in emotions:
                emotion_id = self.emotion_dict[emotion]
                # gives each person's label a weight of 25
                emotion_strengths[emotion_id] += 25
        return emotion_strengths

    def _get_file_rows(self):
        with self.conn:
            for filename in os.listdir(self.detailed_data_directory):
                path = os.path.join(self.detailed_data_directory, filename)
                with open(path) as f:
                    reader = csv.reader(f, delimiter='\t', quotechar='|')
                    for row in reader:
                        yield row

    def load(self):
        # core and full emotions almost same for dataset (with addition of "neutral")
        for row in self._get_file_rows():
            emotion_strengths = self._process_emotion_labels([row[1], row[2]])

            query = 'insert into Texts (data, anger, disgust, fear, joy, sadness, surprise, origin_id'

            if self.include_neutral:
                query += ', neutral) values (?, ?, ?, ?, ?, ?, ?, 2, ?)'
                self.conn.execute(query, (row[3], emotion_strengths[1], emotion_strengths[2], emotion_strengths[3],
                                          emotion_strengths[4], emotion_strengths[5], emotion_strengths[6],
                                          emotion_strengths[7]))
            else:
                query += ') values (?, ?, ?, ?, ?, ?, ?, ?, 2)'
                self.conn.execute(query, (row[3], emotion_strengths[1], emotion_strengths[2], emotion_strengths[3],
                                          emotion_strengths[4], emotion_strengths[5], emotion_strengths[6]))


# sentences from text
# emotions = awe, joy, surprise, optimism, ambiguous, disgust, sadness, love, neutral, anger, submission
# anticipation, contempt, trust, aggression, disapproval, remorse, fear
class PlutchikData(Data):
    # non-core emotions. Each list entry should contribute half the weight of an entry in core_emotions when emotions = 'core'
    emotion_dict = {
        'love': ('joy',),
        'submission': ('sadness',),
        'optimism': ('joy',),
        'remorse': ('disgust', 'sadness'),
        'contempt': ('disgust', 'anger'),
        'awe': ('surprise', 'fear'),
        'disapproval': ('sadness', 'surprise'),
        'aggression': ('anger',)
    }

    def __init__(self, emotions='core', include_neutral=True):
        Data.__init__(self, emotions, include_neutral)
        self.sentence_data = {}

    def _load_emotions_core(self):
        # TODO: reconsider point allocation for non_core emotions
        def process_emotion(sentence, emotion):
            if emotion in core_emotions or (self.include_neutral and emotion == 'neutral'):
                self.sentence_data[sentence][0][emotion] += 2
            elif emotion in self.emotion_dict:
                for parent_emotion in self.emotion_dict[emotion]:
                    self.sentence_data[sentence][0][parent_emotion] += 1
            self.sentence_data[sentence][1] += 2

        # NOTE: sentences not necessarily read in order and no identifier provided is unique per sentence, so sentence_id dict mapping sentences to emotions needed
        with open('../labeled_data/CrowdFlower/plutchik-wheel-full-DFE.csv', 'rU') as f:
            reader = csv.reader(f)
            headers = reader.next()
            for row in reader:
                emotion = row[14].lower()
                sentence = row[18]
                if sentence not in self.sentence_data:
                    self.sentence_data[sentence] = [Counter(), 0]
                process_emotion(sentence, emotion)

        with self.conn:
            for sentence, (temp_dict, max_points) in self.sentence_data.iteritems():
                arguments = [sentence]
                for emotion, strength in temp_dict.iteritems():
                    temp_dict[emotion] = temp_dict[emotion] * 100. / max_points
                for emotion in core_emotions:
                    arguments.append(temp_dict[emotion])
                if self.include_neutral:
                    arguments.append(temp_dict['neutral'])
                    self.conn.execute("""insert into Texts 
                                        (data, anger, disgust, fear, joy, sadness, surprise, origin_id, neutral)
                                        values (?, ?, ?, ?, ?, ?, ?, 3, ?)""", arguments)
                else:
                    self.conn.execute("""insert into Texts (data, anger, disgust, fear, joy, sadness, surprise, origin_id)
                                           values (?, ?, ?, ?, ?, ?, ?, 3)""", arguments)

    def _load_emotions_all(self):
        # TODO: reconsider point allocation for non_core emotions
        def process_emotion(sentence, emotion):
            self.sentence_data[sentence][0][emotion] += 1
            # increments count of number of votes/classifications for sentence
            self.sentence_data[sentence][1] += 1

        # NOTE: sentences not necessarily read in order and no identifier provided is unique per sentence, so sentence_id dict mapping sentences to emotions needed
        with open('../labeled_data/CrowdFlower/plutchik-wheel-full-DFE.csv', 'rU') as f:
            reader = csv.reader(f)
            headers = reader.next()
            for row in reader:
                emotion = row[14].lower()
                sentence = row[18]
                if sentence not in self.sentence_data:
                    self.sentence_data[sentence] = [Counter(), 0]
                process_emotion(sentence, emotion)

        with self.conn:
            for sentence, (temp_dict, max_points) in self.sentence_data.iteritems():
                arguments = []
                emotion_order = []
                for emotion, strength in temp_dict.iteritems():
                    temp_dict[emotion] = temp_dict[emotion] * 100. / max_points
                for emotion in all_emotions:
                    if emotion != 'ambiguous' and emotion in temp_dict:
                        arguments.append(str(temp_dict[emotion]))
                        emotion_order.append(emotion)
                if self.include_neutral:
                    arguments.append(str(temp_dict['neutral']))
                    emotion_order.append('neutral')

                # inserts only if there are emotions to insert
                if emotion_order:
                    query_columns = ','.join(emotion_order)
                    query_values = ','.join(arguments)
                    query = 'insert into Texts (data, {}, origin_id) values (?, {}, 3)'.format(query_columns,
                                                                                               query_values)
                    self.conn.execute(query, (sentence,))

    def load(self):
        if self.emotions == 'core':
            self._load_emotions_core()
        else:
            self._load_emotions_all()


# tweets
# emotions: love, relief, neutral, anger, sadness, empty, surprise, fun, enthusiasm, happiness, hate, worry, boredom
class TweetData(Data):
    # non-core emotions. Each list entry should contribute half the weight of an entry in core_emotions
    emotion_dict = {
        'love': 'joy',
        # TODO: consider adding contribution to surprise
        'relief': 'joy',
        'fun': 'joy',
        'enthusiasm': 'joy',
        'happiness': 'joy',
        'hate': 'anger',
        'worry': 'fear',
        'boredom': 'disgust'
    }

    def __init__(self, emotions='core', include_neutral=True):
        Data.__init__(self, emotions, include_neutral)

    def _filter_sentence(self, sentence):
        sentence = sentence.split(' ')
        output_sentence = ''
        for word in sentence:
            if not ('@' in word or '.com' in word or 'http' in word):
                output_sentence += word + ' '
        return output_sentence[:-1]

    def _load_helper(self):
        with open('../labeled_data/CrowdFlower/text_emotion.csv', 'rU') as f:
            with self.conn:
                reader = csv.reader(f)
                header = reader.next()
                for row in reader:
                    yield row

    def _process_row(self, row):
        sentence = self._filter_sentence(row[3])
        if self.emotions == 'core':
            if row[1] in core_emotions or (self.include_neutral and row[1] == 'neutral'):
                emotion = row[1]
            elif row[1] in self.emotion_dict:
                emotion = self.emotion_dict[row[1]]
            else:
                # emotion isn't 1 of the 6 core emotions and can't be mapped into core emotions
                self.conn.execute("""insert into Texts (data, origin_id) values (?, 4)""", (sentence,))
                return
        else:
            # only emotion equivalency is converted
            if row[1] == 'happiness':
                emotion = 'joy'
            elif row[1] != 'neutral' or (self.include_neutral and row[1] == 'neutral'):
                emotion = row[1]

        # ignore sentences with encoding errors
        self.conn.execute(
            """insert into Texts (data, {}, origin_id) values (?, 100, 4)""".format(emotion),
            (sentence,))

    def load(self):
        for row in self._load_helper():
            try:
                self._process_row(row)
            # ignore sentences with encoding errors leading to exceptions
            except Exception:
                pass


if __name__ == '__main__':
    Data(emotions='core', include_neutral=True).load_all()
