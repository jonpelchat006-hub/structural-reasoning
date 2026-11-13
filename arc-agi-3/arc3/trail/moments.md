# The image plane: do moments carry between games under limited turns?

36 winning routes replayed (18 games); arbitrary presses: up to 150 random presses from each level start, counting only those that changed something. A moment is the before/after crop of a press's main change.

**Library** = the moments of the winning routes of the *other* games (a game never sees its own). **Match** = a press whose moment is in the library. **Route-like** = a moment seen more often (relative) on the other games' routes than on their arbitrary presses, by at least 2x.

## match

| grain | turns | route presses | arbitrary presses | lift (pooled) | lift (games equal) | games where route presses match more | winning press (first frame) |
|---|---|---|---|---|---|---|---|
| context | none | 1% | 3.7% | **0.4x** | 0.9x | 1 of 18 | 0% |
| context | colours | 1% | 3.7% | **0.4x** | 0.9x | 1 of 18 | 0% |
| context | colours+flips | 1% | 3.7% | **0.4x** | 0.9x | 1 of 18 | 0% |
| change | none | 1% | 0.4% | **2.6x** | 2.1x | 2 of 18 | 0% |
| change | colours | 6% | 6.8% | **0.9x** | 0.9x | 3 of 18 | 6% |
| change | colours+flips | 6% | 6.8% | **0.9x** | 0.9x | 3 of 18 | 6% |
| shape | none | 35% | 31.4% | **1.1x** | 1.3x | 4 of 18 | 6% |
| shape | colours | 35% | 31.4% | **1.1x** | 1.3x | 4 of 18 | 6% |
| shape | colours+flips | 35% | 31.4% | **1.1x** | 1.3x | 4 of 18 | 6% |

## route-like

| grain | turns | route presses | arbitrary presses | lift (pooled) | lift (games equal) | games where route presses match more | winning press (first frame) |
|---|---|---|---|---|---|---|---|
| context | none | 1% | 0.3% | **1.7x** | 1.9x | 2 of 18 | 0% |
| context | colours | 1% | 0.3% | **1.7x** | 1.9x | 2 of 18 | 0% |
| context | colours+flips | 1% | 0.3% | **1.7x** | 1.9x | 2 of 18 | 0% |
| change | none | 1% | 0.2% | **5.2x** | 4.8x | 2 of 18 | 0% |
| change | colours | 2% | 3.3% | **0.5x** | 1.2x | 3 of 18 | 0% |
| change | colours+flips | 2% | 3.3% | **0.5x** | 1.2x | 3 of 18 | 0% |
| shape | none | 14% | 14.4% | **0.9x** | 1.9x | 3 of 18 | 0% |
| shape | colours | 14% | 14.4% | **0.9x** | 1.9x | 3 of 18 | 0% |
| shape | colours+flips | 14% | 14.4% | **0.9x** | 1.9x | 3 of 18 | 0% |

## Within a game: the library is this game's earlier levels

| grain | turns | route presses | arbitrary presses | lift | levels |
|---|---|---|---|---|---|
| context | none | 33% | 31.8% | 1.0x | 18 |
| context | colours | 49% | 42.1% | 1.2x | 18 |
| context | colours+flips | 60% | 57.3% | 1.0x | 18 |
| change | none | 43% | 49.9% | 0.9x | 18 |
| change | colours | 69% | 70.5% | 1.0x | 18 |
| change | colours+flips | 71% | 72.0% | 1.0x | 18 |
| shape | none | 71% | 72.2% | 1.0x | 18 |
| shape | colours | 71% | 72.2% | 1.0x | 18 |
| shape | colours+flips | 71% | 72.2% | 1.0x | 18 |

## Winning moments: the library is the winning presses of other games

| grain | turns | winning press | other route presses | arbitrary presses | lift: win vs arbitrary | lift: route vs arbitrary | levels |
|---|---|---|---|---|---|---|---|
| context | none | 0% | 0.0% | 0.0% | - | - | 33 |
| context | colours | 0% | 0.0% | 0.0% | - | - | 33 |
| context | colours+flips | 0% | 0.0% | 0.0% | - | - | 33 |
| change | none | 0% | 0.0% | 0.0% | - | - | 33 |
| change | colours | 0% | 0.5% | 2.5% | 0.0x | 0.2x | 33 |
| change | colours+flips | 0% | 0.5% | 2.5% | 0.0x | 0.2x | 33 |
| shape | none | 0% | 0.5% | 2.5% | 0.0x | 0.2x | 33 |
| shape | colours | 0% | 0.5% | 2.5% | 0.0x | 0.2x | 33 |
| shape | colours+flips | 0% | 0.5% | 2.5% | 0.0x | 0.2x | 33 |

## Winning moments: the library is the winning presses of earlier levels of the same game

| grain | turns | winning press | other route presses | arbitrary presses | lift: win vs arbitrary | lift: route vs arbitrary | levels |
|---|---|---|---|---|---|---|---|
| context | none | 6% | 3.8% | 2.0% | 2.9x | 1.9x | 17 |
| context | colours | 24% | 18.6% | 5.1% | 4.6x | 3.6x | 17 |
| context | colours+flips | 47% | 18.6% | 5.1% | 9.2x | 3.6x | 17 |
| change | none | 12% | 3.8% | 2.0% | 5.8x | 1.9x | 17 |
| change | colours | 29% | 24.8% | 7.0% | 4.2x | 3.5x | 17 |
| change | colours+flips | 65% | 27.2% | 8.6% | 7.5x | 3.2x | 17 |
| shape | none | 29% | 26.1% | 12.2% | 2.4x | 2.1x | 17 |
| shape | colours | 29% | 26.1% | 12.2% | 2.4x | 2.1x | 17 |
| shape | colours+flips | 65% | 34.0% | 17.7% | 3.6x | 1.9x | 17 |
