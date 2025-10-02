//
//  pprimes.c
//  CPrimeFinder
//
//  Created by Talmage Gaisford on 9/29/25.
//

#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <limits.h>
#include <ctype.h>

int parse_integer_arg(const char *input, long long *outValue) {
    char *endptr = NULL;
    errno = 0;
    
    // strtoll to pull integer value from input string
    long long value = strtoll(input, &endptr, 10);

    // check if there is no input
    if (endptr == input) {
        return 0;
    }
    
    // check if input is too long for long long
    if (errno == ERANGE) {
        return 0;
    }

    // Skip over trailing whitespace
    while (*endptr != '\0' && isspace((unsigned char)*endptr)) {
        endptr++;
    }
    
    //check for values after whitespace
    if (*endptr != '\0') {
        return 0;
    }

    *outValue = value;
    return 1;
}

// Returns 1 if n is prime, 0 otherwise.
// Checks divisibility from 2 up to floor(sqrt(n)) using a safe bound (i <= n / i) to avoid overflow.
static int is_prime(long long n) {
    if (n < 2) return 0;          // 0, 1, and negatives are not prime
    if (n == 2) return 1;         // 2 is prime
    if ((n & 1LL) == 0) return 0; // even numbers > 2 are not prime

    for (long long i = 3; i <= n / i; i += 2) {
        if (n % i == 0) {
            return 0;
        }
    }
    return 1;
}

int main(int argc, const char * argv[]) {
    if (argc < 2 || argc > 3) {
        fprintf(stderr, "Usage: %s <max_value> [thread_count]\n", argv[0]);
        return EXIT_FAILURE;
    }

    long long max_value = 0;
    if (!parse_integer_arg(argv[1], &max_value) && max_value > 1) {
        fprintf(stderr, "Error: '%s' is not a valid integer for max_value.\n", argv[1]);
        return EXIT_FAILURE;
    }

    long long thread_count = 2;
    if (argc == 3) {
        if (!parse_integer_arg(argv[2], &thread_count)) {
            fprintf(stderr, "Error: '%s' is not a valid integer for thread_count.\n", argv[2]);
            return EXIT_FAILURE;
        }
        if (thread_count < 1) {
            fprintf(stderr, "Error: thread_count must be >= 1.\n");
            return EXIT_FAILURE;
        }
    }

    printf("max_value: %lld\n", max_value);
    printf("thread_count: %lld\n", thread_count);

    // TODO: Next step: compute and print all prime numbers <= max_value using thread_count threads

    return EXIT_SUCCESS;
}
