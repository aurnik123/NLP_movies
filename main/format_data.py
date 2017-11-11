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
            id integer primary key autoincrement,
            data text,
            anger int default 0,
            disgust int default 0,
            fear int default 0,
            joy int default 0,
            sadness int default 0,
            surprise int default 0
        );
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
            end,
            strongest_emotion
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
                conn.execute('insert into Texts (data) values (?)', (child.text,))
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
    if ignore_emotion_strength:
        directory = '../data/Potter/agree-sent'
        with conn:
            for filename in os.listdir(directory):
                path = os.path.join(directory, filename)
                with open(path) as f:
                    reader = csv.reader(f, delimiter='@', quotechar='|')
                    for row in reader:
                        conn.execute('insert into Texts (data) values (?)', (row[2],))
                        insert_id = conn.execute('select last_insert_rowid()').fetchone()[0]
                        conn.execute('insert into Emotion_Text_Map (text_id, emotion_id) values (?, ?)',
                                     (insert_id, row[1]))
                        if row[1] == '2':
                            # add sentences marked with anger/disgust merged label into both emotions
                            conn.execute('insert into Emotion_Text_Map (text_id, emotion_id) values (?, ?)',
                                         (insert_id, 1))
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
                        # don't insert sentence into database if only neutral emotion labeled
                        if emotion_strengths:
                            conn.execute("""insert into Texts (data, anger, disgust, fear, joy, sadness, surprise)
                                            values (?, ?, ?, ?, ?, ?, ?)""",
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

    sentence_emotions = {}

    sentence_id_map = {}

    def process_emotion(sentence_id, emotion):
        if sentence_id in sentence_emotions:
            if emotion in core_emotions:
                sentence_emotions[sentence_id][emotion] += 2
            elif emotion in emotion_dict:
                for parent_emotion in emotion_dict[emotion]:
                    sentence_emotions[sentence_id][parent_emotion] += 1
            else:
                # tracked to decrease confidence/weight of other emotions
                sentence_emotions[sentence_id]['other'] += 2

    # TODO: consider adding ambiguous/neutral as an emotion to the Texts table, so emotionless/neutral sentences don't get falsely classified as other things
    # alternatively, just filter out classifications that are below a certain strength threshold

    # NOTE: sentences not necessarily read in order, so need to keep track of idiom_id to match emotion classifications
    with open('../labeled_data/CrowdFlower/plutchik-wheel-full-DFE.csv', 'rU') as f:
        reader = csv.reader(f)
        headers = reader.next()
        for row in reader:
            emotion = row[14].lower()
            sentence_id = int(row[17])
            sentence = row[18]
            if sentence_id not in sentence_emotions:
                sentence_id_map[sentence_id] = sentence
                sentence_emotions[sentence_id] = Counter()
            process_emotion(sentence_id, emotion)

    with conn:
        for sentence_id, temp_dict in sentence_emotions.iteritems():
            total = 0
            strongest_emotion = None
            max_strength = 0
            for emotion, strength in temp_dict.iteritems():
                total += strength
                if strength > max_strength:
                    strongest_emotion = emotion
                    max_strength = strength
            if strongest_emotion != 'other':
                sentence = sentence_id_map[sentence_id]
                arguments = [sentence]
                for emotion, strength in temp_dict.iteritems():
                    temp_dict[emotion] = int(round(temp_dict[emotion] * 100. / total))
                for emotion in ('anger', 'disgust', 'fear', 'joy', 'sadness', 'surprise'):
                    arguments.append(temp_dict.get(emotion, 0))
                conn.execute("""insert into Texts (data, anger, disgust, fear, joy, sadness, surprise)
                                values (?, ?, ?, ?, ?, ?, ?)""", arguments)


def load_tweets():
    # TODO: filter out words with @ signs before adding to sentence database (don't contribute to sentiment)
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
                sentence = filter_sentence(row[3])
                if row[1] in core_emotions:
                    emotion = row[1]
                elif row[1] in emotion_dict:
                    emotion = emotion_dict[row[1]]
                else:
                    continue
                # ignore sentences with encoding errors
                try:
                    conn.execute("""insert into Texts (data, {}) values (?, 100)""".format(emotion), (sentence,))
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
    # tweet data ignored for now since less likely to be useful for script analysis without additional processing
    # (typos, content type mismatch, etc.)
    # load_tweets()
