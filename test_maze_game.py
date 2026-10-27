import unittest

from maze_game import EAST, NORTH, SOUTH, WEST, astar_path, generate_maze, shortest_path


class MazeAlgorithmsTests(unittest.TestCase):
    def test_generation_is_reproducible_and_perfect(self):
        first = generate_maze(9, 13, seed=123)
        second = generate_maze(9, 13, seed=123)
        self.assertEqual(first.walls, second.walls)

        open_edges = 0
        for row in range(first.rows):
            for col in range(first.cols):
                walls = first.walls[row][col]
                if col + 1 < first.cols and not walls & EAST:
                    self.assertFalse(first.walls[row][col + 1] & WEST)
                    open_edges += 1
                if row + 1 < first.rows and not walls & SOUTH:
                    self.assertFalse(first.walls[row + 1][col] & NORTH)
                    open_edges += 1
        self.assertEqual(open_edges, first.rows * first.cols - 1)

    def test_bfs_and_astar_return_shortest_valid_routes(self):
        maze = generate_maze(15, 21, seed=42)
        bfs = shortest_path(maze, (0, 0), (14, 20))
        astar = astar_path(maze, (0, 0), (14, 20))
        self.assertEqual(bfs[0], (0, 0))
        self.assertEqual(bfs[-1], (14, 20))
        self.assertEqual(len(astar), len(bfs))

        for path in (bfs, astar):
            for (row, col), (next_row, next_col) in zip(path, path[1:]):
                distance = abs(row - next_row) + abs(col - next_col)
                self.assertEqual(distance, 1)
                if next_row < row:
                    self.assertFalse(maze.walls[row][col] & NORTH)
                elif next_row > row:
                    self.assertFalse(maze.walls[row][col] & SOUTH)
                elif next_col < col:
                    self.assertFalse(maze.walls[row][col] & WEST)
                else:
                    self.assertFalse(maze.walls[row][col] & EAST)

    def test_start_equal_to_goal_is_a_single_cell_path(self):
        maze = generate_maze(2, 2, seed=1)
        self.assertEqual(astar_path(maze, (1, 1), (1, 1)), [(1, 1)])
        self.assertEqual(shortest_path(maze, (1, 1), (1, 1)), [(1, 1)])

    def test_invalid_dimensions_and_positions_are_rejected(self):
        with self.assertRaises(ValueError):
            generate_maze(0, 5)
        maze = generate_maze(2, 2, seed=1)
        with self.assertRaises(ValueError):
            astar_path(maze, (-1, 0), (1, 1))
        with self.assertRaises(ValueError):
            shortest_path(maze, (0, 0), (2, 1))


if __name__ == "__main__":
    unittest.main()
