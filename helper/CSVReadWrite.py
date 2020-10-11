from datetime import datetime
import csv

class CSVReadWrite:

    def __init__(self, filename, header=''):
       self.filename = filename
       self.header = header


    def read_file(self):
        with open(self.filename, mode='r') as csv_file :
            file_reader = csv_file.readlines()

            for line in file_reader:
                print(line)


    def write_file(self, data, *args):
        with open(self.filename, mode='w') as csv_file:

            csv_file.write(self.header + "\n")

            for row in data:
                line = ""
                for arg in args:
                    if arg == args[0]:
                        line = str(row[arg])
                    else:
                        line = line + ","  +  str(row[arg])

                csv_file.write(line + "\n")








#                csv_file.write("{0},{1},{2},{3},{4},{5}\n".format(datetime.fromtimestamp(row[columns[0]]).strftime("%Y/%m/%d"), row[columns[1]],
#                                     row[columns[2]], row[columns[3]],
#                                                             row[columns[4]],
#                                                             row[columns[5]]))
