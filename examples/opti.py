def naive_matrix_multiply(A, B):
    n = len(A)
    result = [[0] * n for _ in range(n)]
    
    for i in range(n):  # Row of A
        for j in range(n):  # Column of B
            for k in range(n):  # Element of row A and column B
                result[i][j] += A[i][k] * B[k][j]
    return result


def fibonacci_recursive(n):
    if n <= 1:
        return n
    return fibonacci_recursive(n - 1) + fibonacci_recursive(n - 2)