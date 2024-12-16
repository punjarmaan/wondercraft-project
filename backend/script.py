import csv

input_file = './d1.csv'
output_file = './d1_clean.csv'

with open(input_file, mode='r', newline='', encoding='utf-8') as infile, \
     open(output_file, mode='w', newline='', encoding='utf-8') as outfile:
    
    csv_reader = csv.DictReader(infile)
    fieldnames = csv_reader.fieldnames
    csv_writer = csv.DictWriter(outfile, fieldnames=fieldnames)
    
    csv_writer.writeheader()
    
    for row in csv_reader:
        if 'answer' in row:
            row['answer'] = row['answer'].strip('"')
        
        csv_writer.writerow(row)
        
