:wait
if not exist uni\GOAL2_FACULTY_DONE.txt (ping -n 21 127.0.0.1 > nul & goto wait)
venv\Scripts\python.exe levelrun.py exam mika3/university.py:Prof_far_rare --casebook trail\frontier_casebook.json --budget 3000 --seeds 4 --mode cold --workers 12 --out trail\exam_cold_far_rare.json > trail\exam_cold_far_rare.log 2>&1
venv\Scripts\python.exe levelrun.py exam mika3/university.py:Prof_three_rungs --casebook trail\frontier_casebook.json --budget 3000 --seeds 4 --mode cold --workers 12 --out trail\exam_cold_three_rungs.json > trail\exam_cold_three_rungs.log 2>&1
venv\Scripts\python.exe levelrun.py exam mika3/university.py:Prof_far_rare --casebook trail\frontier_casebook.json --budget 3000 --seeds 4 --mode warm --workers 12 --out trail\exam_warm_far_rare.json > trail\exam_warm_far_rare.log 2>&1
venv\Scripts\python.exe levelrun.py exam mika3/university.py:Prof_three_rungs --casebook trail\frontier_casebook.json --budget 3000 --seeds 4 --mode warm --workers 12 --out trail\exam_warm_three_rungs.json > trail\exam_warm_three_rungs.log 2>&1
echo done > trail\GOAL3_EXAMS_DONE.txt
venv\Scripts\python.exe harness.py mika3/university.py:Prof_far_rare --workers 12 --seeds 8 --out uni\far_rare.json > uni\far_rare.log 2>&1
venv\Scripts\python.exe harness.py mika3/university.py:Prof_three_rungs --workers 12 --seeds 8 --out uni\three_rungs.json > uni\three_rungs.log 2>&1
echo done > uni\GOAL3_FACULTY_DONE.txt
