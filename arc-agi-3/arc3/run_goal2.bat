venv\Scripts\python.exe levelrun.py exam mika3/university.py:Prof_pick_only --casebook trail\frontier_casebook.json --budget 3000 --seeds 4 --mode cold --workers 12 --out trail\exam_cold_pick_only.json > trail\exam_cold_pick_only.log 2>&1
venv\Scripts\python.exe levelrun.py exam mika3/university.py:Prof_far_change --casebook trail\frontier_casebook.json --budget 3000 --seeds 4 --mode cold --workers 12 --out trail\exam_cold_far_change.json > trail\exam_cold_far_change.log 2>&1
venv\Scripts\python.exe levelrun.py exam mika3/university.py:Prof_pick_only --casebook trail\frontier_casebook.json --budget 3000 --seeds 4 --mode warm --workers 12 --out trail\exam_warm_pick_only.json > trail\exam_warm_pick_only.log 2>&1
venv\Scripts\python.exe levelrun.py exam mika3/university.py:Prof_far_change --casebook trail\frontier_casebook.json --budget 3000 --seeds 4 --mode warm --workers 12 --out trail\exam_warm_far_change.json > trail\exam_warm_far_change.log 2>&1
venv\Scripts\python.exe levelrun.py exam mika3/university.py:Prof_far_change_win --casebook trail\frontier_casebook.json --budget 3000 --seeds 4 --mode warm --workers 12 --out trail\exam_warm_far_change_win.json > trail\exam_warm_far_change_win.log 2>&1
echo done > trail\GOAL2_EXAMS_DONE.txt
venv\Scripts\python.exe harness.py mika3/university.py:Prof_pick_only --workers 12 --seeds 8 --out uni\pick_only.json > uni\pick_only.log 2>&1
venv\Scripts\python.exe harness.py mika3/university.py:Prof_far_change --workers 12 --seeds 8 --out uni\far_change.json > uni\far_change.log 2>&1
venv\Scripts\python.exe harness.py mika3/university.py:Prof_far_change_win --workers 12 --seeds 8 --out uni\far_change_win.json > uni\far_change_win.log 2>&1
echo done > uni\GOAL2_FACULTY_DONE.txt
