def dangerous_eval(user_input):
    #Intentional vuln: using eval on user-controlled input
    return eval(user_input)
