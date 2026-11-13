:wait
if not exist uni\GOAL4_FACULTY_DONE.txt (ping -n 21 127.0.0.1 > nul & goto wait)
venv\Scripts\python.exe levelrun.py exam mika3/university.py:Prof_goal_search --casebook trail\frontier_casebook.json --budget 3000 --seeds 4 --mode warm --workers 12 --out trail\exam_warm_goal_search.json > trail\exam_warm_goal_search.log 2>&1
venv\Scripts\python.exe levelrun.py exam mika3/university.py:Prof_two_rungs_search --casebook trail\frontier_casebook.json --budget 3000 --seeds 4 --mode warm --workers 12 --out trail\exam_warm_two_rungs_search.json > trail\exam_warm_two_rungs_search.log 2>&1
echo done > trail\GOAL5_EXAMS_DONE.txt
venv\Scripts\python.exe harness.py mika3/university.py:Prof_goal_search --workers 12 --seeds 8 --out uni\goal_search.json > uni\goal_search.log 2>&1
venv\Scripts\python.exe harness.py mika3/university.py:Prof_two_rungs_search --workers 12 --seeds 8 --out uni\two_rungs_search.json > uni\two_rungs_search.log 2>&1
echo done > uni\GOAL5_FACULTY_DONE.txt
