import re
import sqlite3

import nltk

database = 'movies.sqlite3'
conn = sqlite3.connect(database)


def init_db():
    # NOTE: scene_num and sentence_num both start at 1
    with conn:
        conn.executescript("""
        drop table if exists Films;
        create table Films (
            id integer primary key autoincrement not null,
            name text not null
        );
        drop table if exists Scenes;
        create table Scenes  (
            id integer primary key autoincrement not null,
            scene_num int not null,
            film_id int not null references Films(id)
        );
        
        drop table if exists Sentences;
        create table Sentences (
            sentence_num int not null,
            data text not null,
            scene_id int not null references Scenes(id)
        );
        """)


def process_scene(scene):
    scene = re.sub('\n\s*[A-Z0-9()][^a-z]*[A-Z0-9():]+.?\s*\n', ' ',
                   scene)  # deal with scene numbers and camera direction
    scene = re.sub('[A-Z]?[0-9][^a-z\s]*', ' ', scene)
    scene = re.sub('\n', ' ', scene)
    scene = re.sub('CONT.+\s', ' ', scene)
    scene = re.sub('OMIT.+\s', ' ', scene)
    scene = re.sub("\s\s+", " ", scene)  # remove double spaces

    sentences = nltk.sent_tokenize(scene)
    return sentences


def process_and_load_scene(scene, film_id, scene_num):
    sentences = process_scene(scene)

    conn.execute("""insert into Scenes (film_id, scene_num) values (?, ?)""", (film_id, scene_num))
    scene_id = conn.execute('select last_insert_rowid()').fetchone()[0]

    conn.executemany("""insert into Sentences (sentence_num, scene_id, data) values (?, {}, ?)"""
                     .format(scene_id),
                     ((i + 1, sentence) for (i, sentence) in enumerate(sentences)))


def process_script(script_file):
    scene = ''
    for line in script_file.readlines():
        if any(substr in line for substr in ('EXT.', 'INT.', 'EXT:', 'INT:')):
            if scene != '':
                yield scene
            scene = ''
        else:
            line = re.sub('[^\x00-\x7F]', ' ', line)  # remove non ascii
            line = re.sub("[\t]", "", line)  # remove tabs
            line = re.sub('-[0-9A-Z].*[0-9A-Z]-', ' ', line)

            scene = scene + line

    # remove text after and including "the end"
    scene = re.sub('\n\s*([tT][Hh][Ee]\s[Ee][Nn][Dd])(.|\n)*', ' ', scene)
    yield scene


def load_script_by_file(script_file, film_name):
    conn.execute('insert into Films (name) values (?)', (film_name,))
    film_id = conn.execute('select last_insert_rowid()').fetchone()[0]

    for scene_num, scene in enumerate(process_script(script_file)):
        process_and_load_scene(scene, film_id, scene_num)


def load_script(filename):
    with conn:
        filepath = '../scripts/' + filename
        with open(filepath, "r") as f:
            load_script_by_file(f, filename.split('.')[0])


if __name__ == '__main__':
    init_db()
    try:
        # grossing
        load_script("Avatar.txt")
        load_script("Dark-Knight-Rises,-The.txt")
        load_script("Spider-Man.txt")
        load_script("Pirates-of-the-Caribbean.txt")
        load_script("Frozen.txt")
        load_script("Star-Wars-Revenge-of-the-Si.txt")
        load_script("Star-Wars-The-Force-Awakens.txt")
        load_script("Lord-of-the-Rings-Return-of-the-King.txt")
        load_script("Mission-Impossible.txt")
        load_script("Shrek-the-Third.txt")
        # rated
        load_script("Boyhood.txt")
        load_script("Lost-in-Translation.txt")
        load_script("12-Years-a-Slave.txt")
        load_script("Social-Network,-The.txt")
        load_script("Boyhood.txt")
        load_script("Zero-Dark-Thirty.txt")
        load_script("Wall-E.txt")
        load_script("Sideways.txt")
        load_script("Amour.txt")
        load_script("Crouching-Tiger,-Hidden-Dragon.txt")
        # bad
        load_script("Hudson-Hawk.txt")
        load_script("Catwoman.txt")
    except Exception as e:
        print(e)
