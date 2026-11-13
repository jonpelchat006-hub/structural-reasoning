def solve(send, grid):
    # Define the number of rows and columns in the grid
    rows = len(grid)
    cols = len(grid[0])
    
    # Define the directions for the 8 neighbors (up, down, left, right, and diagonals)
    directions = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
    
    # Function to apply an ACTION6 operation at position (x, y)
    def action6(x, y):
        nonlocal grid
        if x < 0 or x >= rows or y < 0 or y >= cols:
            return
        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            if 0 <= nx < rows and 0 <= ny < cols:
                grid[nx][ny] = (grid[nx][ny] + 1) % 8
    
    # Apply each action to the grid
    for action in send:
        x, y = action
        action6(x, y)
    
    return grid

# Example usage:
initial_grid = [
    [0]*64 for _ in range(7)
]
actions = [(38, 29), (50, 46), (61, 25), (61, 33), (31, 0), (28, 29), (51, 29)]
final_grid = solve(actions, initial_grid)
print(final_grid)