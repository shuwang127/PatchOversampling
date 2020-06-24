# PatchOversampling
    '''
    Security Patch Group: Patch Oversampling Task.
    Developer: Shu Wang
    Date: 2020-06-24
    Version: S2020.06.24 (Version 5.0)
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
