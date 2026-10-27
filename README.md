# Maze Runner

Run the single-player game:

```powershell
python -m pip install -r requirements.txt
python "maze game.py"
```

Move with **W/A/S/D** or the arrow keys. Press **H** to show or hide the BFS
shortest path, and **R** to start a new maze. Reaching the exit plays a short
victory celebration, then automatically generates the next level. Use the
**Sound** button to toggle movement and victory effects. There is no background
music.

The maze is generated using randomized depth-first search, and shortest paths
are found using breadth-first search.
