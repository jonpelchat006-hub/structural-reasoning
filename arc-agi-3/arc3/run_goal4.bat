venv\Scripts\python.exe levelrun.py exam mika3/university.py:Prof_win_image --casebook trail\frontier_casebook.json --budget 3000 --seeds 4 --mode warm --workers 12 --out trail\exam_warm_win_image.json > trail\exam_warm_win_image.log 2>&1
venv\Scripts\python.exe levelrun.py exam mika3/university.py:Prof_took_image --casebook trail\frontier_casebook.json --budget 3000 --seeds 4 --mode warm --workers 12 --out trail\exam_warm_took_image.json > trail\exam_warm_took_image.log 2>&1
venv\Scripts\python.exe levelrun.py exam mika3/university.py:Prof_two_rungs_image --casebook trail\frontier_casebook.json --budget 3000 --seeds 4 --mode warm --workers 12 --out trail\exam_warm_two_rungs_image.json > trail\exam_warm_two_rungs_image.log 2>&1
echo done > trail\GOAL4_EXAMS_DONE.txt
venv\Scripts\python.exe harness.py mika3/university.py:Prof_win_image --workers 12 --seeds 8 --out uni\win_image.json > uni\win_image.log 2>&1
venv\Scripts\python.exe harness.py mika3/university.py:Prof_took_image --workers 12 --seeds 8 --out uni\took_image.json > uni\took_image.log 2>&1
venv\Scripts\python.exe harness.py mika3/university.py:Prof_two_rungs_image --workers 12 --seeds 8 --out uni\two_rungs_image.json > uni\two_rungs_image.log 2>&1
echo done > uni\GOAL4_FACULTY_DONE.txt
