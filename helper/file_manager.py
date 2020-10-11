
def apply_rsi_values(file_name, rsi_values):
    file = open(file_name, "a")
    file.write(rsi_values)
    file.close()

def read_rsi_values(file_name):
    file = open(file_name, "r")
    print(file.read())
    file.close()
