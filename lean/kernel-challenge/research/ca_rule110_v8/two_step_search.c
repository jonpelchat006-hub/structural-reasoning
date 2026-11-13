// Search: is the k-step Rule 110 map a "bit q of a weighted sum" function?
//   out = bit q of (t + sum_i w_i x_i), weights taken mod 2^(q+1).
// Incremental search with pruning: assign weights one at a time and check every input
// pattern whose set bits lie within the assigned weights.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static int f1(int l,int c,int r){ return (110 >> (4*l+2*c+r)) & 1; }
static int NV, Q, MOD;
static unsigned char target[1<<9];
static int w[9]; static long long found = 0; static int T;
static int printed = 0;
// patterns ordered so that pattern p uses only variables < v when p < (1<<v)
static void rec(int v, int *sum /* sum for each pattern < 1<<v */){
  if (v == NV){
    found++;
    if (printed < 8){ printed++; printf("  q=%d t=%d w=", Q, T); for(int i=0;i<NV;i++) printf("%d ", w[i]); printf("\n"); }
    return;
  }
  int half = 1<<v;
  for (int wv = 1; wv < MOD; wv++){
    int ok = 1;
    for (int p = 0; p < half; p++){
      int s = (sum[p] + wv) & (MOD-1);
      if (((s >> Q) & 1) != target[p | half]) { ok = 0; break; }
      sum[p | half] = s;
    }
    if (ok){ w[v] = wv; rec(v+1, sum); }
  }
}
int main(int argc, char **argv){
  int steps = atoi(argv[1]); int qmax = atoi(argv[2]);
  NV = 2*steps + 1;
  // variable i = cell at offset i - steps; compute steps-fold rule 110 at the center
  for (int p = 0; p < (1<<NV); p++){
    int cur[16], nxt[16]; for (int i=0;i<NV;i++) cur[i] = (p>>i)&1;
    int n = NV;
    for (int s=0;s<steps;s++){ for (int i=1;i<n-1;i++) nxt[i-1] = f1(cur[i-1],cur[i],cur[i+1]); n -= 2; memcpy(cur,nxt,sizeof(int)*n); }
    target[p] = cur[0];
  }
  for (Q = 1; Q <= qmax; Q++){
    MOD = 1<<(Q+1); found = 0; printed = 0;
    static int sum[1<<9];
    for (T = 0; T < MOD; T++){
      if (((T >> Q) & 1) != target[0]) continue;
      sum[0] = T; rec(0, sum);
    }
    printf("steps=%d q=%d: %lld solutions (weights mod %d)\n", steps, Q, found, MOD);
    fflush(stdout);
  }
  return 0;
}
