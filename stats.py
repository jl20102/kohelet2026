import numpy as np
import math
import matplotlib.pyplot as plt

#checks in with the user once and continues to ask until they give a valid number.
#appends the valid number to the existing anxietyList and returns it.
"""def check_in_once(anxietyList = []):
    #continuously prompts the user for input until a valid number is entered
    while(True):
        try:
            user_input = input("On a scale from 1 to 10, how well are you doing anxiety-wise: -->")
            user_input = int(user_input)
            if 1 <= user_input <= 10:
                anxietyList.append(user_input)
                return user_input
            else:  
                print("This number is not from 1 to 10. Please enter a number between 1 and 10.")
        except ValueError:
            print("This is not a valid number.")
"""
#calculates the next anxiety check time by taking the anxity list and accounting for high levels, high changes, and slow scroll speed.
def calculate_next_anxiety_check(anxietyList, averageScrollSpeed):
    """ average scroll speed is compared to average"""
    if len(anxietyList) < 4:
        return 500 # default to 5 minutes if we don't have enough data
    
    anxietyList = np.array(anxietyList)
    averageAnxiety = np.mean(anxietyList)
    anxietySTD = np.std(anxietyList)

    return 200 - 10*(-averageAnxiety - 2 * anxietySTD - math.fabs(20 - averageScrollSpeed)/5)

def warn_high_anxiety(anxietyList):
    if anxietyList[-1] >= 8:
        return True

def warn_high_change(anxietyList, timeBetween = 2, threshold = 1.5):
    if len(anxietyList) < 2:
        return False
    return math.fabs(anxietyList[-1] - anxietyList[-2])/timeBetween >= threshold

def warn_slow_scroll_speed(averageScrollSpeed, threshold = 20):
    if averageScrollSpeed <= threshold:
        return True
    
def plot_anxiety_over_time(anxietyList, checkInIntervals):
    plt.plot(np.cumsum(checkInIntervals),anxietyList)
    plt.xlabel('Time')
    plt.ylabel('Anxiety Level')
    plt.title('Anxiety Levels Over Time')
    plt.show()

def moving_average(X, size):
  # We create a window of weights: [1/size, 1/size, ..., 1/size]
  return np.convolve(X, np.ones(size)/size, mode='valid')