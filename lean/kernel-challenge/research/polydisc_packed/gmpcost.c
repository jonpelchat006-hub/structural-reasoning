// Price a list of GMP operations with the same GMP the Lean kernel links (Lean's libgmp.a).
// stdin lines: "mul A B" | "div Q D" (exact: dividend = q*d, q ~Q bits, d ~D bits) | "add A B" | "sub A B"
// Under callgrind (--collect-atstart=no) only the operations themselves are counted.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <valgrind/callgrind.h>
typedef struct { int a; int s; unsigned long *d; } mpz_struct;
typedef mpz_struct mpz_t[1];
void __gmpz_init(mpz_struct *);
void __gmpz_clear(mpz_struct *);
void __gmpz_mul(mpz_struct *, const mpz_struct *, const mpz_struct *);
void __gmpz_add(mpz_struct *, const mpz_struct *, const mpz_struct *);
void __gmpz_sub(mpz_struct *, const mpz_struct *, const mpz_struct *);
void __gmpz_tdiv_q(mpz_struct *, const mpz_struct *, const mpz_struct *);
void __gmpz_tdiv_r(mpz_struct *, const mpz_struct *, const mpz_struct *);
void __gmpz_and(mpz_struct *, const mpz_struct *, const mpz_struct *);
void __gmpz_mul_2exp(mpz_struct *, const mpz_struct *, unsigned long);
void __gmpz_tdiv_q_2exp(mpz_struct *, const mpz_struct *, unsigned long);
void __gmpz_import(mpz_struct *, size_t, int, size_t, int, size_t, const void *);
void __gmpz_setbit(mpz_struct *, unsigned long);
static unsigned long long st = 88172645463325252ULL;
static unsigned long long rnd(void) { st ^= st << 13; st ^= st >> 7; st ^= st << 17; return st; }
static void rand_bits(mpz_struct *z, long bits) {
  long n = (bits + 63) / 64; if (n < 1) n = 1;
  unsigned long long *buf = malloc(n * 8);
  for (long i = 0; i < n; i++) buf[i] = rnd();
  long top = bits - 64 * (n - 1); if (top < 64 && top > 0) buf[n-1] &= (top == 64 ? ~0ULL : ((1ULL << top) - 1));
  __gmpz_import(z, n, -1, 8, 0, 0, buf); __gmpz_setbit(z, bits > 0 ? bits - 1 : 0); free(buf);
}
int main(void) {
  char op[16]; long a, b; mpz_t x, y, r, p;
  __gmpz_init(x); __gmpz_init(y); __gmpz_init(r); __gmpz_init(p);
  while (scanf("%15s %ld %ld", op, &a, &b) == 3) {
    if (!strcmp(op, "mod")) { rand_bits(x, a); rand_bits(y, b); __gmpz_mul(p, x, y);
      CALLGRIND_TOGGLE_COLLECT; __gmpz_tdiv_r(r, p, y); CALLGRIND_TOGGLE_COLLECT; }
    else if (!strcmp(op, "shl")) { rand_bits(x, a);
      CALLGRIND_TOGGLE_COLLECT; __gmpz_mul_2exp(r, x, b); CALLGRIND_TOGGLE_COLLECT; }
    else if (!strcmp(op, "shr")) { rand_bits(x, a);
      CALLGRIND_TOGGLE_COLLECT; __gmpz_tdiv_q_2exp(r, x, b); CALLGRIND_TOGGLE_COLLECT; }
    else if (!strcmp(op, "and")) { rand_bits(x, a); rand_bits(y, b);
      CALLGRIND_TOGGLE_COLLECT; __gmpz_and(r, x, y); CALLGRIND_TOGGLE_COLLECT; }
    else if (!strcmp(op, "div")) { rand_bits(x, a); rand_bits(y, b); __gmpz_mul(p, x, y);
      CALLGRIND_TOGGLE_COLLECT; __gmpz_tdiv_q(r, p, y); CALLGRIND_TOGGLE_COLLECT; }
    else { rand_bits(x, a); rand_bits(y, b);
      CALLGRIND_TOGGLE_COLLECT;
      if (!strcmp(op, "mul")) __gmpz_mul(r, x, y); else if (!strcmp(op, "add")) __gmpz_add(r, x, y); else __gmpz_sub(r, x, y);
      CALLGRIND_TOGGLE_COLLECT; }
  }
  return 0;
}
