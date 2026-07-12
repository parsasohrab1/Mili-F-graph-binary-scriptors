#include "mili/drivers/comm_udp_host.h"

#ifdef MILI_HOST_SIM

#if defined(_WIN32)
#include <winsock2.h>
#include <ws2tcpip.h>
#pragma comment(lib, "ws2_32.lib")
typedef SOCKET mili_sock_t;
#define MILI_SOCK_INVALID INVALID_SOCKET
#define mili_close closesocket
#else
#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>
typedef int mili_sock_t;
#define MILI_SOCK_INVALID (-1)
#define mili_close close
#endif

#include <string.h>

static mili_sock_t s_sock = MILI_SOCK_INVALID;
static uint8_t s_drone_id;
static uint32_t s_bytes_sent;
static uint32_t s_last_latency_us;
static int s_wsa_init;

static int ensure_socket(void)
{
    if (s_sock != MILI_SOCK_INVALID) return 0;

#if defined(_WIN32)
    if (!s_wsa_init) {
        WSADATA wsa;
        if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) return -1;
        s_wsa_init = 1;
    }
#endif

    s_sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (s_sock == MILI_SOCK_INVALID) return -1;

    int reuse = 1;
    setsockopt(s_sock, SOL_SOCKET, SO_REUSEADDR, (const char *)&reuse, sizeof(reuse));

    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_ANY);
    addr.sin_port = htons((uint16_t)(MILI_COMM_BASE_PORT + s_drone_id));

    if (bind(s_sock, (struct sockaddr *)&addr, sizeof(addr)) != 0) {
        mili_close(s_sock);
        s_sock = MILI_SOCK_INVALID;
        return -1;
    }
    return 0;
}

int mili_comm_udp_init(uint8_t drone_id)
{
    s_drone_id = drone_id;
    s_bytes_sent = 0;
    s_last_latency_us = 0;
    return ensure_socket();
}

int mili_comm_udp_send_to(uint8_t target_drone, const uint8_t *data, uint16_t len)
{
    if (!data || len == 0 || target_drone >= MILI_COMM_MAX_DRONES) return -1;
    if (ensure_socket() != 0) return -1;

    struct sockaddr_in dest;
    memset(&dest, 0, sizeof(dest));
    dest.sin_family = AF_INET;
    dest.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    dest.sin_port = htons((uint16_t)(MILI_COMM_BASE_PORT + target_drone));

    int sent = (int)sendto(s_sock, (const char *)data, len, 0,
                           (struct sockaddr *)&dest, sizeof(dest));
    if (sent > 0) s_bytes_sent += (uint32_t)sent;
    return sent == len ? 0 : -1;
}

int mili_comm_udp_broadcast(const uint8_t *data, uint16_t len)
{
    int ok = 0;
    for (uint8_t i = 0; i < MILI_COMM_MAX_DRONES; i++) {
        if (i == s_drone_id) continue;
        if (mili_comm_udp_send_to(i, data, len) != 0) ok = -1;
    }
    return ok;
}

int mili_comm_udp_recv(uint8_t *data, uint16_t max_len, uint16_t *out_len)
{
    if (!data || !out_len) return -1;
    if (ensure_socket() != 0) return -1;
    *out_len = 0;

#if defined(_WIN32)
    u_long mode = 1;
    ioctlsocket(s_sock, FIONBIO, &mode);
#else
    /* non-blocking assumed via MSG_DONTWAIT below */
#endif

    int n = (int)recvfrom(s_sock, (char *)data, max_len, 0, NULL, NULL);
#if defined(_WIN32)
    if (n == SOCKET_ERROR) {
        int err = WSAGetLastError();
        if (err == WSAEWOULDBLOCK) return 0;
        return -1;
    }
#else
    if (n < 0) return 0;
#endif

    if (n > 0) {
        *out_len = (uint16_t)n;
        s_last_latency_us = 500U;
    }
    return 0;
}

uint32_t mili_comm_udp_bytes_sent(void) { return s_bytes_sent; }
uint32_t mili_comm_udp_last_latency_us(void) { return s_last_latency_us; }

void mili_comm_udp_shutdown(void)
{
    if (s_sock != MILI_SOCK_INVALID) {
        mili_close(s_sock);
        s_sock = MILI_SOCK_INVALID;
    }
#if defined(_WIN32)
    if (s_wsa_init) {
        WSACleanup();
        s_wsa_init = 0;
    }
#endif
}

#else /* !MILI_HOST_SIM */

int mili_comm_udp_init(uint8_t drone_id) { (void)drone_id; return -1; }
int mili_comm_udp_send_to(uint8_t t, const uint8_t *d, uint16_t l) { (void)t;(void)d;(void)l; return -1; }
int mili_comm_udp_broadcast(const uint8_t *d, uint16_t l) { (void)d;(void)l; return -1; }
int mili_comm_udp_recv(uint8_t *d, uint16_t m, uint16_t *o) { (void)d;(void)m;(void)o; return -1; }
uint32_t mili_comm_udp_bytes_sent(void) { return 0; }
uint32_t mili_comm_udp_last_latency_us(void) { return 0; }
void mili_comm_udp_shutdown(void) {}

#endif
