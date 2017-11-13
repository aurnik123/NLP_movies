import csv
import os
import sqlite3
import xml.etree.cElementTree as ET
from collections import Counter

conn = sqlite3.connect('database.db')
core_emotions = frozenset(('anger', 'disgust', 'fear', 'joy', 'sadness', 'surprise'))


# TOOD: consider flattening db
def init_db():
    with conn:
        # NOTE: no foreign keys created to increase performance
        # NOTE: indices not created as db is unlikely to be used frequently for queries
        conn.executescript("""
        drop table if exists Texts;
        create table Texts  (
            id integer primary key autoincrement not null,
            data text,
            anger int default 0 not null,
            disgust int default 0 not null,
            fear int default 0 not null,
            joy int default 0 not null,
            sadness int default 0 not null,
            surprise int default 0 not null,
            origin_id int not null
        );
        
        create index if not exists texts_origin_id_idx on texts(origin_id);
        
        drop view if exists Strongest_Emotions;
        create view Strongest_Emotions
        as
        select data,
            case strongest_emotion
                when anger then 'anger'
                when disgust then 'disgust'
                when fear then 'fear'
                when joy then 'joy'
                when sadness then 'sadness'
                when surprise then 'surprise'
            end as strongest_emotion,
            strongest_emotion as strength, origin_id
          from (
        select max(anger, disgust, fear, joy, sadness, surprise) as strongest_emotion, * from texts
        );
        """)


def load_affective_data():
    text_dict = {}

    def load_xml(filepath):
        tree = ET.parse(filepath)
        root = tree.getroot()
        # NOTE: not directly using ids as may conflict with other files later if not loaded in correct order
        # maps xml id to db id
        for child in root:
            with conn:
                conn.execute('insert into Texts (data, origin_id) values (?, 1)', (child.text,))
                insert_id = conn.execute('select last_insert_rowid()').fetchone()[0]
                text_dict[child.attrib['id']] = insert_id

    def load_emotions(filepath):

        def emotion_generator():
            with open(filepath) as f:
                reader = csv.reader(f, delimiter=' ', quotechar='|')
                with conn:
                    for row in reader:
                        text_id = text_dict[row[0]]
                        yield (row[1], row[2], row[3], row[4], row[5], row[6], text_id)

        with conn:
            conn.executemany("""update texts set anger = ?, disgust = ?, fear = ?, joy = ?, sadness = ?, surprise = ?
                                where id = ?;
                             """,
                             emotion_generator())

    load_xml('../labeled_data/AffectiveText.Semeval.2007/AffectiveText.trial/affectivetext_trial.xml')
    load_xml('../labeled_data/AffectiveText.Semeval.2007/AffectiveText.test/affectivetext_test.xml')

    load_emotions('../labeled_data/AffectiveText.Semeval.2007/AffectiveText.trial/affectivetext_trial.emotions.gold')
    load_emotions('../labeled_data/AffectiveText.Semeval.2007/AffectiveText.test/affectivetext_test.emotions.gold')


# gives each person's label a weight of 25
def load_potter_data(ignore_emotion_strength=False):
    emotion_map = {
        '3': 'fear',
        '4': 'joy',
        '6': 'sadness',
        '7': 'surprise'
    }

    if ignore_emotion_strength:
        directory = '../labeled_data/Potter/agree-sent'
        with conn:
            for filename in os.listdir(directory):
                path = os.path.join(directory, filename)
                with open(path) as f:
                    reader = csv.reader(f, delimiter='@', quotechar='|')
                    for row in reader:
                        if row[1] == '2':
                            conn.execute(
                                """insert into Texts (data, anger, disgust, origin_id) values (?, 100, 100, 2)""",
                                (row[2],))
                        else:
                            emotion = emotion_map[row[1]]
                            conn.execute(
                                """insert into Texts (data, origin_id, {}) values (?, 2, 100)""".format(emotion),
                                (row[2],))

    else:
        directory = '../labeled_data/Potter/emmood'
        emotion_dict = {
            'A': 1,
            'D': 2,
            'F': 3,
            'H': 4,
            'N': None,
            'S': 5,
            'Sa': 5,
            # TODO: consider differentiating between positive/negative surprised (maybe add to strength of angry/happy?)
            'Su+': 6,
            '+': 6,
            'Su-': 6,
            '-': 6
        }

        def process_emotion_labels(labels):
            emotion_strengths = Counter()
            for label in labels:
                emotions = label.split(':')
                for emotion in emotions:
                    emotion_id = emotion_dict[emotion]
                    if emotion_id is not None:
                        emotion_strengths[emotion_id] += 25
            return emotion_strengths

        with conn:
            for filename in os.listdir(directory):
                path = os.path.join(directory, filename)
                with open(path) as f:
                    reader = csv.reader(f, delimiter='\t', quotechar='|')
                    for row in reader:
                        emotion_strengths = process_emotion_labels([row[1], row[2]])
                        conn.execute("""insert into Texts (data, anger, disgust, fear, joy, sadness, surprise, origin_id)
                                        values (?, ?, ?, ?, ?, ?, ?, 2)""",
                                     (row[3], emotion_strengths[1], emotion_strengths[2], emotion_strengths[3],
                                      emotion_strengths[4], emotion_strengths[5], emotion_strengths[6]))


def load_plutchik_data():
    # non-core emotions. Each list entry should contribute half the weight of an entry in core_emotions
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

    sentence_data = {}

    # TODO: reconsider point allocation for non_core emotions
    def process_emotion(sentence, emotion):
        if emotion in core_emotions:
            sentence_data[sentence][0][emotion] += 2
        elif emotion in emotion_dict:
            for parent_emotion in emotion_dict[emotion]:
                sentence_data[sentence][0][parent_emotion] += 1
        sentence_data[sentence][1] += 2

    # NOTE: sentences not necessarily read in order and no identifier provided is unique per sentence, so sentence_id dict mapping sentences to emotions needed
    with open('../labeled_data/CrowdFlower/plutchik-wheel-full-DFE.csv', 'rU') as f:
        reader = csv.reader(f)
        headers = reader.next()
        for row in reader:
            emotion = row[14].lower()
            sentence = row[18]
            if sentence not in sentence_data:
                sentence_data[sentence] = [Counter(), 0]
            process_emotion(sentence, emotion)

    with conn:
        for sentence, (temp_dict, max_points) in sentence_data.iteritems():
            arguments = [sentence]
            for emotion, strength in temp_dict.iteritems():
                temp_dict[emotion] = int(round(temp_dict[emotion] * 100. / max_points))
            for emotion in ('anger', 'disgust', 'fear', 'joy', 'sadness', 'surprise'):
                arguments.append(temp_dict[emotion])
            conn.execute("""insert into Texts (data, anger, disgust, fear, joy, sadness, surprise, origin_id)
                            values (?, ?, ?, ?, ?, ?, ?, 3)""", arguments)


def load_tweets():
    def filter_sentence(sentence):
        sentence = sentence.split(' ')
        output_sentence = ''
        for word in sentence:
            if not ('@' in word or '.com' in word or 'http' in word):
                output_sentence += word + ' '
        return output_sentence[:-1]

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

    # emotions: love, relief, neutral, anger, sadness, empty, surprise, fun, enthusiasm, happiness, hate, worry, boredom
    with open('../labeled_data/CrowdFlower/text_emotion.csv', 'rU') as f:
        with conn:
            reader = csv.reader(f)
            header = reader.next()
            for row in reader:
                try:
                    sentence = filter_sentence(row[3])
                    if row[1] in core_emotions:
                        emotion = row[1]

                    elif row[1] in emotion_dict:
                        emotion = emotion_dict[row[1]]

                    else:
                        # emotion isn't 1 of the 6 core emotions
                        conn.execute("""insert into Texts (data, origin_id) values (?, 4)""", (sentence,))
                        continue
                    # ignore sentences with encoding errors
                    conn.execute("""insert into Texts (data, {}, origin_id) values (?, 100, 4)""".format(emotion),
                                 (sentence,))
                except Exception:
                    pass


if __name__ == '__main__':
    init_db()
    # headline data
    load_affective_data()
    # storybook sentences
    load_potter_data()
    # various sentences (appear to be from stories?)
    load_plutchik_data()
    # tweets
    load_tweets()
