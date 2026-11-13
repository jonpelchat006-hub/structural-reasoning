# Notes from Jonathan, for Mika

One note per idea. Plain words are fine: I'll turn each "When" into something she can check on the screen.

How she uses them:
- **Every note starts black and white.** She only says a note to the model when its "When" actually shows up in the frames, so a note that doesn't fit a game stays quiet.
- **A note the frames back up gets her colour.** It's said once per level, with the exact places, in the model's words where she knows them.
- **Every note is tested offline on the 25 public games before it goes into a Kaggle version.**
- **Keep them general.** The hidden games are different games.

```
## short name
When: what she has to see on the screen first
Say: what she tells the model
Why (optional): where the idea comes from
```

---

## Something to solve before the end
When: the body reaches the place that looks like the end (a box or door, often holding a glyph) and the level does not end
Say: There is at least one objective to solve before moving to the end. The end is usually locked until it is done: look for what the end is showing (a picture, a colour, a count) and what on the board can change to match it, then come back.
Why: on ls20 in v9 the model matched the picture, walked to the end, didn't win, and nearly threw away the right idea.

## One button per direction
When: the first time a direction press does not move the body exactly one step its way
Say: Each direction button normally moves the body one step. This press didn't, so something on the board did it (a wall, a push, a jump, swapped controls), and it will do it again.
Why: the body has one button per direction; anything else is a mechanic.

## Moving things follow their own pattern
When: something moves that the press did not move
Say: That moved by itself. Moving objects follow their own pattern (a loop, a back-and-forth, or chasing you): watch it for a few presses before planning around it.
Then (colour): once she has seen the whole loop, the track note gives the exact loop and where it will be after the next press.

## Alike only when two properties match
When: two or more things share at least two properties (exact shape and exact colours, or shape and the same behaviour when touched)
Say: These share shape and colour, so they are probably related: test one and expect the others to act the same.
Not said: things that share only one property (same size, or same shape in a different colour) look the same but are not related.
Why: things can look the same but are only related if they share more than one property. On ls20 the three 3x3 tiles look alike and do three different things (turn, reshape, recolour); they share size but not exact shape or colours.

## A death is an unplanned reset; lives are pips
When: the board goes back to the level's start without RESET being pressed
Say: That was a death (an unplanned reset). Lives are marked by small pips: the one at rows ..., cols ... just emptied, N left. Say what ended the life if it is known (the bar ran out, or touching something).
Why: a death is when there is an unplanned reset. Lives are marked by small pips, and on a death one empties.

---

## Suggested by Claude, kept by Jonathan (Oct 29)

## The bar is a budget
When: a long bar at the edge shrinks by the same amount each press, and a death happens when it runs out
Say: That bar counts your presses; when it is empty you lose a life. Plan routes that fit inside what is left.

## A small far picture is a display
When: a small picture away from the body changes when something is touched
Say: That picture shows state (like a key or a counter). What you touched changes it, so it can be set on purpose.

---

(more notes below)

