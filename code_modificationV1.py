import os
import numpy as np

datPath = './data/'
outPath = './outputs/'

def main():
    for root, ds, fs in os.walk(datPath):
        for file in fs:
            filename = os.path.join(root, file)
            Oversampling01(filename)
            Oversampling02(filename)
    return

# add if (1).
def Oversampling01(filename):
    def FindInsertPoints(marks_para):
        if 1 == max(marks_para):
            listones = np.where(marks_para == 1)[0]
            #print(listones)
            pStart = listones[0] + 1
            pEnd = listones[-1] + 1
        else:
            listtwos = np.where(marks_para == 2)[0]
            #print(listtwos)
            pStart = listtwos[0] - 1
            pEnd = listtwos[-1] + 2
        return pStart, pEnd

    def InsertIfOne(ind_func):
        pStart, pEnd = FindInsertPoints(marks_func[ind_func])
        #print(pStart)
        #print(pEnd)
        for i in range(pStart, pEnd):
            lines[i] = '\t' + lines[i]
        lines.insert(pEnd, '\t}\n')
        lines.insert(pStart, '\t{\n')
        lines.insert(pStart, '\tif (1)\n')
        return

    # read file from the filename.
    fp = open(filename, encoding='utf-8', errors='ignore')
    lines = fp.readlines()
    numLines = len(lines)

    # find all pure comments.
    marks_comments = np.zeros(numLines, dtype = int)
    for i in range(numLines): # find multi-line comments.
        line = lines[i]
        cnt = line.count('/*') - line.count('*/')
        if (i):
            marks_comments[i] = marks_comments[i-1] + cnt
        else:
            marks_comments[i] = cnt
    for i in range(numLines-1, 0, -1):
        if (0 == marks_comments[i]) & (1 == marks_comments[i-1]):
            marks_comments[i] = 1
    for i in range(numLines): # find single-line comments.
        line = lines[i].replace(' ', '')
        if (line[:2] == '/*') & (line[-3:-1] == '*/'):
            marks_comments[i] = 1
        #print(i + 1, marks_comments[i], lines[i], end='')

    # find all indentation.
    marks = np.zeros(numLines, dtype = int)
    for i in range(numLines):
        if (marks_comments[i] == 0): # not pure comment.
            line = lines[i]
            if line.count('/*'): # embed comment.
                line = line.split('/*', 1)[0]
            cnt = line.count('{') - line.count('}')
        else: # pure comment.
            cnt = 0
        if (i):
            marks[i] = marks[i-1] + cnt
        else:
            marks[i] = cnt
    #for i in range(numLines-1, 0, -1):
    #    if (marks[i] == marks[i-1] - 1):
    #        marks[i] = marks[i-1]
    for i in range(numLines):
        print(i, marks_comments[i], marks[i], lines[i], end='')

    # divide into functions.
    numFunc = 0
    for i in range(1, numLines):
        if (0 == marks[i]) & (1 == marks[i-1]):
            numFunc += 1
    #print(numFunc)
    marks_func = np.zeros((numFunc, numLines), dtype=int)
    ind_func = 0
    for i in range(numLines):
        marks_func[ind_func][i] = marks[i]
        if (i > 0) & (0 == marks[i]) & (1 == marks[i-1]) & (ind_func < numFunc-1):
            #print(i)
            ind_func += 1
    #print(marks_func)

    # change the code
    for i in range(numFunc, 0, -1):
        #print(i)
        InsertIfOne(i-1)
    # show changed code
    #for i in range(len(lines)):
    #    print(i, lines[i], end='')

    fname = filename.split('/')
    ind = fname[-1].find('.')
    if ind > 0:
        fname[-1] = fname[-1][:ind] + '_01' + fname[-1][ind:]
    else:
        fname[-1] = fname[-1] + '_01'
    foutput = outPath + fname[-1]
    print(foutput)

    fp = open(foutput, 'w')
    for i in range(len(lines)):
        fp.write(lines[i])
    fp.close()

    return

# add if (0)
def Oversampling02(filename):
    def FindInsertPoints(marks_para):
        if 1 == max(marks_para):
            listones = np.where(marks_para == 1)[0]
            #print(listones)
            pStart = listones[0] + 1
            pEnd = listones[-1] + 1
        else:
            listtwos = np.where(marks_para == 2)[0]
            #print(listtwos)
            pStart = listtwos[0] - 1
            pEnd = listtwos[-1] + 2
        return pStart, pEnd

    def InsertIfOne(ind_func):
        pStart, pEnd = FindInsertPoints(marks_func[ind_func])
        #print(pStart)
        #print(pEnd)
        for i in range(pStart, pEnd):
            lines[i] = '\t' + lines[i]
        lines.insert(pEnd, '\t}\n')
        lines.insert(pStart, '\t{\n')
        lines.insert(pStart, '\telse\n')
        lines.insert(pStart, '\t}\n')
        lines.insert(pStart, '\t\tprintf(\'No used!\')\n')
        lines.insert(pStart, '\t{\n')
        lines.insert(pStart, '\tif (0)\n')
        return

    # read file from the filename.
    fp = open(filename, encoding='utf-8', errors='ignore')
    lines = fp.readlines()
    numLines = len(lines)

    # find all pure comments.
    marks_comments = np.zeros(numLines, dtype = int)
    for i in range(numLines): # find multi-line comments.
        line = lines[i]
        cnt = line.count('/*') - line.count('*/')
        if (i):
            marks_comments[i] = marks_comments[i-1] + cnt
        else:
            marks_comments[i] = cnt
    for i in range(numLines-1, 0, -1):
        if (0 == marks_comments[i]) & (1 == marks_comments[i-1]):
            marks_comments[i] = 1
    for i in range(numLines): # find single-line comments.
        line = lines[i].replace(' ', '')
        if (line[:2] == '/*') & (line[-3:-1] == '*/'):
            marks_comments[i] = 1
        #print(i + 1, marks_comments[i], lines[i], end='')

    # find all indentation.
    marks = np.zeros(numLines, dtype = int)
    for i in range(numLines):
        if (marks_comments[i] == 0): # not pure comment.
            line = lines[i]
            if line.count('/*'): # embed comment.
                line = line.split('/*', 1)[0]
            cnt = line.count('{') - line.count('}')
        else: # pure comment.
            cnt = 0
        if (i):
            marks[i] = marks[i-1] + cnt
        else:
            marks[i] = cnt
    #for i in range(numLines-1, 0, -1):
    #    if (marks[i] == marks[i-1] - 1):
    #        marks[i] = marks[i-1]
    for i in range(numLines):
        print(i, marks_comments[i], marks[i], lines[i], end='')

    # divide into functions.
    numFunc = 0
    for i in range(1, numLines):
        if (0 == marks[i]) & (1 == marks[i-1]):
            numFunc += 1
    #print(numFunc)
    marks_func = np.zeros((numFunc, numLines), dtype=int)
    ind_func = 0
    for i in range(numLines):
        marks_func[ind_func][i] = marks[i]
        if (i > 0) & (0 == marks[i]) & (1 == marks[i-1]) & (ind_func < numFunc-1):
            #print(i)
            ind_func += 1
    #print(marks_func)

    # change the code
    for i in range(numFunc, 0, -1):
        #print(i)
        InsertIfOne(i-1)
    # show changed code
    #for i in range(len(lines)):
    #    print(i, lines[i], end='')

    fname = filename.split('/')
    ind = fname[-1].find('.')
    if ind > 0:
        fname[-1] = fname[-1][:ind] + '_02' + fname[-1][ind:]
    else:
        fname[-1] = fname[-1] + '_02'
    foutput = outPath + fname[-1]
    print(foutput)

    fp = open(foutput, 'w')
    for i in range(len(lines)):
        fp.write(lines[i])
    fp.close()

    return

# add variable.
def Oversampling03(filename):

    return

if __name__ == '__main__':
    main()