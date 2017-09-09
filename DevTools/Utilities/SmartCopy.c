/*
 * Utility to work around bug in Windows file system, which causes
 * copy of large (10s of GB) files to fail.
 *
 * TODO: implement support for optional count parameter.
 */
#include <stdio.h>
#include <stdlib.h>
#include <windows.h>

#define RETRIES 10

void showError() {
    static char buf[1024];
    DWORD lastError = GetLastError();
    fprintf(stderr, "System error %ld (%08lx)\n", lastError, lastError);
    if (FormatMessage(FORMAT_MESSAGE_FROM_SYSTEM | 
                      FORMAT_MESSAGE_IGNORE_INSERTS,
                      NULL, lastError, 0, buf, sizeof buf - 1, NULL))
        fprintf(stderr, "[%s]\n", buf);
    exit(EXIT_FAILURE);
}

void bail() {
    showError();
    exit(EXIT_FAILURE);
}

int main(int ac, char** av) {

    // Local variables.
    char*         inName     = NULL;
    char*         outName    = NULL;
    HANDLE        inFile     = 0;
    HANDLE        outFile    = 0;
    __int64       copied     = 0;
    __int64       position   = 0;
    DWORD         count      = 0;
    LARGE_INTEGER start      = { 0 };

    // Collect the command-line arguments.
    if (ac < 4) {
        fprintf(stderr, "usage: SmartCopy infile outfile start [count]\n");
        return EXIT_FAILURE;
    }
    inName         = av[1];
    outName        = av[2];
    position     = _strtoui64(av[3], NULL, 10);
    start.QuadPart = position;
    count          = ac > 4 ? atol(av[4]) : 0; // ignored for now.

    // Open the source file for reading.
    inFile = CreateFile(inName, GENERIC_READ, FILE_SHARE_READ, NULL,
                        OPEN_EXISTING,
                        /* FILE_FLAG_SEQUENTIAL_SCAN, */
                        /* FILE_ATTRIBUTE_NORMAL, */
                        FILE_FLAG_NO_BUFFERING, NULL);
    if (!inFile) {
        fprintf(stderr, "can't open %s for reading\n", inName);
        bail();
    }
    fprintf(stderr, "%s opened for reading\n", inName);

    // Move to the resumption point in the input file.
    if (!SetFilePointerEx(inFile, start, NULL, FILE_BEGIN)) {
        fprintf(stderr, "can't move to position %s\n", av[3]);
        CloseHandle(inFile);
        bail();
    }
    fprintf(stderr, "%s positioned at byte %s\n", inName, av[3]);

    // Open the destination file for writing.
    outFile = CreateFile(outName, GENERIC_WRITE, 0, NULL, OPEN_ALWAYS,
                         /*FILE_ATTRIBUTE_NORMAL, */
                         FILE_FLAG_NO_BUFFERING, NULL);
    if (!outFile) {
        fprintf(stderr, "can't create %s\n", outName);
        CloseHandle(inFile);
        bail();
    }
    fprintf(stderr, "%s created for writing\n", outName);

    // Position the output file at the resumption point.
    if (!SetFilePointerEx(outFile, start, NULL, FILE_BEGIN)) {
        fprintf(stderr, "can't position %s at %s\n", outName, av[3]);
        CloseHandle(outFile);
        CloseHandle(inFile);
        bail();
    }
    fprintf(stderr, "%s positioned at %s\n", outName, av[3]);

    // Loop through as many bytes as we can, 10M at a time.
    while (1) {

        // Loop-local variables.
        static char buf[1024 * 1024 /* 8192 */];
        DWORD n = 0;
        DWORD m = 0;

        // Read a chunk.
        int failures = 0;
        while (failures < RETRIES) {
            if (ReadFile(inFile, (LPVOID)buf, sizeof buf, &n, NULL)) {
                failures = 0;
                break;
            }
            fprintf(stderr, "\nerror reading from %s\n", inName);
            showError();
            Sleep(++failures * 1000);

            // Move to the resumption point in the input file.
            while (failures < RETRIES) {
                start.QuadPart = position;
                if (SetFilePointerEx(inFile, start, NULL, FILE_BEGIN))
                    break;
                fprintf(stderr, "\ncan't move back to %I64d\n", position);
                showError();
                Sleep(++failures * 1000);
            }
        }
 
        if (failures) {
            CloseHandle(inFile);
            CloseHandle(outFile);
            exit(1);
        }

        // If we're not at the end, write the chunk.
        if (n < 1)
            break;
        while (failures < RETRIES) {
            m = 0;
            if (WriteFile(outFile, (LPVOID)buf, n, &m, NULL) && n == m) {
                failures = 0;
                break;
            }
            fprintf(stderr, "\nerror writing %ld bytes\n", n);
            showError();
            Sleep(++failures * 1000);
            
            // Position the output file at the resumption point.
            while (failures < RETRIES) {
                start.QuadPart = position;
                if (SetFilePointerEx(outFile, start, NULL, FILE_BEGIN))
                    break;
                fprintf(stderr, "can't move back to %I64d\n", position);
                showError();
                Sleep(++failures * 1000);
            }
        }
        if (failures) {
            CloseHandle(inFile);
            CloseHandle(outFile);
            exit(1);
        }

        // Show progress.
        copied += n;
        position += n;
        fprintf(stderr, "\rcopied %I64d bytes: new EOF is %I64d", copied,
                position);
    }

    // Clean up and go home.
    fprintf(stderr, "\n");
    CloseHandle(inFile);
    CloseHandle(outFile);
    return EXIT_SUCCESS;
}
