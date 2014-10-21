def calc_elo_change(score, rank, opponent_rank, k=32):
    '''Gives an elo change for a scoring period (game, torunament, etc.).
    score is expected to be 1 for a win, 0 for a loss, and 0.5 for a draw.'''
    expected_score = 1 / (1 + pow(10, (opponent_rank - rank) / 400))
    new_rank = rank + k * (score - expected_score)
    return new_rank

def calc_win_probability(rank, opponent_rank):
    '''Gives the probability that player with rank will beat player with opponent_rank.'''
    expected_score = 1 / (1 + pow(10, (opponent_rank - rank) / 400))
    return expected_score
