import os
import re
import random

rootPath = './'
appPath = rootPath + '/openssl/'
datPath = appPath + '/file_jk/'
patPath = appPath + '/patch_jk/'
astPath = appPath + '/ast_jk/'
outPath = appPath + '/out_jk/'
version = 'after' # 'after' or 'before'

_DEBUG_ = 0 # 1: only use one sample, 0: use all samples.

def main():
    global _DEBUG_
    # Generate AST files from program files.
    #GenerateASTs(datPath, astPath)
    # get patch lists from patch path.
    patchList = ScanPatches(patPath, datPath)
    # scan all the files.
    for root, ds, fs in os.walk(os.path.join(datPath, version)):
        for file in fs:
            # if _DEBUG_ == 1, run single C/Cpp file; if _DEBUG_ == 0, run all files.
            if _DEBUG_ <= 96:    # can change to N.
                extname = os.path.splitext(file)[1]         # get the file extension.
                if '.c' == extname or '.cpp' == extname:    # if file extension is .c or .cpp.
                    if _DEBUG_ >= 1: _DEBUG_ += 1           # _DEBUG_ = 2
                    # ===================================================================
                    # get the corresponding program file name.
                    filename = os.path.join(root, file)    # get the program file name.
                    filename = filename.replace('\\', '/')
                    print(filename)
                    # get the corresponding ast file name.
                    astname = filename.replace(datPath, astPath, 1) + '.txt'
                    if _DEBUG_: print('[DEBUG] ', astname)
                    # find all IF statements in the ast file.
                    ifstmts = FindIfStmts(astname)
                    for item in ifstmts:
                        # find the changed IF statements in diff file.
                        patchname = CheckIfChanged(filename, item, patchList, version)
                        if (len(patchname)):
                            if _DEBUG_: print('[DEBUG] ', filename, item, patchname)
                            contents = Oversampling(filename, item)
                            SaveToFile(contents, root.replace(datPath, outPath, 1), file)
    return

def GenerateASTs(dataPath, ASTsPath):
    '''
    Generate AST files from dataPath to ASTsPath.
    clang -fmodules -fsyntax-only -Xclang -ast-dump [dataPath]/**/**.c(pp)   1>[ASTsPath]/**/**.c(pp).txt  2>NUL
    :param dataPath: data path.
    :param ASTPath: ast path.
    :return: 0 if success.
    '''

    # print the arguments.
    print('Data Path: ' + dataPath)
    print('ASTs Path: ' + ASTsPath)

    # go through each file in data path.
    for root, ds, fs in os.walk(dataPath):
        for file in fs:
            extname = os.path.splitext(file)[1]                 # get the file extension.
            if '.c' == extname or '.cpp' == extname:            # if file extension is .c or .cpp.
                outRoot = root.replace(dataPath, ASTsPath, 1)   # get the output path.
                if not os.path.exists(outRoot):                 # if output path does not exist, build the directory.
                    os.makedirs(outRoot)
                filename = os.path.join(root, file)             # get the program file name.
                astsname = os.path.join(outRoot, file + '.txt') # get the ast file name.
                # set the shell command.
                cmdstr = 'clang -fmodules -fsyntax-only -Xclang -ast-dump  ' + filename + '  1>' + astsname + '  2>NUL'
                print('[shell] >>> ' + cmdstr)
                os.system(cmdstr)                               # run the shell command.

    return 0

def ScanPatches(patchPath, dataPatch):
    def ReadPatch(filename, dataPatch):
        def FindCorrespondLine(atStat, lineNum):
            for item in reversed(atStat):
                if item[0] < lineNum:
                    break
            return item[1:]

        # read the patch file.
        fp = open(filename, encoding='utf-8', errors='ignore')  # get file point.
        lines = fp.readlines()                                  # read all lines.
        numLines = len(lines)                                   # get the line number.

        # find all @@ -000,00 +000,00 @@
        atStat = []     # [[i, 70, 71, 70, 73], ...]
        for i in range(numLines):
            # search from line[i]
            if re.match(r'@@ -\d+,\d+ \+\d+,\d+ @@', lines[i]):
                # get @ statement.
                atstmt = re.findall(r'@@ -\d+,\d+ \+\d+,\d+ @@', lines[i])
                atnum = re.findall(r'\d+', atstmt[0]) # get 4 numbers
                bStart = int(atnum[0])
                bEnd = bStart + max(1, int(atnum[1])) - 1
                aStart = int(atnum[2])
                aEnd = aStart + max(1, int(atnum[3])) - 1
                if 0: print(i, bStart, bEnd, aStart, aEnd)
                atStat.append([i, bStart, bEnd, aStart, aEnd])
        if 0: print(atStat)

        # read contents line by line.
        outputs = []
        bfname = ''
        afname = ''
        for i in range(numLines):
            # line[i]
            # find diff --git a/**** b/****
            if re.match(r'diff --git a/(.*) b/(.*)', lines[i]):
                segs = lines[i].split() # split the line.
                aname = segs[2][2:]     # get after name.
                bname = segs[3][2:]     # get before name.
                if 0: print(os.path.join(os.path.join(dataPatch, 'after'), aname), os.path.join(os.path.join(dataPatch, 'before'), bname))
                # check if two files exist.
                if (os.path.exists(os.path.join(os.path.join(dataPatch, 'after'), aname))
                        & os.path.exists(os.path.join(os.path.join(dataPatch, 'before'), bname))):
                    bfname = os.path.join(os.path.join(dataPatch, 'before'), bname).replace('\\', '/')
                    afname = os.path.join(os.path.join(dataPatch, 'after'), aname).replace('\\', '/')
                else:
                    bfname = ''
                    afname = ''
            # find IF statement.
            ifstmts = re.findall(r'if\s*\(', lines[i])
            if (len(ifstmts) & (bfname != '') & (afname != '')): # if lines[i] contains IF statements.
                if 0: print(i, lines[i], end='')
                block = FindCorrespondLine(atStat, i)       # get [70, 71, 70, 73]
                if 0: print(block)
                outputs.append([bfname, afname] + block + [filename])

        # delete replications.
        finalOut = []
        for item in outputs:
            if not item in finalOut:
                finalOut.append(item)
        if 0: print(finalOut)

        return finalOut

    # get all the changes that contains IF statements.
    outputs = []
    # scan all the patch files.
    for root, ds, fs in os.walk(patchPath):
        for file in fs:
            filename = os.path.join(root, file)  # get the patch filename.
            filename = filename.replace('\\', '/')
            # read the patch and get all patch changes that contains IF statements.
            out = ReadPatch(filename, dataPatch)
            outputs.extend(out)

    # delete replications.
    finalOut = []
    for item in outputs:
        if not item in finalOut:
            finalOut.append(item)
    if _DEBUG_:
        print('[DEBUG] All the patch changes contains IF statements:\n[DEBUG] ', end='')
        print(finalOut)

    return finalOut

def FindIfStmts(fname):
    # check if the ast file exists.
    if not os.path.exists(fname):
        print('[Warning] Cannot find the file %s' % (fname))
        return []

    # read lines of the ast file.
    fp = open(fname, encoding='utf-8', errors='ignore')     # get the ast file point.
    lines = fp.readlines()                                  # read all lines.
    numLines = len(lines)                                   # get the line number.

    ifstmts = []    # [[74, 77], ...]
    # search each line in the ast file.
    for i in range(numLines):   # lines[i].
        # find ****IfStmt *** <line:000:00, line:000:00> ***
        if re.match(r'(.*)IfStmt(.*)<line:\d+:\d+, line:\d+:\d+>(.*)', lines[i]):
            if _DEBUG_ & 0: print('[DEBUG] ', i, lines[i], end='')
            # find <line:000:00, line:000:00>
            linestmt = re.findall(r'<line:\d+:\d+, line:\d+:\d+>', lines[i])
            if _DEBUG_ & 0: print('[DEBUG] ', linestmt)
            # find line numbers in <line:000:00, line:000:00>
            numbers = re.findall(r'\d+', linestmt[0])
            if _DEBUG_ & 0: print('[DEBUG] ', [numbers[0], numbers[2]])
            ifstmts.append([int(numbers[0]), int(numbers[2])])

    # return line numbers of if statements.
    if _DEBUG_: print('[DEBUG] ', ifstmts)
    return ifstmts

def CheckIfChanged(fname, ifstmt, patchList, mode='after'):
    if mode == 'after':
        for item in patchList:
            if (fname == item[1]):
                if (item[4] <= ifstmt[0]) & (ifstmt[0] <= item[5]):
                    return item[6]
    elif mode == 'before':
        for item in patchList:
            if (fname == item[0]):
                if (item[2] <= ifstmt[0]) & (ifstmt[0] <= item[3]):
                    return item[6]
    return ''

def Oversampling(fname, ifstmt):
    # read file from the filename.
    fp = open(fname, encoding='utf-8', errors='ignore')
    lines = fp.readlines()
    numLines = len(lines)
    # sparse the augments.
    stmtStart = ifstmt[0] - 1
    stmtEnd = ifstmt[1] - 1
    if 0: print(stmtStart, stmtEnd)
    # print each line of the program file.
    for i in range(stmtStart-3, stmtEnd+4):
        if 0: print(i, lines[i], end='')

    # get the IF block
    ifBlock = ''
    for i in range(stmtStart, stmtEnd+1):
        ifBlock += lines[i]
    if _DEBUG_: print(ifBlock)
    # find the index of the first if__(
    ifStart = re.findall(r'if\s*\(', ifBlock)
    if 0: print(ifStart)
    indexIfStart = ifBlock.index(ifStart[0])
    if 0: print(indexIfStart, ifBlock[indexIfStart])
    # find the corresponding (
    indexIfLeft = indexIfStart + len(ifStart[0]) - 1
    if 0: print(indexIfLeft, ifBlock[indexIfLeft])
    # find the corresponding )
    mark = 1
    indexIfRight = indexIfLeft
    while(mark):
        indexIfRight += 1
        if ifBlock[indexIfRight] == '(':
            mark += 1
        elif ifBlock[indexIfRight] == ')':
            mark -= 1
    if 0: print(indexIfRight, ifBlock[indexIfRight])

    # modify the if block.
    nChoice = random.randint(0, 1)
    if (0 == nChoice):
        newBlock = ifBlock[:indexIfRight] + ' || _SYS_ZERO' + ifBlock[indexIfRight:]
        newBlock = ' ' * indexIfStart + 'const int _SYS_ZERO = 0; \n' + newBlock
    elif (1 == nChoice):
        newBlock = ifBlock[:indexIfRight] + ' && _SYS_ONE' + ifBlock[indexIfRight:]
        newBlock = ' ' * indexIfStart + 'const int _SYS_ONE = 1; \n' + newBlock
    if _DEBUG_: print(newBlock)
    # change string to lists.
    newBlockList = newBlock.split('\n')
    ifBlockList = []
    for stmt in newBlockList[:-1]:
        ifBlockList.append(stmt + '\n')
    if 0: print(ifBlockList)

    # delete original block.
    del lines[stmtStart:stmtEnd+1]
    # add modified block.
    for i in range(len(ifBlockList)):
        lines.insert(stmtStart+i, ifBlockList[i])
    for i in range(stmtStart-3, stmtEnd+4):
        if 0: print(i, lines[i], end='')

    return lines

def SaveToFile(lines, path, file):
    # check the path.
    if not os.path.exists(path):
        os.makedirs(path)

    # get all filenames in the folder.
    fileList = os.listdir(path)
    if 0: print(fileList)
    # get the filename and extension.
    filename = os.path.splitext(file)
    if 0: print(filename[0], filename[1])

    # find an available name.
    fileIdx = 1
    while(1):
        fname = filename[0] + '_' + str(fileIdx).zfill(4) + filename[1]
        if not os.path.exists(os.path.join(path, fname)):
            break
        else:
            fileIdx += 1

    # save file.
    fpath = os.path.join(path, fname)
    fp = open(fpath, 'w')
    for i in range(len(lines)):
        fp.write(lines[i])
    fp.close()

    return 0

if __name__ == '__main__':
    main()