from example3 import x

def user_func1():
    user_func2()

def user_func2():
    x()

def unrelated_func():
    user_func2()
    print("This is a built-in function")