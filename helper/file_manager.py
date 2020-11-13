def apply_rsi_values(file_name, rsi_values):
    file = open(file_name, "a")
    file.write(rsi_values)
    file.close()


def read_rsi_values(file_name):
    file = open(file_name, "r")
    print(file.read())
    file.close()


def create_file(filename, header='', temp=False):
    if filename == '':
        print("Enter a file name first!")
    else:
        base_path = 'temp_files/' if temp else ''
        file_path = '{}{}'.format(base_path, filename)

        file = open(file_path, 'w')
        if header != '':
            file.write('{}\n'.format(header))
        file.close()


def append_to_file(filename, data, temp=False):
    if filename == '':
        print("Enter a file name first!")
    else:
        base_path = 'temp_files/' if temp else ''
        file_path = '{}{}'.format(base_path, filename)

        with open(file_path, 'a') as file:
            file.write('{}\n'.format(data))


def write_to_file(filename, data, temp=False):
    if filename == '':
        print("Enter a file name first!")
    else:
        base_path = 'temp_files/' if temp else ''
        file_path = '{}{}'.format(base_path, filename)

        with open(file_path, 'w') as file:
            file.write('{}\n'.format(data))


def delete_file(filename, temp=False):
    import os

    base_path = 'temp_files/' if temp else 'files/ohlc/'
    file_path = '{}{}'.format(base_path, filename)

    if os.path.exists(file_path):
        os.remove(file_path)
    else:
        print('File does not exist!')