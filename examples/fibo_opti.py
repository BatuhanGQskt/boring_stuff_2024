from opti import naive_matrix_multiply, fibonacci_recursive

def inefficient_code():
    # Inefficient use of Fibonacci function
    fib_number = fibonacci_recursive(10)  # Compute a small Fibonacci number (inefficient due to recursion)
    
    # Inefficient matrix multiplication example
    # Creating two matrices with Fibonacci numbers
    A = [[fibonacci_recursive(i + 1) for i in range(3)] for _ in range(3)]
    B = [[fibonacci_recursive(i + 2) for i in range(3)] for _ in range(3)]
    
    # Perform naive matrix multiplication
    result = naive_matrix_multiply(A, B)
    
    return result

def print_greetings():
    print("Hello world")

# Execute the inefficient code
if __name__ == "__main__":
    result = inefficient_code()
    print("Resulting Matrix:")
    for row in result:
        print(row)