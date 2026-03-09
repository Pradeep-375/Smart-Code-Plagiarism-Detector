def factorial(n):
    result = 1
    for i in range(1,n+1):
        result = result * i
    return result

def square(x):
    return x*x

a = factorial(5)
b = square(4)

print("Factorial:",a)
print("Square:",b)