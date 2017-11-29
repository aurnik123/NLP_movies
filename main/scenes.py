import re
import sqlite3

database = 'movies.sqlite3'
conn = sqlite3.connect(database)


def init_db():
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
            film_id int not null,
            data text not null
        );

        drop view if exists Scene_View;
        create view Scene_View as 
            select film_id, name as film_name, data
            from Films inner join Scenes
            on Films.id = Scenes.film_id;
        """)


# filepath is name of txt file in scripts folder (eg 8MM.txt)
def load_script(filepath):
    with conn:
        count = 0
        # for filepath in os.listdir('../scripts'):
        text_dict = {}
        # filepath = "test.txt"
        script = open("../scripts/" + filepath, "r")
        film_name = filepath.split('.')[0]

        conn.execute('insert into Films (name) values (?)', (film_name,))
        film_id = conn.execute('select last_insert_rowid()').fetchone()[0]

        sceneNum = 0
        scene = ''
        for line in script.readlines():
            if any(substr in line for substr in ('EXT.', 'INT.', 'EXT:', 'INT:')):
                if sceneNum != 0:
                    scene = re.sub('\n\s*[A-Z0-9()][^a-z]*[A-Z0-9():]+.?\s*\n', ' ',
                                   scene)  # deal with scene numbers and camera direction
                    scene = re.sub('[A-Z]?[0-9][^a-z\s]*', ' ', scene)
                    scene = re.sub('\n', ' ', scene)
                    scene = re.sub('CONT.+\s', ' ', scene)
                    scene = re.sub('OMIT.+\s', ' ', scene)
                    scene = re.sub("\s\s+", " ", scene)  # remove double spaces
                    print(scene)
                    conn.execute("""insert into Scenes (film_id, data) values (?, ?)""", (film_id, scene))

                sceneNum += 1
                scene = ''

            else:
                line = re.sub('[^\x00-\x7F]', ' ', line)  # remove non ascii
                line = re.sub("[\t]", "", line)  # remove tabs
                line = re.sub('-[0-9A-Z].*[0-9A-Z]-', ' ', line)

                scene = scene + line

        scene = re.sub('([tT]?[Hh]?[Ee]?\s?[Ee][Nn][Dd])(.|\n)*', '', scene)
        scene = re.sub('\n\s*[A-Z0-9()][^a-z]*[A-Z0-9():]+.?\s*\n', ' ',
                       scene)  # deal with scene numbers and camera direction
        scene = re.sub('[A-Z]?[0-9][^a-z\s]*', ' ', scene)
        scene = re.sub('\n', ' ', scene)
        scene = re.sub('CONT.+\s', ' ', scene)
        scene = re.sub('OMIT.+\s', ' ', scene)
        scene = re.sub("\s\s+", " ", scene)  # remove double spaces
        # print(scene)
        conn.execute("""insert into Scenes (film_id, data) values (?, ?)""", (film_id, scene))

        count += 1
        print("count: " + str(count))


if __name__ == '__main__':
    init_db()
    load_script("8MM.txt")
