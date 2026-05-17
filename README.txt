🎲 BOGGLE SOLVER — HOW TO USE
================================

QUICK START
-----------
1. Double-click "run_boggle.command"  (easiest!)
   — OR —
   Open Terminal, drag this folder in, then type:
       python3 boggle_solver.py

FROM AN IMAGE
-------------
   python3 boggle_solver.py your_photo.jpg

   The program will try to read the letters automatically.
   If any cell shows "?" it could not read it — you can
   correct it when prompted.

TYPING LETTERS MANUALLY
------------------------
   Choose option [2] in the menu.
   Enter each row of letters when asked.
   Example for a 4×4 board:
       Row 1:  A B C D
       Row 2:  E F G H
       Row 3:  I J K L
       Row 4:  M N O P

TIPS FOR BETTER IMAGE READING
-------------------------------
   • Take the photo straight-on (not at an angle)
   • Good lighting — avoid glare
   • Crop the image so only the letter grid is visible
   • Supports .jpg  .png  .bmp  .gif

OUTPUT
------
   • Answers are printed in the terminal
   • Also saved to "answers.txt" in this folder
   • Words are grouped by length and scored per official Boggle rules:
       3-4 letters = 1 pt
       5 letters   = 2 pts
       6 letters   = 3 pts
       7 letters   = 5 pts
       8+ letters  = 11 pts

BOGGLE RULES USED
-----------------
   • Words must be 3+ letters
   • Letters must be adjacent (horizontally, vertically, diagonally)
   • Cannot reuse the same tile twice in one word
   • Q counts as "QU" automatically
