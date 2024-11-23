from example1 import user_func1

def a():
    b()

def b():
    user_func1()
    c()

def c():
    print("Hello, World!")