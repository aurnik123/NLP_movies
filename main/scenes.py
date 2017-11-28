import csv
import os
import re
import sqlite3
import xml.etree.cElementTree as ET
from collections import Counter

database = 'movies.db'
conn = sqlite3.connect(database)

def init_db():
    with conn:
        conn.executescript("""
        drop table if exists Scenes;
        create table Scenes  (
            id integer primary key autoincrement not null,
            film text not null,
            scene integer not null,
            data text
        );


        """)

#filepath is name of txt file in scripts folder (eg 8MM.txt)
def load_script(filepath):
    with conn:
        count = 0
        #for filepath in os.listdir('../scripts'):
        text_dict = {}
        #filepath = "test.txt"
        script = open("../scripts/" + filepath, "r")
        film = filepath[11:]

        sceneNum = 0
        scene = ''
        sceneList = []
        for line in script.readlines():
            if (line.find("EXT.") != -1) or (line.find("INT.") != -1) or (line.find("EXT:") != -1) or (line.find("INT:") != -1):
                if sceneNum != 0:
                    scene = re.sub('\n\s*[A-Z0-9()][^a-z]*[A-Z0-9():]+.?\s*\n', ' ', scene) #deal with scene numbers and camera direction
                    scene = re.sub('[A-Z]?[0-9][^a-z\s]*',' ', scene)
                    scene = re.sub('\n', ' ', scene)
                    scene = re.sub('CONT.+\s', ' ',scene)
                    scene = re.sub('OMIT.+\s', ' ',scene)
                    scene = re.sub("\s\s+" , " ", scene) #remove double spaces
                    print(scene)
                    conn.execute("""insert into Scenes ( film,scene, data) values (?,?,?)""", (film, sceneNum, scene))

                sceneNum = sceneNum+1
                scene = ''

            else:
                line = re.sub('[^\x00-\x7F]',' ', line) # remove non ascii
                line = re.sub("[\t]", "", line) #remove tabs
                line = re.sub('-[0-9A-Z].*[0-9A-Z]-',' ',line)

                scene = scene + line
        scene = re.sub('([tT]?[Hh]?[Ee]?\s?[Ee][Nn][Dd])(.|\n)*', '', scene)
        scene = re.sub('\n\s*[A-Z0-9()][^a-z]*[A-Z0-9():]+.?\s*\n', ' ', scene) #deal with scene numbers and camera direction
        scene = re.sub('[A-Z]?[0-9][^a-z\s]*',' ', scene)
        scene = re.sub('\n', ' ', scene)
        scene = re.sub('CONT.+\s', ' ',scene)
        scene = re.sub('OMIT.+\s', ' ',scene)
        scene = re.sub("\s\s+" , " ", scene) #remove double spaces
        #print(scene)
        conn.execute("""insert into Scenes ( film,scene, data) values (?,?,?)""", (film, sceneNum, scene))

        count = count +1
        print("count: "+ str(count))




if __name__ == '__main__':
    init_db()
    # headline data
    load_script("8MM.txt")
