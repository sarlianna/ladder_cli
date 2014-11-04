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


def ladder(mode="all"):
    if mode == "all":
        modes_tables = [("1v1", "players"), ("FFA", "players_ffa"), ("2v2", "players_team")]
        for mode, table in modes_tables:
            _print_ladder(mode, table)
    elif mode == "1s":
        _print_ladder("1v1", "players")
    elif mode == "ffa":
        _print_ladder("FFA", "players_ffa")
    elif mode == "2s":
        _print_ladder("2v2", "players_team")


def _print_ladder(mode, table):
    '''print all players' stats to stdout for a particular mode stored in table, sorted by elo.'''
    cursor = db.cursor()
    cursor.execute("SELECT name, elo, wins, losses FROM {}".format(table))
    players = cursor.fetchall()
    table = []
    for player in players:
        row = [player[0], player[1], player[2], player[3]]
        table.append(row)

    table.sort(key=itemgetter(1))
    table.reverse()
    for i, player in enumerate(table):
        player.insert(0, str(i + 1))

    print "Mode: {}\n-----------------------------------------".format(mode)
    print tabulate(table, headers=["Rank", "Player", "Elo", "Wins", "Losses"])
    print "" # extra newline


def add_player(mode, name):
    '''add a new player, identified by name.'''
    initial_elo = 1000
    cursor = db.cursor()
    player = (name, initial_elo,)
    if mode == "1s":
        cursor.execute("INSERT INTO players VALUES (?, ?, 0, 0)", player)
    elif mode == "ffa":
        cursor.execute("INSERT INTO players_ffa VALUES (?, ?, 0, 0)", player)
    elif mode == "2s":
        cursor.execute("INSERT INTO players_team VALUES (?, ?, 0, 0)", player)
    elif mode == "all":
        cursor.execute("INSERT INTO players VALUES (?, ?, 0, 0)", player)
        cursor.execute("INSERT INTO players_ffa VALUES (?, ?, 0, 0)", player)
        cursor.execute("INSERT INTO players_team VALUES (?, ?, 0, 0)", player)
    db.commit()


def match(winner, loser):
    _match_update(winner, loser, "players")

def _match_update(winner, loser, table):
    '''change and store player's ratings.  First player listed is assumed to have won.'''
    cursor = db.cursor()
    players = (winner, loser,)
    winner_obj = None
    loser_obj  = None
    for row in cursor.execute("SELECT name, elo, wins, losses FROM {table} WHERE name=? OR name=?".format(table=table), players):
        if row[0] == winner:
            winner_obj = row
        else:
            loser_obj = row

    winner_new_elo    = calc_elo_change(1, winner_obj[1], loser_obj[1])
    loser_new_elo     = calc_elo_change(0, loser_obj[1], winner_obj[1])
    updated_winner    = (winner_new_elo, winner_obj[2] + 1, winner_obj[3], winner_obj[0])
    updated_loser     = (loser_new_elo, loser_obj[2], loser_obj[3] + 1, loser_obj[0])

    updated = [updated_winner, updated_loser]
    cursor.executemany("UPDATE {table} SET elo=?, wins=?, losses=? WHERE name=?".format(table=table), updated)
    db.commit()

    headers = ["Player", "Elo change", "New Elo"]
    table   = [[winner, updated_winner[0] - winner_obj[1], updated_winner[0]],
               [loser, updated_loser[0] - loser_obj[1], updated_loser[0]]]
    print tabulate(table, headers=headers)


def team(winner, second_winner, loser, second_loser):
    cursor = db.cursor()
    players = [winner, second_winner, loser, second_loser]
    winners = [winner, second_winner]
    losers  = [loser, second_loser]

    cursor.execute("SELECT name, elo, wins, losses FROM players_team WHERE name=? OR name=? OR name=? OR name=?", players)
    rows = cursor.fetchall()
    winner_objs = rows[:2]
    loser_obs = rows[2:]
    winners_elo = sum([win[1] for win in winner_objs]) / 2.0
    losers_elo = sum([lose[1] for lose in loser_objs]) / 2.0

    win_elo_change  = [_update_single(1, win, losers_elo, "players_team") for win in winners]
    loss_elo_change = [_update_single(0, loss, winners_elo, "players_team") for loss in losers]

    winners_info = [[winner, change[0], change[1]] for winner, change in zip(winners, win_elo_change)]
    losers_info  = [[loser, change[0], change[1]] for loser, change in zip(losers, loss_elo_change)]
    table        = winners_info + losers_info

    headers = ["Player", "Elo change", "New Elo"]
    print tabulate(table, headers=headers)


def _update_single(score, player, opponents_elo, table):
    '''update a single player given that player's score, rank, and average elo of opponents.
    returns a tuple with (elo change, new current elo)'''
    cursor = db.cursor()
    cursor.execute("SELECT name, elo, wins, losses FROM {table} WHERE name=?".format(table=table), player)
    rows = cursor.fetchall()
    player_obj = rows[0]
    player_new_elo = calc_elo_change(score, player_obj[1], opponents_elo)
    if score == 1:
        plus_wins = 1
        plus_losses = 0
    elif score == 0:
        plus_wins = 0
        plus_losses = 1
    else:
        plus_wins = 0
        plus_losses = 0

    updated = (player_new_elo, player_obj[2] + plus_wins, player_obj[3] + plus_losses, player)
    cursor.execute("UPDATE {table} SET elo=?, wins=?, losses=? WHERE name=?".format(table=table), updated)
    db.commit()

    return (player_obj[1] - player_new_elo, player_new_elo)


# TODO: rewrite to use _update_single
def ffa(winner, losers):
    '''change and store a player's ratings.  Expects winner as a single player, losers as a list.'''
    def average(x, y):
        return float((x + y) / 2)

    cursor = db.cursor()
    players = (winner, losers[0], losers[1])
    cursor.execute("SELECT name, elo, wins, losses FROM players_ffa WHERE name=? OR name=? OR name=?", players)
    rows = cursor.fetchall()
    winner_obj = rows[0]
    loser_obj  = rows[1]
    second_loser_obj = rows[2]

    winner_new_elo       = calc_elo_change(1, winner_obj[1], average(loser_obj[1], second_loser_obj[1]))
    loser_new_elo        = calc_elo_change(0, loser_obj[1], average(winner_obj[1], second_loser_obj[1]))
    second_loser_new_elo = calc_elo_change(0, second_loser_obj[1], average(winner_obj[1], loser_obj[1]))

    updated_winner       = (winner_new_elo, winner_obj[2] + 1, winner_obj[3], winner_obj[0])
    updated_loser        = (loser_new_elo, loser_obj[2], loser_obj[3] + 1, loser_obj[0])
    updated_second_loser = (second_loser_new_elo, second_loser_obj[2], second_loser_obj[3] + 1, second_loser_obj[0])

    updated = [updated_winner, updated_loser, updated_second_loser]
    cursor.executemany("UPDATE players_ffa SET elo=?, wins=?, losses=? WHERE name=?", updated)
    db.commit()

    headers = ["Player", "Elo change", "New Elo"]
    table   = [[winner, updated_winner[0] - winner_obj[1], updated_winner[0]],
               [losers[0], updated_loser[0] - loser_obj[1], updated_loser[0]],
               [losers[1], updated_second_loser[0] - second_loser_obj[1], updated_second_loser[0]]]
    print tabulate(table, headers=headers)


def print_help():
    print "Usage:"
    print "[ladder | l] [1s|ffa|2s]                   -- Print all players' ratings sorted by elo.  Default is to print a table for all modes."
    print "match | m <winner> <loser>                 -- Change and store ratings for a single 1v1 match."
    print "ffa | f <winner> <loser> <loser>           -- Change and store ratings for a single ffa match."
    print "team | t <winner> <winner> <loser> <loser> -- Change and store ratings for a single 2v2 match."
    print "add [1s|ffa|2s|all] <player name>          -- Add a player to the ladder. Name must be unique."


if __name__ == "__main__":
    args = sys.argv
    if len(args) == 1:
        ladder()
    elif len(args) == 2 and (args[1] == "1s" or args[1] == "ffa" or args[1] == "2s"):
        ladder(args[1])
    elif len(args) == 2 and (args[1] == "ladder" or args[1] == "l"):
        ladder()
    elif len(args) == 3 and (args[1] == "ladder" or args[1] == "l"):
        ladder(args[2])
    elif len(args) == 4 and (args[1] == "match" or args[1] == "m"):
        match(args[2], args[3])
    elif len(args) == 3 and args[1] == "add":
        add_player("all", args[2])
    elif len(args) == 4 and args[1] == "add":
        add_player(args[2], args[3])
    elif len(args) == 5 and (args[1] == "ffa" or args[1] == "f"):
        ffa(args[2], [args[3], args[4]])
    elif len(args) == 6 and (args[1] == "team" or args[1] == "t"):
        team(args[2], args[3], args[4], args[5])
    else:
        print_help()
    db.close()
