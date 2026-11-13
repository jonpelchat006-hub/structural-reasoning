// One callgrind dump per operation: price a grid of GMP operation sizes in one valgrind run.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <valgrind/callgrind.h>
typedef struct { int a; int s; unsigned long *d; } mpz_struct;
void __gmpz_init(mpz_struct *);
void __gmpz_mul(mpz_struct *, const mpz_struct *, const mpz_struct *);
void __gmpz_tdiv_q(mpz_struct *, const mpz_struct *, const mpz_struct *);
void __gmpz_tdiv_r(mpz_struct *, const mpz_struct *, const mpz_struct *);
void __gmpz_add(mpz_struct *, const mpz_struct *, const mpz_struct *);
void __gmpz_import(mpz_struct *, size_t, int, size_t, int, size_t, const void *);
void __gmpz_setbit(mpz_struct *, unsigned long);
static unsigned long long st = 88172645463325252ULL;
static unsigned long long rnd(void) { st ^= st << 13; st ^= st >> 7; st ^= st << 17; return st; }
static void rand_limbs(mpz_struct *z, long n) {
  unsigned long long *buf = malloc(n * 8);
  for (long i = 0; i < n; i++) buf[i] = rnd();
  __gmpz_import(z, n, -1, 8, 0, 0, buf); __gmpz_setbit(z, 64 * n - 1); free(buf);
}
int main(void) {
  char op[16]; long a, b; mpz_struct x, y, r, p;
  __gmpz_init(&x); __gmpz_init(&y); __gmpz_init(&r); __gmpz_init(&p);
  while (scanf("%15s %ld %ld", op, &a, &b) == 3) {
    rand_limbs(&x, a); rand_limbs(&y, b);
    if (!strcmp(op, "mul")) { CALLGRIND_ZERO_STATS; CALLGRIND_TOGGLE_COLLECT; __gmpz_mul(&r, &x, &y); CALLGRIND_TOGGLE_COLLECT; }
    else if (!strcmp(op, "add")) { CALLGRIND_ZERO_STATS; CALLGRIND_TOGGLE_COLLECT; __gmpz_add(&r, &x, &y); CALLGRIND_TOGGLE_COLLECT; }
    else { __gmpz_mul(&p, &x, &y); CALLGRIND_ZERO_STATS; CALLGRIND_TOGGLE_COLLECT;
      if (!strcmp(op, "div")) __gmpz_tdiv_q(&r, &p, &y); else __gmpz_tdiv_r(&r, &p, &y); CALLGRIND_TOGGLE_COLLECT; }
    CALLGRIND_DUMP_STATS_AT(op);
  }
  return 0;
}
