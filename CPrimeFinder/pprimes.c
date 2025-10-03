//
//  pprimes.c
//  CPrimeFinder
//
//  Created by Talmage Gaisford on 9/29/25.
//

// pprimes.c — skeleton with thin main (no threads yet)
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <limits.h>
#include <ctype.h>
#include <time.h>

/* ---------- Timing ---------- */
struct Timer {
    struct timespec start;
};

static void timer_start(struct Timer *t) {
    clock_gettime(CLOCK_MONOTONIC, &t->start);
}

static double timer_ms_since(const struct Timer *t) {
    struct timespec now;
    clock_gettime(CLOCK_MONOTONIC, &now);
    time_t sec = now.tv_sec - t->start.tv_sec;
    long nsec = now.tv_nsec - t->start.tv_nsec;
    if (nsec < 0) { sec -= 1; nsec += 1000000000L; }
    return (double)sec * 1000.0 + (double)nsec / 1000000.0;
}

/* ---------- Parsing ---------- */
int parse_integer_arguments(const char *input, long long *outValue) {
    char *endptr = NULL;
    errno = 0;
    long long value = strtoll(input, &endptr, 10);

    if (endptr == input) return 0;            // no digits
    if (errno == ERANGE) return 0;            // out of range
    while (*endptr && isspace((unsigned char)*endptr)) endptr++; // skip trailing ws
    if (*endptr != '\0') return 0;            // junk after number

    *outValue = value;
    return 1;
}

int parse_command_line(int argc, const char *argv[], long long *max_value, long long *thread_count) {
    if (argc < 2 || argc > 3) {
        fprintf(stderr, "Usage: %s <max_value> [thread_count]\n", argv[0]);
        return 0;
    }
    if (!parse_integer_arguments(argv[1], max_value) || *max_value < 2) {
        fprintf(stderr, "Error: '%s' is not a valid integer ≥ 2 for max_value.\n", argv[1]);
        return 0;
    }
    *thread_count = 2; // default
    if (argc == 3) {
        if (!parse_integer_arguments(argv[2], thread_count) || *thread_count < 1) {
            fprintf(stderr, "Error: '%s' is not a valid integer ≥ 1 for thread_count.\n", argv[2]);
            return 0;
        }
    }
    return 1;
}

/* ---------- Primality ---------- */
static int is_prime(long long n) {
    if (n < 2) return 0;
    if (n == 2) return 1;
    if ((n & 1LL) == 0) return 0;            // even >2
    for (long long d = 3; d <= n / d; d += 2) {
        if (n % d == 0) return 0;
    }
    return 1;
}

/* ---------- Results & Output ---------- */
unsigned char *alloc_results(long long max_value) {
    size_t bytes = (size_t)(max_value + 1);
    unsigned char *arr = (unsigned char *)calloc(bytes, 1); // zeroed
    if (!arr) {
        fprintf(stderr, "Error: failed to allocate %zu bytes for results.\n", bytes);
        exit(EXIT_FAILURE);
    }
    return arr;
}

void count_and_print(const unsigned char *is_prime, long long max_value, const char *label) {
    long long count = 0;
    for (long long n = 2; n <= max_value; ++n) if (is_prime[n]) count++;

    printf("[%s] total primes: %lld\n", label, count);
    printf("[%s] list:", label);
    for (long long n = 2; n <= max_value; ++n) if (is_prime[n]) printf(" %lld", n);
    printf("\n");
}

/* ---------- Runners ---------- */
void run_sequential(long long max_value, unsigned char *is_prime_arr) {
    for (long long n = 2; n <= max_value; ++n) {
        is_prime_arr[n] = (unsigned char)is_prime(n);
    }
}

/* placeholder: call threaded later; for now reuse sequential so it still runs */
void run_threaded(long long max_value, long long thread_count, unsigned char *is_prime_arr) {
    (void)thread_count; // suppress unused for now
    run_sequential(max_value, is_prime_arr);
}

/* ---------- Main (thin) ---------- */
int main(int argc, const char *argv[]) {
    long long max_value = 0, thread_count = 2;
    if (!parse_command_line(argc, argv, &max_value, &thread_count)) return EXIT_FAILURE;

    printf("max_value: %lld\nthread_count: %lld\n", max_value, thread_count);

    unsigned char *is_prime_arr = alloc_results(max_value);

    struct Timer t;
    timer_start(&t);

    if (thread_count == 1) {
        run_sequential(max_value, is_prime_arr);
    } else {
        run_threaded(max_value, thread_count, is_prime_arr);
    }

    double ms = timer_ms_since(&t);
    const char *label = (thread_count == 1) ? "sequential" : "threaded";
    count_and_print(is_prime_arr, max_value, label);
    printf("[%s] elapsed: %.3f ms\n", label, ms);

    free(is_prime_arr);
    return EXIT_SUCCESS;
}

