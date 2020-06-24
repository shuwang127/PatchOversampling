'''
Security Patch Group: Patch Oversampling Task.
Developer: Shu Wang
Date: 2020-06-22
Version: S2020.06.22 (Version 5)
File Structure:
    PatchClearance
        |-- _old_versions           # old versions for the programs.
        |-- openssl                 # openssl data.
            |-- file_jk             # program files.
                | -- after          # 'after' version.
                | -- before         # 'before' version
            |-- patch_jk            # patch files.
            |-- ast_jk              # AST files.
                | -- after          # 'after' version.
                | -- before         # 'before' version
            |-- out_jk              # output program files.
                | -- after          # 'after' version.
                | -- before         # 'before' version
            |-- outp_jk             # output patch files.
        |-- code_modification.py    # main entrance.
        |-- README.md               # readme file.
Prerequirements:
    LLVM 10.0.0 (Download Link: http://www.llvm.org/releases/download.html)
Usage:
    python code_modification.py
'''

import os
import re
import random
import numpy as np

rootPath = './'
appPath = rootPath + '/openssl/'
datPath = appPath + '/file_jk/'
patPath = appPath + '/patch_jk/'
astPath = appPath + '/ast_jk/'
outPath = appPath + '/out_jk/'
optPath = appPath + '/outp_jk/'
version = 'after' # 'after' or 'before'

_DEBUG_ = 1 # 1: only use one sample, 0: use all samples.
_CHOICE_ = 8 # Choice

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
                    for ifstmt in ifstmts:
                        # check if the IF statements changed in diff file.
                        patchname, linenums = CheckIfChanged(filename, ifstmt, patchList, version)
                        if (len(patchname)): # find the changed IF statements from diff file.
                            if _DEBUG_: print('[DEBUG] ', filename, ifstmt, patchname, linenums)
                            # ===========================================================
                            # get variants of the source code.
                            codeChanged, nChoice = CodeOversampling(filename, ifstmt, 2)
                            #SaveToFile(codeChanged, root.replace(datPath, outPath, 1), file)
                            # get variants of the patch.
                            patchChanged, _, ok = PatchOversampling(patchname, version, filename, linenums, ifstmt, nChoice)
                            if (ok): SaveToFile(patchChanged, optPath, patchname.replace(patPath, ''))

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
    '''
    Scan the patches and find all hunks that contains IF statements.
    :param patchPath: patch file path.
    :param dataPatch: program file path.
    :return: all the hunk information that contains IF statements.
    [[bfname, afname, bStart, bEnd, aStart, aEnd, filename], ...]
    '''
    def ReadPatch(filename, dataPatch):
        '''
        Scan the patches and find all hunks that contains IF statements.
        :param filename: patch file name.
        :param dataPatch: program file path.
        :return: all the hunk information that contains IF statements.
        [[bfname, afname, bStart, bEnd, aStart, aEnd, filename], ...]
        '''
        def FindCorrespondLine(atStat, lineNum):
            '''
            Find the line numbers of the hunk.
            :param atStat: all the hunk information.
            [[lineNum, bStart, bEnd, aStart, aEnd], ...]
            :param lineNum: the total line number of the patch file.
            :return: line number of hunk.
            [bStart, bEnd, aStart, aEnd]
            '''
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
                if 0:
                    print(i, bStart, bEnd, aStart, aEnd)
                atStat.append([i, bStart, bEnd, aStart, aEnd])
        if 0:
            print(atStat)

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
                if 0:
                    print(os.path.join(os.path.join(dataPatch, 'after'), aname), os.path.join(os.path.join(dataPatch, 'before'), bname))
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
                if 0:
                    print(i, lines[i], end='')
                block = FindCorrespondLine(atStat, i)       # get [70, 71, 70, 73]
                if 0:
                    print(block)
                outputs.append([bfname, afname] + block + [filename])

        # delete replications.
        finalOut = []
        for item in outputs:
            if not item in finalOut:
                finalOut.append(item)
        if 0:
            print(finalOut)

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
    '''
    Find all the IF statements from the AST file.
    :param fname: AST file name.
    :return: All the IF block information.
    [[ifStart, ifEnd], ...]
    '''
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
            if _DEBUG_ & 0:
                print('[DEBUG] ', i, lines[i], end='')
            # find <line:000:00, line:000:00>
            linestmt = re.findall(r'<line:\d+:\d+, line:\d+:\d+>', lines[i])
            if _DEBUG_ & 0:
                print('[DEBUG] ', linestmt)
            # find line numbers in <line:000:00, line:000:00>
            numbers = re.findall(r'\d+', linestmt[0])
            if _DEBUG_ & 0:
                print('[DEBUG] ', [numbers[0], numbers[2]])
            ifstmts.append([int(numbers[0]), int(numbers[2])])

    # return line numbers of if statements.
    if _DEBUG_:
        print('[DEBUG] ', ifstmts)
    return ifstmts

def CheckIfChanged(fname, ifstmt, patchList, mode='after'):
    '''
    Check if the IF statement is changed in the patches.
    :param fname: program file.
    :param ifstmt: IF statement.
    [ifStart, ifEnd]
    :param patchList: all the hunk information that contains IF statements.
    [[bfname, afname, bStart, bEnd, aStart, aEnd, filename], ...]
    :param mode: 'after' or 'before'
    :return: YES: filename, [bStart, bEnd, aStart, aEnd]
             NO: '', [0, 0, 0, 0]
    '''
    if mode == 'after':
        for item in patchList:
            if (fname == item[1]):
                if (item[4]+3 <= ifstmt[0]) & (ifstmt[0] <= item[5]-3):
                    return item[6], item[2:6]
    elif mode == 'before':
        for item in patchList:
            if (fname == item[0]):
                if (item[2]+3 <= ifstmt[0]) & (ifstmt[0] <= item[3]-3):
                    return item[6], item[2:6]
    return '', [0, 0, 0, 0]

def CodeOversampling(fname, ifstmt, nChoice=-1):
    '''
    Code Oversampling.
    :param fname: the program file.
    :param ifstmt: IF statement.
    [ifStart, ifEnd]
    :param nChoice: the choice of oversampling. -1: random, 0-N: specific.
    :return: lines: the changed code.
             nChoice: the final choice of oversampling.
    '''
    # read file from the filename.
    fp = open(fname, encoding='utf-8', errors='ignore')
    lines = fp.readlines()
    numLines = len(lines)
    # sparse the augments.
    stmtStart = ifstmt[0] - 1
    stmtEnd = ifstmt[1] - 1
    if 0:
        print(stmtStart, stmtEnd)
    # print each line of the program file.
    for i in range(stmtStart-3, stmtEnd+4):
        if 0:
            print(i, lines[i], end='')

    # locate: get the IF block
    ifBlock = ''
    for i in range(stmtStart, stmtEnd+1):
        ifBlock += lines[i]
    if _DEBUG_: print(ifBlock)
    # find the index of the first if__(
    ifStart = re.findall(r'if\s*\(', ifBlock)
    if 0:
        print(ifStart)
    indexIfStart = ifBlock.index(ifStart[0])
    if 0:
        print(indexIfStart, ifBlock[indexIfStart])
    # find the corresponding (
    indexIfLeft = indexIfStart + len(ifStart[0]) - 1
    if 0:
        print(indexIfLeft, ifBlock[indexIfLeft])
    # find the corresponding )
    mark = 1
    indexIfRight = indexIfLeft
    while(mark):
        indexIfRight += 1
        if ifBlock[indexIfRight] == '(':
            mark += 1
        elif ifBlock[indexIfRight] == ')':
            mark -= 1
    if 0:
        print(indexIfRight, ifBlock[indexIfRight])

    # modify: change the IF block.
    if (nChoice not in range(_CHOICE_)):         # if nChoice is not in our settings.
        nChoice = random.randint(0, _CHOICE_-1)      # randomly choose.
    newBlock = ''
    if (0 == nChoice): # add 1, modify 1
        newBlock += ' ' * indexIfStart + 'const int _SYS_ZERO = 0; \n'
        newBlock += ifBlock[:indexIfLeft+1] + '_SYS_ZERO || ' + ifBlock[indexIfLeft+1:]
    elif (1 == nChoice): # add 1, modify 1
        newBlock += ' ' * indexIfStart + 'const int _SYS_ONE = 1; \n'
        newBlock += ifBlock[:indexIfLeft+1] + '_SYS_ONE && ' + ifBlock[indexIfLeft+1:]
    elif (2 == nChoice):
        newBlock += ' ' * indexIfStart + 'bool _SYS_STMT = ' + ifBlock[indexIfLeft+1:indexIfRight] + ';\n'
        newBlock += ifBlock[:indexIfLeft+1] + 'True == _SYS_STMT' + ifBlock[indexIfRight:]
    elif (3 == nChoice):
        newBlock += ' ' * indexIfStart + 'bool _SYS_STMT = !(' + ifBlock[indexIfLeft + 1:indexIfRight] + ');\n'
        newBlock += ifBlock[:indexIfLeft + 1] + '!_SYS_STMT' + ifBlock[indexIfRight:]
    elif (4 == nChoice):
        newBlock += ' ' * indexIfStart + 'int _SYS_VAL = 0;\n'
        newBlock += ifBlock[:indexIfRight+1] + ' {\n'
        newBlock += ' ' * (indexIfStart+4) + 'int _SYS_VAL = 1;\n'
        newBlock += ' ' * indexIfStart +'}\n'
        newBlock += ifBlock[:indexIfLeft+1] + '_SYS_VAL && ' + ifBlock[indexIfLeft+1:]
    elif (5 == nChoice):
        newBlock += ' ' * indexIfStart + 'int _SYS_VAL = 1;\n'
        newBlock += ifBlock[:indexIfRight + 1] + ' {\n'
        newBlock += ' ' * (indexIfStart + 4) + 'int _SYS_VAL = 0;\n'
        newBlock += ' ' * indexIfStart + '}\n'
        newBlock += ifBlock[:indexIfLeft+1] + '!_SYS_VAL || ' + ifBlock[indexIfLeft+1:]
    elif (6 == nChoice):
        newBlock += ' ' * indexIfStart + 'int _SYS_VAL = 0;\n'
        newBlock += ifBlock[:indexIfRight + 1] + ' {\n'
        newBlock += ' ' * (indexIfStart + 4) + 'int _SYS_VAL = 1;\n'
        newBlock += ' ' * indexIfStart + '}\n'
        newBlock += ifBlock[:indexIfLeft+1] + '_SYS_VAL' + ifBlock[indexIfRight:]
    elif (7 == nChoice):
        newBlock += ' ' * indexIfStart + 'int _SYS_VAL = 1;\n'
        newBlock += ifBlock[:indexIfRight + 1] + ' {\n'
        newBlock += ' ' * (indexIfStart + 4) + 'int _SYS_VAL = 0;\n'
        newBlock += ' ' * indexIfStart + '}\n'
        newBlock += ifBlock[:indexIfLeft + 1] + '!_SYS_VAL' + ifBlock[indexIfRight:]
    if _DEBUG_: print(newBlock)
    # change string to lists.
    newBlockList = newBlock.split('\n')
    ifBlockList = []
    for stmt in newBlockList[:-1]:
        ifBlockList.append(stmt + '\n')
    if 0:
        print(ifBlockList)

    # delete original block.
    del lines[stmtStart:stmtEnd+1]
    # add modified block.
    for i in range(len(ifBlockList)):
        lines.insert(stmtStart+i, ifBlockList[i])
    for i in range(stmtStart-3, stmtEnd+4):
        if 0:
            print(i, lines[i], end='')

    return lines, nChoice

def SaveToFile(lines, path, file):
    '''
    Save the changed code or patch.
    :param lines: the changed code or patch.
    :param path: the save path.
    :param file: the save filename without variant.
    :return: 0 if success.
    '''
    # check the path.
    if not os.path.exists(path):
        os.makedirs(path)

    # get all filenames in the folder.
    fileList = os.listdir(path)
    if 0:
        print(fileList)
    # get the filename and extension.
    filename = os.path.splitext(file)
    if 0:
        print(filename[0], filename[1])

    # find an available name.
    fileIdx = 1
    while(1):
        fname = filename[0] + '_' + str(fileIdx).zfill(4) + filename[1]
        if not os.path.exists(os.path.join(path, fname)):
            break
        else:
            fileIdx += 1

    # save file.
    fpath = os.path.join(path, fname).replace('\\', '/')
    fp = open(fpath, 'w')
    for i in range(len(lines)):
        fp.write(lines[i])
    fp.close()
    if _DEBUG_:
        print('[DEBUG] Save code variant in ' + fpath)

    return 0

def PatchOversampling(pname, version, fname, lnums, ifstmt, nChoice=-1):
    '''
    Patch Oversampling.
    :param pname: patch filename.
    :param version: 'after' or 'before'.
    :param fname: program filename.
    :param lnums: corresponding hunk.
    [bStart, bEnd, aStart, aEnd]
    :param ifstmt: IF statement.
    [ifStart, ifEnd]
    :param nChoice: the choice of oversampling. -1: random; 0-N: specific.
    :return: lines: changed/unchanged patch.
             nChoice: the final choice. -1 for failure; 0-N for success.
             ok: 0 for failure; 1 for success.
    '''
    if _DEBUG_:
        print(pname, version, fname, lnums, ifstmt, nChoice)
    # get the matching file string.
    filestr = fname.replace(datPath, '', 1)
    filestr = filestr.replace(version, '', 1)
    if 'after' == version:
        filestr = 'a' + filestr
    elif 'before' == version:
        filestr = 'b' + filestr

    # get the matching line string.
    linestr = '@@ -'
    linestr += str(lnums[0]) + ','
    linestr += str(lnums[1]-lnums[0]+1) + ' +'
    linestr += str(lnums[2]) + ','
    linestr += str(lnums[3]-lnums[2]+1) + ' @@'

    # get version string.
    verstr = '+' if (version == 'after') else '-' if (version == 'before') else ' '
    verlnum = lnums[2] if (version == 'after') else lnums[0] if (version == 'before') else 0

    # read the patch file.
    fp = open(pname, encoding='utf-8', errors='ignore')
    lines = fp.readlines()
    numLines = len(lines)

    # get the line numbers of IF block in diff file.
    markDiff = 0
    markLine = 0
    cnt = 0
    ifloc = [0, 0]
    # scan each line of the patch file.
    for i in range(numLines):  # lines[i].
        # find diff --git a/**** b/****
        if re.match(r'diff --git a/(.*) b/(.*)', lines[i]):
            segs = lines[i].split()  # split the line.
            markDiff = 1 if (filestr in segs) else 0

        # find @@ -000,00 +000,00 @@
        if re.match(r'@@ -\d+,\d+ \+\d+,\d+ @@', lines[i]):
            # get @ statement.
            atstmt = re.findall(r'@@ -\d+,\d+ \+\d+,\d+ @@', lines[i])
            markLine = 1 if (atstmt[0] == linestr) else 0

        if ((markDiff & markLine) and (lines[i][0] in ['@', ' ', verstr])):
            if _DEBUG_: print(i, lines[i], end='')
            cnt += 1
            if cnt == (ifstmt[0] - verlnum + 2):
                ifloc[0] = i
                ifloc[1] = min(ifloc[0] + ifstmt[1] - ifstmt[0], numLines - 1)

    # locate: get the IF block
    if _DEBUG_: print(ifloc)
    ifBlock = ''
    for i in range(ifloc[0], ifloc[1] + 1):
        ifBlock += lines[i]
    # find the index of the first if__(
    ifStart = re.findall(r'if\s*\(', ifBlock)
    if ([] == ifStart):
        return lines, -1, 0
    indexIfStart = ifBlock.index(ifStart[0])
    # find the corresponding (
    indexIfLeft = indexIfStart + len(ifStart[0]) - 1
    # find the corresponding )
    mark = 1
    indexIfRight = indexIfLeft
    while (mark):
        indexIfRight += 1
        if ifBlock[indexIfRight] == '(':
            mark += 1
        elif ifBlock[indexIfRight] == ')':
            mark -= 1

    # modify: change the IF block.
    if (nChoice not in range(_CHOICE_)):  # if nChoice is not in our settings.
        nChoice = random.randint(0, _CHOICE_ - 1)  # randomly choose.

    nChoice = 2
    newBlock = ''
    if (0 == nChoice):
        newBlock += verstr + ' ' * (indexIfStart-1) + 'const int _SYS_ZERO = 0; \n'
        if ifBlock[0] == verstr: # start with '+' or '-'
            newBlock += ifBlock[:indexIfLeft + 1] + '_SYS_ZERO || ' + ifBlock[indexIfLeft + 1:]
        elif verstr == '+': # start with ' '
            newBlock += '+' + ifBlock[1:indexIfLeft + 1] + '_SYS_ZERO || ' + ifBlock[indexIfLeft + 1:]
            newBlock = '-' + ifBlock.split('\n')[0][1:] + '\n' + newBlock
        elif verstr == '-': # start with ' ' and before.
            indexEnter = ifBlock.find('\n', 1)
            newBlock += '-' + ifBlock[1:indexIfLeft + 1] + '_SYS_ZERO || ' + ifBlock[indexIfLeft + 1:indexEnter+1]
            newBlock += '+' + ifBlock.split('\n')[0][1:] + '\n'
            newBlock += ifBlock[indexEnter + 1:]
    elif (1 == nChoice):
        newBlock += verstr + ' ' * (indexIfStart - 1) + 'const int _SYS_ONE = 1; \n'
        if ifBlock[0] == verstr:  # start with '+' or '-'
            newBlock += ifBlock[:indexIfLeft + 1] + '_SYS_ONE && ' + ifBlock[indexIfLeft + 1:]
        elif verstr == '+':  # start with ' '
            newBlock += '+' + ifBlock[1:indexIfLeft + 1] + '_SYS_ONE && ' + ifBlock[indexIfLeft + 1:]
            newBlock = '-' + ifBlock.split('\n')[0][1:] + '\n' + newBlock
        elif verstr == '-':  # start with ' ' and before.
            indexEnter = ifBlock.find('\n', 1)
            newBlock += '-' + ifBlock[1:indexIfLeft + 1] + '_SYS_ONE && ' + ifBlock[indexIfLeft + 1:indexEnter + 1]
            newBlock += '+' + ifBlock.split('\n')[0][1:] + '\n'
            newBlock += ifBlock[indexEnter + 1:]
    elif (2 == nChoice):
        print(ifBlock, end='')
        print('------------------------------')
        ifBlockSeg = ifBlock.split('\n')
        del ifBlockSeg[-1]
        print(ifBlockSeg)
        print('------------------------------')
        indexIfJudgeEnd = ifBlock[indexIfRight + 1:].find('\n', 1)
        ifPatchDel = '-' + ifBlock[1:indexIfRight+1+indexIfJudgeEnd+1]
        ifPatchDel = ifPatchDel.replace('\n ', '\n-')
        ifPatchDel = ifPatchDel.replace('\n+', '\n-')
        ifPatchAdd = '+' + ' ' * (indexIfStart-1) + 'bool _SYS_STMT = ' + ifBlock[indexIfLeft + 1:indexIfRight] + ';\n'
        ifPatchAdd = ifPatchAdd.replace('\n ', '\n+')
        ifPatchAdd = ifPatchAdd.replace('\n-', '\n+')
        ifPatchAdd += '+' + ifBlock[1:indexIfLeft+1] + 'True == _SYS_STMT' + ifBlock[indexIfRight:indexIfRight+1+indexIfJudgeEnd+1]
        ifPatch = ifPatchDel + ifPatchAdd
        ifPatchSeg = ifPatch.split('\n')
        del ifPatchSeg[-1]
        print(ifPatchSeg)
        print('------------------------------')
        marks = -1 * np.ones(len(ifBlockSeg)+1, dtype=int)
        for i in range(len(ifBlockSeg)):
            for j in range(1+np.max(marks), len(ifPatchSeg)):
                if ifBlockSeg[i][1:] == ifPatchSeg[j][1:]:
                    marks[i] = j
                    break
        print(marks)

        for i in reversed(range(len(marks)-1)):
            if (marks[i] >= 0):
                print(i, marks[i])
                if (-1 == np.max(marks[i+1:])):
                    ifBlockSeg = ifBlockSeg[:i+1] + ifPatchSeg[marks[i]+1:] + ifBlockSeg[i+1:]
                    print(ifBlockSeg)
                else:
                    indexNext = [item for item in marks[i+1:] if (item >= 0)][0]
                    ifBlockSeg = ifBlockSeg[:i+1] + ifPatchSeg[marks[i]+1:indexNext] + ifBlockSeg[i+1:]

                if (ifPatchSeg[marks])






        print('------------------------------')





    elif (3 == nChoice):
        newBlock += verstr + ' ' * (indexIfStart-1) + 'bool _SYS_STMT = !(' + ifBlock[indexIfLeft + 1:indexIfRight] + ');\n'
        newBlock += ifBlock[:indexIfLeft + 1] + '!_SYS_STMT' + ifBlock[indexIfRight:]
    elif (4 == nChoice):
        newBlock += verstr + ' ' * (indexIfStart-1) + 'int _SYS_VAL = 0;\n'
        newBlock += ifBlock[:indexIfRight + 1] + ' {\n'
        newBlock += verstr + ' ' * (indexIfStart + 3) + 'int _SYS_VAL = 1;\n'
        newBlock += verstr + ' ' * (indexIfStart-1) + '}\n'
        newBlock += ifBlock[:indexIfLeft + 1] + '_SYS_VAL && ' + ifBlock[indexIfLeft + 1:]
    elif (5 == nChoice):
        newBlock += verstr + ' ' * (indexIfStart-1) + 'int _SYS_VAL = 1;\n'
        newBlock += ifBlock[:indexIfRight + 1] + ' {\n'
        newBlock += verstr + ' ' * (indexIfStart + 3) + 'int _SYS_VAL = 0;\n'
        newBlock += verstr + ' ' * (indexIfStart-1) + '}\n'
        newBlock += ifBlock[:indexIfLeft + 1] + '!_SYS_VAL || ' + ifBlock[indexIfLeft + 1:]
    elif (6 == nChoice):
        newBlock += verstr + ' ' * (indexIfStart-1) + 'int _SYS_VAL = 0;\n'
        newBlock += ifBlock[:indexIfRight + 1] + ' {\n'
        newBlock += verstr + ' ' * (indexIfStart + 3) + 'int _SYS_VAL = 1;\n'
        newBlock += verstr + ' ' * (indexIfStart-1) + '}\n'
        newBlock += ifBlock[:indexIfLeft + 1] + '_SYS_VAL' + ifBlock[indexIfRight:]
    elif (7 == nChoice):
        newBlock += verstr + ' ' * (indexIfStart-1) + 'int _SYS_VAL = 1;\n'
        newBlock += ifBlock[:indexIfRight + 1] + ' {\n'
        newBlock += verstr + ' ' * (indexIfStart+3) + 'int _SYS_VAL = 0;\n'
        newBlock += verstr + ' ' * (indexIfStart-1) + '}\n'
        newBlock += ifBlock[:indexIfLeft + 1] + '!_SYS_VAL' + ifBlock[indexIfRight:]
    # change string to lists.
    newBlockList = newBlock.split('\n')
    ifBlockList = []
    for stmt in newBlockList[:-1]:
        ifBlockList.append(stmt + '\n')

    # delete original block.
    del lines[ifloc[0]:ifloc[1] + 1]
    # add modified block.
    for i in range(len(ifBlockList)):
        lines.insert(ifloc[0] + i, ifBlockList[i])
    for i in range(ifloc[0]-3, min(ifloc[1]+4, len(lines))):
        if _DEBUG_: print(i, lines[i], end='')

    return lines, nChoice, 1

if __name__ == '__main__':
    main()