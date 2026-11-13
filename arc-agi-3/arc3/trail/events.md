# The first employer survey: do skills carry sideways?

36 winning routes replayed to the win (of 39 inside levels), turned into events.

For each level: the share of its winning route's distinct skills already seen, and whether its winning event was already seen, in
(a) earlier levels of the same game, (b) other games of the same department, (c) other departments.

## fine events

| employer pool | levels with a pool | skills already known | winning event already seen as a skill | winning event = an earlier winning event |
|---|---|---|---|---|
| a: earlier levels, same game | 18 | 27% | 28% | 28% |
| b: other games, same department | 36 | 0% | 0% | 0% |
| c: other departments | 36 | 0% | 0% | 0% |

## coarse events

| employer pool | levels with a pool | skills already known | winning event already seen as a skill | winning event = an earlier winning event |
|---|---|---|---|---|
| a: earlier levels, same game | 18 | 86% | 94% | 94% |
| b: other games, same department | 36 | 59% | 58% | 33% |
| c: other departments | 36 | 73% | 69% | 25% |

Most common coarse skills (in how many winning routes):

- 19x  ('move', 'other', ('changed',), True
- 19x  ('click', 'other', ('recoloured',), True
- 15x  ('click', 'other', ('changed', 'recoloured'), True
- 8x  ('move', 'other', ('moved',), False
- 8x  ('move', 'other', ('changed',), False
- 6x  ('move', 'other', ('changed', 'recoloured'), True
- 6x  ('click', 'other', ('changed',), True
- 5x  ('click', 'self', ('changed', 'recoloured'), True
- 3x  ('move', 'other', ('changed', 'moved', 'recoloured'), True
- 3x  ('A5', 'other', ('recoloured',), False

Most common winning events (coarse):

- 9x  ('move', 'other', ('changed',), True
- 6x  ('click', 'other', ('changed', 'recoloured'), True
- 5x  ('click', 'other', ('recoloured',), True
- 4x  ('move', 'other', ('changed',), False
- 2x  ('A5', 'other', ('recoloured',), False
- 2x  ('click', 'self', ('changed', 'recoloured'), True
- 2x  ('click', 'other', ('changed',), True
- 1x  ('move', 'other', ('changed', 'moved', 'recoloured'), True
