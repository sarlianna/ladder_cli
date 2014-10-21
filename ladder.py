import sys
import os.path
import sqlite3
from tabulate import tabulate
from operator import itemgetter

from elo import calc_elo_change
from schema import (
    DB_FILENAME,
    init_db
)

if not os.path.isfile(DB_FILENAME):
    init_db()
db = sqlite3.connect(DB_FILENAME)


def ladder():
    '''print all players' stats to stdout, sorted by elo.'''
    cursor = db.cursor()
    cursor.execute("SELECT name, elo, wins, losses FROM players")
    players = cursor.fetchall()
    table = []
    for player in players:
        row = [player[0], player[1], player[2], player[3]]
        table.append(row)

    table.sort(key=itemgetter(1))
    table.reverse()
    for i, player in enumerate(table):
        player.insert(0, str(i + 1))

    print tabulate(table, headers=["Rank", "Player", "Elo", "Wins", "Losses"])


def add_player(name):
    '''add a new player, identified by name.'''
    initial_elo = 1000
    cursor = db.cursor()
    player = (name, initial_elo,)
    cursor.execute("INSERT INTO players VALUES (?, ?, 0, 0)", player)
    db.commit()


def match(winner, loser):
    '''change and store player's ratings.  First player listed is assumed to have won.'''
    cursor = db.cursor()
    players = (winner, loser,)
    winner_obj = None
    loser_obj  = None
    for row in cursor.execute("SELECT name, elo, wins, losses FROM players WHERE name=? OR name=?", players):
        if row[0] == winner:
            winner_obj = row
        else:
            loser_obj = row

    winner_new_elo    = calc_elo_change(1, winner_obj[1], loser_obj[1])
    loser_new_elo     = calc_elo_change(0, loser_obj[1], winner_obj[1])
    updated_winner    = (winner_new_elo, winner_obj[2] + 1, winner_obj[3], winner_obj[0])
    updated_loser     = (loser_new_elo, loser_obj[2], loser_obj[3] + 1, loser_obj[0])

    updated = [updated_winner, updated_loser]
    cursor.executemany("UPDATE players SET elo=?, wins=?, losses=? WHERE name=?", updated)
    db.commit()

    # print results
    headers = ["Player", "Elo change", "New Elo"]
    table   = [[winner, updated_winner[0] - winner_obj[1], updated_winner[0]],
               [loser, updated_loser[0] - loser_obj[1], updated_loser[0]]]
    print tabulate(table, headers=headers)


def ffa(winner, losers):
    '''change and store a player's ratings.  Expects winner as a single player, losers as a list.'''
    pass


def print_help():
    print "Usage:"
    print "[ladder | l]               -- Print all players' ratings sorted by elo."
    print "match | m <winner> <loser> -- Change and store ratings for a single match."
    print "add <player name>          -- Add a player to the ladder. Name must be unique."


if __name__ == "__main__":
    args = sys.argv
    if len(args) == 1:
        ladder()
    elif len(args) == 2 and (args[1] == "ladder" or args[1] == "l"):
        ladder()
    elif len(args) == 4 and (args[1] == "match" or args[1] == "m"):
        match(args[2], args[3])
    elif len(args) == 3 and args[1] == "add":
        add_player(args[2])
    else:
        print_help()
    db.close()
