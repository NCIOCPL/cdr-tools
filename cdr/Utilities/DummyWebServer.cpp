/*
 * $Id: DummyWebServer.cpp,v 1.1 2008-01-05 00:45:21 bkline Exp $
 *
 * Test program to catch and log HTTP requests.  This is a very crude
 * implementation: everything is handled in a single thread, and we
 * assume that the headers contain a correct Content-length header
 * if there is a body to the request.  Listens on port 80 unless a
 * command-line argument is given to override the default.
 *
 * cl /EHsc DummyWebServer.cpp wsock32.lib
 *
 * $Log: not supported by cvs2svn $
 */

// System headers.
#include <winsock.h>
#include <iostream>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <ctime>

// Information about a single header line.
struct Header {
    std::string line;
    std::string name;
    std::string value;
};

// Local constants, functions.
const short DEFAULT_PORT = 80;
static void cleanup(void);
static bool readHeader(int, Header&);
static std::string readPayload(int, int);
static std::string makeFilename(int);
static void sendResponse(int);

/**
 * Creates a socket and listens for connections on it.  Runs until stopped
 * by an interrupt (e.g., control+C).
 */
main(int ac, char **av)
{
    WSAData             wsadata;
    int                 sock;
    struct sockaddr_in  addr;
    short               port = DEFAULT_PORT;
    int                 requestNumber = 1;

    // Let the operator override the default port.
    if (ac > 1)
        port = atoi(av[1]);

    // Windows needs special code to initialize its socket library.
    if (WSAStartup(0x0101, &wsadata) != 0) {
        unsigned long wsaError = WSAGetLastError();
        std::cerr << "WSAStartup() WSA error " << wsaError << '\n';
        return EXIT_FAILURE;
    }
    atexit(cleanup);
    std::cout << "initialized...\n";

    // Create the socket.
    sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock < 0) {
        unsigned long wsaError = (unsigned long)WSAGetLastError();
        perror("socket");
        std::cerr << "socket() WSA error: " << wsaError << '\n';
        return EXIT_FAILURE;
    }
    std::cout << "socket created...\n";

    // Bind it to the port we're going to listen on.
    addr.sin_family = AF_INET;
    addr.sin_port = htons(port);
    addr.sin_addr.s_addr = htonl(INADDR_ANY);
    if (bind(sock, (struct sockaddr *)&addr, sizeof addr) == SOCKET_ERROR) {
        unsigned long wsaError = (unsigned long)WSAGetLastError();
        perror("bind");
        std::cerr << "bind() WSA error: " << wsaError << '\n';
        return EXIT_FAILURE;
    }
    std::cout << "bound...\n";

    // Accept one connection at a time.
    if (listen(sock, 1) == SOCKET_ERROR) {
        unsigned long wsaError = (unsigned long)WSAGetLastError();
        perror("listen");
        std::cerr << "listen() WSA error: " << wsaError << '\n';
        return EXIT_FAILURE;
    }
    std::cout << "listening...\n";

    // Loop until a signal stops us.
    while (true) {
        struct sockaddr_in client_addr;
        int len = sizeof client_addr;
        memset(&client_addr, 0, sizeof client_addr);
        int fd = accept(sock, (struct sockaddr *)&client_addr, &len);
        if (fd < 0) {
            unsigned long wsaError = (unsigned long)WSAGetLastError();
            perror("accept");
            std::cerr << "accept() WSA error: " << wsaError << '\n';
            return EXIT_FAILURE;
        }

        // Log the bytes the client sends us.
        std::cout << "accepted request " << requestNumber << std::endl;
        std::string name = makeFilename(requestNumber++);
        std::cout << "logging request to " << name.c_str() << std::endl;
        FILE* fp = fopen(name.c_str(), "wb");

        // Read the headers (including the "start-line" which won't
        // have a name).  One of the headers may give us the length
        // of the payload body.
        Header header;
        int length = 0;
        while (readHeader(fd, header)) {
            if (header.name == "CONTENT-LENGTH")
                length = atoi(header.value.c_str());
            fwrite(header.line.c_str(), 1, header.line.length(), fp);
            fflush(fp);
        }
        if (!header.line.empty()) {
            fwrite(header.line.c_str(), 1, header.line.length(), fp);
            fflush(fp);
        }
        std::cout << "got headers for " << length << "-byte request"
                  << std::endl;

        // If there's a body, read and log that, too.
        if (length > 0) {
            std::string payload = readPayload(fd, length);
            fwrite(payload.c_str(), 1, payload.length(), fp);
            std::cout << "read payload successfully" << std::endl;
        }
        fclose(fp);
        sendResponse(fd);
        closesocket(fd);
    }
    return EXIT_SUCCESS;
}

/**
 * Clean up winsock resources.
 */
static void cleanup() {
    std::cerr << "stopping\n";
    WSACleanup();
}

/*
 * Read the request body.
 */
static std::string readPayload(int fd, int requested) {

    char* buf = new char[requested + 1];
    memset(buf, 0, requested + 1);
    
    // Keep reading until we have all the bytes, an error occurs, or we give
    // up after getting no bytes, sleeping for awhile, and then trying again.
    size_t totalRead = 0;
    bool canSleep = true;
    while (totalRead < requested) {
        size_t bytesLeft = requested - totalRead;
        int nRead = recv(fd, buf + totalRead, bytesLeft, 0);
        if (nRead < 0)
            throw "readPayload failure";
        else if (nRead == 0) {
            if (canSleep) {
                Sleep(500);
                canSleep = false;
            }
            else
                throw "readPayload didn't get all the bytes";
        }
        else
            canSleep = true;
        totalRead += nRead;
    }
    std::string payload = buf;
    delete [] buf;
    return payload;
}

/*
 * Read a single header line.  For the first line (called "start-line"
 * or "Request line" by the RFC) we'll get METHOD REQUEST-URI HTTP-VERSION
 * (e.g., "POST /GateKeeper/GateKeeper.asmx HTTP/1.1" or "GET /index.html
 * HTTP/1.1").  All the other headers will be in the form NAME: VALUE CR NL.
 * After the last header line we'll get an empty line (just CR NL).
 */
static bool readHeader(int fd, Header& header) {
    header.line = "";
    header.name = "";
    header.value = "";
    char c = '\0';
    bool empty = true;
    while (c != '\n') {
        int nRead = recv(fd, &c, 1, 0);
        if (nRead != 1)
            throw "readHeader(): end of header line not found";
        if (!isspace(c))
            empty = false;
        if (c == ':' && header.name.empty()) {
            for (size_t i = 0; i < header.line.size(); ++i)
                header.name += toupper(header.line[i]);
        }
        else if (!header.name.empty())
            header.value += c;
        header.line += c;
    }
    if (empty)
        return false;

    // Trim whitespace from both ends of the header value.
    if (!header.value.empty()) {
        size_t begin = 0;
        size_t end = header.value.length();
        while (begin < end) {
            if (isspace(header.value[begin]))
                ++begin;
            else if (isspace(header.value[end - 1]))
                --end;
            else
                break;
        }
    }
    return true;
}

/*
 * Make up a unique file name for logging a single request.
 */
static std::string makeFilename(int counter) {
    time_t clock = time(NULL);
    struct tm* now = localtime(&clock);
    char buf[256];
    strftime(buf, sizeof buf, "DummyWebServer-%Y%m%d%H%M%S", now);
    sprintf(buf + strlen(buf), "-%d.log", counter);
    return std::string(buf);
}

/**
 * Sends the client a simple HTTP response.
 */
void sendResponse(int fd) {
    char* response = "<body><i><b>We're testing right now!</b></i></body>";
    char headers[256];
    int len = strlen(response);
    sprintf(headers,
            "HTTP/1.1 200 OK\r\n"
            "Content-type: text/html\r\n"
            "Content-length: %d\r\n\r\n", len);
    send(fd, headers, strlen(headers), 0);
    send(fd, response, len, 0);
}
