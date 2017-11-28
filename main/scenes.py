import csv
import os
import re
import sqlite3
import xml.etree.cElementTree as ET
from collections import Counter

database = 'movies.db'
conn = sqlite3.connect(database)

# TOOD: consider flattening db
def init_db():
    with conn:
        # NOTE: no foreign keys created to increase performance
        # NOTE: indices not created as db is unlikely to be used frequently for queries
        conn.executescript("""
        drop table if exists Scenes;
        create table Scenes  (
            id integer primary key not null,
            data text
        );


        """)


def load_script():
    with conn:
        text_dict = {}
        filepath = "../scripts/8MM.txt"
        script = open(filepath, "r")

        sceneNum = 0
        scene = ''
        sceneList = []
        for line in script.readlines():
            if (line.find("EXT.") != -1) or (line.find("INT.") != -1):
                print scene
                conn.execute("""insert into Scenes (id, data) values (?,?)""", (sceneNum,scene))

                sceneNum = sceneNum+1
                scene = ''

            else:
                line = line.replace(':', '').replace('\n', '')
                re.sub("\t", "", line)
                re.sub("\s\s+" , " ", line)
                scene = scene + line
            #if (line.find()) Find the end





if __name__ == '__main__':
    init_db()
    # headline data
    load_script()
