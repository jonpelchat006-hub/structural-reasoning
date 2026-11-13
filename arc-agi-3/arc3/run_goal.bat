venv\Scripts\python.exe levelrun.py exam mika3/university.py:Prof_took_control --casebook trail\frontier_casebook.json --budget 3000 --seeds 4 --mode cold --workers 12 --out trail\exam_cold_took_control.json > trail\exam_cold_took_control.log 2>&1
venv\Scripts\python.exe levelrun.py exam mika3/university.py:Prof_took_light --casebook trail\frontier_casebook.json --budget 3000 --seeds 4 --mode cold --workers 12 --out trail\exam_cold_took_light.json > trail\exam_cold_took_light.log 2>&1
venv\Scripts\python.exe levelrun.py exam mika3/university.py:Prof_two_rungs --casebook trail\frontier_casebook.json --budget 3000 --seeds 4 --mode cold --workers 12 --out trail\exam_cold_two_rungs.json > trail\exam_cold_two_rungs.log 2>&1
venv\Scripts\python.exe levelrun.py exam mika3/university.py:Prof_took_control --casebook trail\frontier_casebook.json --budget 3000 --seeds 4 --mode warm --workers 12 --out trail\exam_warm_took_control.json > trail\exam_warm_took_control.log 2>&1
venv\Scripts\python.exe levelrun.py exam mika3/university.py:Prof_took_light --casebook trail\frontier_casebook.json --budget 3000 --seeds 4 --mode warm --workers 12 --out trail\exam_warm_took_light.json > trail\exam_warm_took_light.log 2>&1
venv\Scripts\python.exe levelrun.py exam mika3/university.py:Prof_win_event --casebook trail\frontier_casebook.json --budget 3000 --seeds 4 --mode warm --workers 12 --out trail\exam_warm_win_event.json > trail\exam_warm_win_event.log 2>&1
venv\Scripts\python.exe levelrun.py exam mika3/university.py:Prof_two_rungs --casebook trail\frontier_casebook.json --budget 3000 --seeds 4 --mode warm --workers 12 --out trail\exam_warm_two_rungs.json > trail\exam_warm_two_rungs.log 2>&1
echo done > trail\GOAL_EXAMS_DONE.txt
venv\Scripts\python.exe harness.py mika3/university.py:Prof_took_control --workers 12 --seeds 8 --out uni\took_control.json > uni\took_control.log 2>&1
venv\Scripts\python.exe harness.py mika3/university.py:Prof_took_light --workers 12 --seeds 8 --out uni\took_light.json > uni\took_light.log 2>&1
venv\Scripts\python.exe harness.py mika3/university.py:Prof_win_event --workers 12 --seeds 8 --out uni\win_event.json > uni\win_event.log 2>&1
venv\Scripts\python.exe harness.py mika3/university.py:Prof_two_rungs --workers 12 --seeds 8 --out uni\two_rungs.json > uni\two_rungs.log 2>&1
echo done > uni\GOAL_FACULTY_DONE.txt
