import os
import re
import random

rootPath = './'
appPath = rootPath + '/openssl/'
datPath = appPath + '/file_jk/'
patPath = appPath + '/patch_jk/'
astPath = appPath + '/ast_jk/'
outPath = appPath + '/out_jk/'

_DEBUG_ = 0 # 1: only use one sample, 0: use all samples.

def main():
    global _DEBUG_
    # Generate AST files from program files.
    #GenerateASTs(datPath, astPath)
    # get patch lists from patch path.
    patchList = ScanPatches(patPath)
    '''
    # scan the after files.
    for root, ds, fs in os.walk(datPath + '/after/'):
        for file in fs:
            if _DEBUG_ <= 1:
                if _DEBUG_ == 1:
                    _DEBUG_ += 1 # _DEBUG_ = 2
                # get the program file name.
                filename = os.path.join(root, file)
                print(filename)
                # get the corresponding semantic file name.
                semname = os.path.join(semPath + '/after/', os.path.splitext(file)[0] + '.txt')
                if _DEBUG_: print(semname)
                # find all IF statements in the semantic file.
                ifstmts = FindIfStmts(semname)
                if len(ifstmts): # IF statements exist in the program file.
                    # find the changed IF statements in diff file.
                    for item in ifstmts:
                        if (CheckIfChanged(file, item, patchList, 'after')):
                            print(item)
                            contents = Oversampling(filename, item)
                            SaveToFile(contents, outPath + '/after/', file)
    '''
    return

def GenerateASTs(dataPath, ASTsPath):
    '''
    Generate AST files from dataPath to ASTsPath.
    clang -fmodules -fsyntax-only -Xclang -ast-dump [dataPath]/**/**.c(pp)   1>[ASTsPath]/**/**.c(pp).txt  2>NUL
    :param dataPath:
    :param ASTPath:
    :return:
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

def FindIfStmts(fname):
    # check if the semantic file exists.
    if not os.path.exists(fname):
        print('[Warning] Cannot find the file %s' % (fname))
        return []

    # read lines of the semantic file.
    fp = open(fname, encoding='utf-8', errors='ignore')
    lines = fp.readlines()
    numLines = len(lines)

    ifstmts = []
    # print the semantic file with each line.
    for i in range(numLines):
        # find ****IfStmt *** <line:000:00, line:000:00> ***
        if re.match(r'(.*)IfStmt(.*)<line:\d+:\d+, line:\d+:\d+>(.*)', lines[i]):
            if _DEBUG_: print(i, lines[i], end='')
            # find <line:000:00, line:000:00>
            linestmt = re.findall(r'<line:\d+:\d+, line:\d+:\d+>', lines[i])
            if _DEBUG_: print(linestmt)
            # find numbers in <line:000:00, line:000:00>
            numbers = re.findall(r'\d+', linestmt[0])
            if _DEBUG_: print([numbers[0], numbers[2]])
            ifstmts.append([int(numbers[0]), int(numbers[2])])

    # return line numbers of if statements.
    if _DEBUG_: print(ifstmts)
    return ifstmts

def Oversampling(fname, ifstmt):
    # read file from the filename.
    fp = open(fname, encoding='utf-8', errors='ignore')
    lines = fp.readlines()
    numLines = len(lines)
    # sparse the augments.
    stmtStart = ifstmt[0] - 1
    stmtEnd = ifstmt[1] - 1
    if _DEBUG_: print(stmtStart, stmtEnd)
    # print each line of the program file.
    for i in range(stmtStart-3, stmtEnd+4):
        if _DEBUG_: print(i, lines[i], end='')

    # get the IF block
    ifBlock = ''
    for i in range(stmtStart, stmtEnd+1):
        ifBlock += lines[i]
    if _DEBUG_: print(ifBlock)
    # find the index of the first if__(
    ifStart = re.findall(r'if\s*\(', ifBlock)
    if _DEBUG_: print(ifStart)
    indexIfStart = ifBlock.index(ifStart[0])
    if _DEBUG_: print(indexIfStart, ifBlock[indexIfStart])
    # find the corresponding (
    indexIfLeft = indexIfStart + len(ifStart[0]) - 1
    if _DEBUG_: print(indexIfLeft, ifBlock[indexIfLeft])
    # find the corresponding )
    mark = 1
    indexIfRight = indexIfLeft
    while(mark):
        indexIfRight += 1
        if ifBlock[indexIfRight] == '(':
            mark += 1
        elif ifBlock[indexIfRight] == ')':
            mark -= 1
    if _DEBUG_: print(indexIfRight, ifBlock[indexIfRight])

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
    if _DEBUG_: print(ifBlockList)

    # delete original block.
    del lines[stmtStart:stmtEnd+1]
    # add modified block.
    for i in range(len(ifBlockList)):
        lines.insert(stmtStart+i, ifBlockList[i])
    for i in range(stmtStart-3, stmtEnd+4):
        if _DEBUG_: print(i, lines[i], end='')

    return lines

def SaveToFile(lines, path, file):
    # get all filenames in the folder.
    fileList = os.listdir(path)
    if _DEBUG_: print(fileList)
    # get the filename and extension.
    filename = os.path.splitext(file)
    if _DEBUG_: print(filename[0], filename[1])

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

def ScanPatches(patchPath):
    def ReadPatch(filename):
        # convert filename.
        def ConvertFilename(fname):
            # split the filename with '/' and get extension.
            ext = ''
            segs = fname.split('/')
            if '.' in segs[-1]:
                ext = os.path.splitext(segs[-1])[1]
                segs = segs[:-1] + [os.path.splitext(segs[-1])[0]]
            if 0: print(segs, ext)

            # combine the file name.
            outname = '-'.join(segs[1:])
            if segs[0] == 'a':
                outname += '_after' + ext
            elif segs[0] == 'b':
                outname += '_before' + ext
            if 0: print(outname)

            return outname

        def FindCorrespondLine(atStat, lineNum):
            for item in reversed(atStat):
                if item[0] < lineNum:
                    break
            if 0: print(item)
            return item[1:]

        # read the patch file.
        fp = open(filename, encoding='utf-8', errors='ignore')
        lines = fp.readlines()
        numLines = len(lines)

        # find all @@ -000,00 +000,00 @@
        atStat = []
        for i in range(numLines):
            # line[i]
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
                segs = lines[i].split()
                if 0: print(segs[2], segs[3])
                aname = ConvertFilename(segs[2])
                bname = ConvertFilename(segs[3])
                # check if two files exist.
                if (os.path.exists(os.path.join(datPath + '/after/', aname))
                        & os.path.exists(os.path.join(datPath + '/before/', bname))):
                    bfname = bname
                    afname = aname
                else:
                    bfname = ''
                    afname = ''
            # find IF statement.
            ifstmts = re.findall(r'if\s*\(', lines[i])
            if (len(ifstmts) & (bfname != '') & (bfname != '')): # if lines[i] contains IF statements.
                if 0: print(i, lines[i], end='')
                block = FindCorrespondLine(atStat, i)
                if 0: print(block)
                outputs.append([bfname, afname] + block)

        # delete replications.
        finalOut = []
        for item in outputs:
            if not item in finalOut:
                finalOut.append(item)
        if _DEBUG_: print(finalOut)
        return finalOut

    outputs = []
    # scan all the patch files.
    for root, ds, fs in os.walk(patchPath):
        for file in fs:
            filename = os.path.join(root, file)
            if _DEBUG_: print(filename)
            out = ReadPatch(filename)
            outputs.extend(out)
    #file = '3b5a079d6b454d6d46279e2d56d625495c597633.patch'
    #filename = os.path.join(patchPath, file)
    #ReadPatch(filename)

    # delete replications.
    finalOut = []
    for item in outputs:
        if not item in finalOut:
            finalOut.append(item)
    if _DEBUG_: print(finalOut)
    return finalOut

def CheckIfChanged(fname, ifstmt, patchList, mode='after'):
    if mode == 'after':
        for item in patchList:
            if (fname == item[1]):
                if (item[4] <= ifstmt[0]) & (ifstmt[0] <= item[5]):
                    return 1
    elif mode == 'before':
        for item in patchList:
            if (fname == item[0]):
                if (item[2] <= ifstmt[0]) & (ifstmt[0] <= item[3]):
                    return 1
    return 0

if __name__ == '__main__':

    main()